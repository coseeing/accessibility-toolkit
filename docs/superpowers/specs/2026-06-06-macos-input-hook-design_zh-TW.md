# macOS Keyboard Hook 與 Hotkey Capture 設計

## 背景

目前專案的鍵盤輸入擷取能力只在 Windows 上可用。

- [`WindowsKeyboardCapture`](/workspace/nvda-remote-client/src/adapters/windows/keyboard_hook.py:34) 透過 Win32 low-level keyboard hook 擷取全域鍵盤事件。
- [`WindowsHotkeyCapture`](/workspace/nvda-remote-client/src/adapters/windows/hotkey.py:14) 透過 Windows message loop 註冊全域 `F11` hotkey。
- [`NvdaRemoteAppService`](/workspace/nvda-remote-client/src/apps/nvda_remote/service.py:16) 依賴 `InputCapture` 與 `HotkeyCapture` 這兩個抽象，將輸入事件轉為 remote `KEY` 訊息，並在 controlling 狀態下 suppress 本機按鍵。

目前 shared contract 已經整理得相對清楚：

- [`InputCapture`](/workspace/nvda-remote-client/src/adapters/inputs/base.py:11)
- [`HotkeyCapture`](/workspace/nvda-remote-client/src/adapters/inputs/base.py:27)
- [`KeyEvent`](/workspace/nvda-remote-client/src/interop/key/key_event.py:4)

這代表 macOS 擴充不應直接改寫 app service 邏輯，而應補上一組與 Windows 能力等價的 adapter。

## 目標

本次設計目標如下：

1. 為 macOS 新增可用於全域鍵盤擷取的 `InputCapture` 實作。
2. 為 macOS 新增可用於全域 `F11` toggle 的 `HotkeyCapture` 實作。
3. 在 controlling 狀態下，盡量達到與 Windows 相同的本機按鍵 suppress 行為。
4. 保持 `NvdaRemoteAppService` 對平台差異無感，不在 app service 中塞入 macOS 特例。
5. 將 macOS 權限、run loop、event tap lifecycle 封裝在 adapter 邊界內。

## 非目標

以下內容不在本次範圍：

- macOS clipboard backend
- macOS 語音輸出 backend
- 完整 macOS GUI 打包、簽署、notarization 流程
- 任意可配置 hotkey 組合；本次先固定維持 `F11`
- 滑鼠事件 capture 或其他 HID 類型
- 重寫 shared `KeyEvent` 成跨平台全新事件模型

## 關鍵結論

### 1. 必須使用 macOS 原生低階事件 API

若需求包含：

- app 不在前景時仍能全域擷取鍵盤
- controlling 時阻止按鍵繼續送到本機前景 app

則 macOS 端必須使用 `Quartz` event tap，而不是只用 observe-only 的高階事件監看 API。

### 2. Python 端採用 `PyObjC`

本次不另外引入 Swift/Objective-C 小型原生模組，而是在 Python 中透過 `PyObjC` 直接呼叫：

- `Quartz`
- `CoreGraphics`
- `ApplicationServices`

原因如下：

- 能直接存取 event tap、run loop、AX trust 檢查等 Apple 原生能力
- 維持專案以 Python 為主，不額外建立原生 build pipeline
- 比 `ctypes` 手刻 Core Foundation / callback / memory 管理更可維護

### 3. 保留既有 `InputCapture` / `HotkeyCapture` 邊界

雖然 macOS 底層最合理的做法是單一 event tap 處理所有鍵盤事件，但上層 app 已經依賴兩個明確 protocol。

因此本次設計採用：

- 兩個 macOS adapter
- 一個共享底層 `MacOSEventTapManager`

這樣可以同時滿足：

- 不改動現有 app service 的業務邏輯
- 不在 macOS 上真的建立兩套互相競爭的 event tap

## 設計原則

### 1. 平台複雜度留在 adapter 內

權限檢查、event tap 建立、run loop 啟停、事件轉換都應限制在 `adapters/macos` 中，不向 `application` 或 `apps` 擴散。

### 2. 維持 shared app contract

macOS 版必須忠實實作既有能力：

- `InputCapture.set_listener(...)`
- `InputCapture.start() / stop()`
- `HotkeyCapture.set_handler(...)`
- `HotkeyCapture.start() / stop()`

### 3. 單一低階 tap，避免多 tap 競爭

`MacOSKeyboardCapture` 與 `MacOSHotkeyCapture` 不應各自建立 event tap。真正接入系統事件流的元件只能有一個，以避免：

- 重複權限處理
- tap 啟停不同步
- 事件重入與攔截順序不穩
- 本機 suppress 規則彼此衝突

### 4. 明確面對 keycode translation

macOS 原生鍵盤事件不是 Win32 `vk`。由於 remote payload 目前仍以 Windows 風格欄位表示，macOS adapter 必須明確負責 keycode translation，而不能假設可直接沿用原值。

## 架構

### 新增模組

建議新增：

```text
src/
  adapters/
    macos/
      __init__.py
      event_tap.py
      keyboard_hook.py
      hotkey.py
      permissions.py
      keymap.py
```

### `MacOSEventTapManager`

用途：唯一接入 macOS 全域鍵盤事件流的底層管理器。

責任：

- 檢查是否具備必要權限
- 建立 `CGEventTap`
- 建立 run loop source 並掛到背景 thread 的 `CFRunLoop`
- 接收原始 `Quartz` keyboard events
- 將事件轉為內部原始事件模型
- 依序分派給 hotkey 與 keyboard capture 訂閱者
- 根據訂閱者決策回傳 pass-through 或 suppress
- 處理 tap disable / re-enable
- 在最後一個訂閱者解除時安全關閉 tap 與 run loop

它不直接知道 remote protocol，也不直接知道 `NvdaRemoteAppService`。

### `MacOSKeyboardCapture`

用途：`InputCapture` 的 macOS 實作。

責任：

- 向 `MacOSEventTapManager` 註冊 keyboard listener
- 將 manager 提供的原始 macOS 鍵盤事件轉為 shared `KeyEvent`
- 把 `KeyEvent` 傳給目前 listener
- 將 listener 的 `KeyEventDecision` 回傳給 manager

它不直接處理權限 prompt、run loop 細節或 hotkey 判斷。

### `MacOSHotkeyCapture`

用途：`HotkeyCapture` 的 macOS 實作。

責任：

- 向 `MacOSEventTapManager` 註冊 `F11` hotkey handler
- 只在 `F11 keyDown` 時觸發一次 handler
- 避免 key repeat 導致重複 toggle
- 要求 manager suppress 這組 `F11` 的 down/up

### `permissions.py`

用途：隔離 macOS 權限檢查相關 API。

責任：

- 封裝 `AXIsProcessTrustedWithOptions(...)`
- 封裝是否要帶 prompt 的選項
- 提供一致的 Python 例外或狀態結果

### `keymap.py`

用途：集中管理 macOS keycode 到 shared `KeyEvent` 欄位的轉換規則。

責任：

- 定義 macOS `keyCode` -> remote `vk` mapping
- 定義 function key、方向鍵、modifier 類按鍵的特殊處理
- 提供單元測試可直接驗證的純函式

## 執行模型

### 背景 thread 與 run loop

`MacOSEventTapManager` 在 `start()` 時建立背景 thread。

該 thread 內負責：

1. 建立 `CGEventTap`
2. 建立 `CFMachPortCreateRunLoopSource`
3. 將 source 加入 `CFRunLoop`
4. 啟用 tap
5. 執行 `CFRunLoopRun()`

這個 thread 的角色，對應到 Windows hotkey adapter 中 message loop thread 的概念，但在 macOS 上必須換成 `CFRunLoop`。

### 生命週期

- 第一個 subscriber 啟動時，manager 啟動 event tap
- 後續 subscriber 只增加註冊，不重複建立 tap
- 當 keyboard listener 與 hotkey handler 都解除後，manager 關閉 tap 與 run loop

這表示 `MacOSKeyboardCapture` 與 `MacOSHotkeyCapture` 可獨立啟停，但底層只有一份系統資源。

## 事件流

### 1. 事件接收

manager 監聽至少：

- `keyDown`
- `keyUp`

必要時可加入：

- `flagsChanged`

是否納入 `flagsChanged` 取決於 modifier-only 行為是否需要更完整支援。本次設計允許 manager 支援它，但 V1 可以先以 `keyDown` / `keyUp` 為主。

### 2. Hotkey 優先判斷

每個原始鍵盤事件進入 manager 後，先執行 hotkey 比對：

- 目前只支援 `F11`
- 只在 `F11 keyDown` 觸發 handler
- `F11 keyRepeat` 不重複觸發
- 命中 hotkey 後，`F11` down 與後續對應的 keyup 都必須 suppress

這可避免前景 app 同時收到 `F11`。

### 3. Keyboard capture 判斷

若事件不是 hotkey，或目前 keyboard capture 已啟用，則 manager 將事件送入 `MacOSKeyboardCapture`。

`MacOSKeyboardCapture` 會：

1. 將 macOS 原始事件轉為 shared `KeyEvent`
2. 呼叫 listener
3. 將 listener 回傳的 `KeyEventDecision` 回給 manager

### 4. 最終 suppress 決策

manager 根據 hotkey 與 keyboard listener 的結果決定：

- `PASS_THROUGH`：事件繼續進入本機前景 app
- `SUPPRESS`：事件由 event tap 吃掉，不進入本機 app

## `F11` 與 controlling 行為

本次行為必須與現有 [`NvdaRemoteAppService.handle_key_event(...)`](/workspace/nvda-remote-client/src/apps/nvda_remote/service.py:122) 盡量一致。

### connected 但尚未 controlling

- `HotkeyCapture` 已啟用
- `InputCapture` 尚未 forwarding 所有鍵盤
- 使用者按 `F11`
- 觸發 toggle handler
- `F11` down/up 被 suppress

### controlling 中

- `InputCapture` 已啟用
- 所有鍵盤事件都經過 `handle_key_event(...)`
- 一般鍵盤事件會被送成 remote `KEY` 訊息
- listener 回傳 `SUPPRESS` 時，本機按鍵被阻止
- `F11` 仍保留本機停止 controlling 的語意

### keyup 成對 suppress

無論是：

- hotkey 觸發的 `F11`
- 或其他被 listener suppress 的按鍵

只要 keydown 被 suppress，就必須確保對應 keyup 也被 suppress，避免前景 app 看到不完整的按鍵序列。

這個狀態可由 manager 或 app service 維護，但職責上建議：

- app service 繼續管理業務層的 `_suppressed_keyups`
- manager 管理純 tap 層對 `F11` hotkey 的 keyup suppress

## KeyEvent 對映策略

### 現況

shared `KeyEvent` 目前欄位如下：

```python
@dataclass(frozen=True, slots=True)
class KeyEvent:
    vk: int
    scan: int | None
    extended: bool
    pressed: bool
```

這是偏 Windows 的事件模型。

### macOS 對映原則

`MacOSKeyboardCapture` 需要把 macOS 原始事件轉成：

- `vk`: 對應 remote 協定期望的 Windows virtual-key code
- `scan`: 若無穩定跨平台語意，可先保留 macOS keycode 或在必要時填 `None`
- `extended`: 對方向鍵、右側 modifier、function/navigation 類鍵給出可重現規則
- `pressed`: `keyDown=True`、`keyUp=False`

### 設計決策

本次不擴張 shared `KeyEvent` 結構，而是由 macOS adapter 承擔 translation 成本。

理由：

- 目前 remote payload 與 app service 既有邏輯都依賴這個形狀
- 若在同一任務中重寫 shared key model，會把 scope 擴大到協定與所有測試

### 風險

keycode translation 是 macOS 方案中最高風險的 correctness 點。

風險來源包含：

- ANSI 與 ISO 鍵盤配置差異
- function/navigation keys 對映
- modifier-only 鍵事件
- 不同輸入法對實際字符與硬體 keycode 的關係

因此 V1 應以「硬體鍵位與 remote 協定的一致性」優先，而不是字符語意。

## 權限模型

### 必要權限

macOS 版全域鍵盤擷取與 suppress 需要依賴系統授權。

V1 設計上至少必須：

- 檢查 accessibility trust
- 在未授權時清楚回報

專案文件與手動驗證流程中也應明確要求使用者授權 `Accessibility` / `Input Monitoring`。

### 失敗回報

以下情況都不得靜默吞掉：

- 權限未授予
- event tap 建立失敗
- run loop source 建立失敗
- thread 啟動失敗

這些錯誤都應轉成清楚的 `RuntimeError` 或 adapter-specific 例外，讓 app 可在 UI 或 log 中明確呈現。

## event tap 異常與恢復

macOS 可能在特定情況下 disable event tap。

manager 需要支援：

- 偵測 tap disable 事件
- 嘗試重新 enable
- 若恢復失敗，將錯誤狀態暴露給上層

恢復策略應保守：

- 先嘗試單次 re-enable
- 若仍失敗，標記 manager 失效
- 讓下一次 `start()` 可重新建立整個 tap

## 與現有組裝層的整合

目前 [`apps/nvda_remote/main.py`](/workspace/nvda-remote-client/src/apps/nvda_remote/main.py:1) 直接組裝 Windows adapters。

為了支援 macOS，後續實作可採以下方向：

- 在 composition root 依 `sys.platform` 選擇：
  - Windows: `WindowsKeyboardCapture` / `WindowsHotkeyCapture`
  - macOS: `MacOSKeyboardCapture` / `MacOSHotkeyCapture`
- 共享底層 manager 應只在 macOS 分支中建立

本次 spec 不要求立即建立完整跨平台工廠，但後續實作不得把平台判斷散落進 app service。

## 測試策略

### 單元測試

新增 macOS adapter 單元測試，重點涵蓋：

- manager 能建立與關閉 tap lifecycle
- 未授權時 `start()` 失敗且錯誤明確
- keyboard listener 可收到正規化 `KeyEvent`
- listener 回傳 `SUPPRESS` 時 manager 回傳 suppress
- `F11` 只在 keydown 觸發一次
- `F11` key repeat 不重複觸發
- `F11` 的 keyup 也被 suppress
- tap disable 後可重啟或回報清楚失敗

### key mapping 測試

為 `keymap.py` 建立獨立測試，至少覆蓋：

- 字母鍵
- 數字鍵
- 方向鍵
- `F1` 到 `F12`
- `Enter`、`Tab`、`Escape`
- 左右 `Shift` / `Control` / `Option` / `Command`

### 既有 app service 測試

`NvdaRemoteAppService` 的既有測試應盡量不改。

理由：

- shared contract 不變
- 若 macOS adapter 實作正確，上層業務測試不應因平台而重寫

### 手動驗證

必須在真實 macOS 機器上驗證以下情境：

1. 首次啟動時未授權，錯誤訊息清楚。
2. 授權後可成功啟用 keyboard capture。
3. app 不在前景時仍可收到全域鍵盤事件。
4. controlling 時，本機前景 app 不會收到被轉發的按鍵。
5. `F11` 可開始 controlling。
6. controlling 中再按一次 `F11` 可停止 controlling。
7. `F11` 不會意外觸發前景 app 的功能鍵行為。
8. 常用鍵在遠端表現正確，特別是方向鍵、功能鍵與 modifier 組合。

## 實作順序建議

1. 新增 `adapters/macos/permissions.py` 與最小權限檢查測試。
2. 新增 `MacOSEventTapManager` 與 fake backend 測試。
3. 新增 `keymap.py` 與 key translation 測試。
4. 新增 `MacOSKeyboardCapture`。
5. 新增 `MacOSHotkeyCapture`。
6. 在 composition root 加入平台選擇。
7. 補 README 與手動驗證說明。

## 開放風險與取捨

### 1. `scan` 欄位語意不完全跨平台

Windows 的 `scan` 與 macOS 的硬體 keycode 並不等價。V1 可先以「對遠端是否足夠穩定」為主，而不是追求語意完全一致。

### 2. keyboard layout 差異

若遠端協定實際依賴 Windows `vk` 語意，則 macOS 不同實體鍵盤布局可能需要額外 mapping 表。V1 應先支援常見鍵盤，再依手測結果擴充。

### 3. 權限 UX 仍需在 UI 層補足

本次只定義 adapter 端錯誤與檢查，不包含完整 UI 導引。後續若要降低使用成本，應在 GUI 中補充更友善的授權說明。

## 結論

本次採用的設計是：

- Python 主程式維持不變
- macOS 端使用 `PyObjC` 直連 `Quartz` / `ApplicationServices`
- 保留 `InputCapture` 與 `HotkeyCapture` 兩個 shared contract
- 在 `adapters/macos` 內新增共享 `MacOSEventTapManager`
- 由 `MacOSKeyboardCapture` 與 `MacOSHotkeyCapture` 共用同一個 event tap

這個方向能在不污染 app service 的前提下，為 macOS 提供最接近 Windows 的全域 keyboard hook 與 local suppress 能力，同時把風險集中在可測、可替換的 adapter 邊界內。
