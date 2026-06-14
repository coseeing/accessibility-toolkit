# CapturedKeyEvent 與 Windows Native Context 設計

## 摘要

這份設計處理鍵盤輸入管線中兩個彼此耦合的問題：

1. Windows 鍵盤捕獲在面對回報非標準掃描碼格式的硬體時，仍必須持續產生正確的 HID 語意。
2. 某些下游消費者，特別是 NVDA Remote 的 legacy 按鍵轉送，必須保留原始 Windows `vk/scan/extended` 值，而不是從 HID 重新推回。

此設計在輸入捕獲邊界引入跨平台的 `CapturedKeyEvent` 容器，同時讓 `interop.key.KeyEvent` 維持純 HID 模型。Windows capture 會附帶 Windows 專用的 native context，而 NVDA Remote 會透過專用 bridge helper，在建立 legacy payload 時優先使用該 native context。

## 問題

目前的 `KeyEvent` 模型同時承擔了兩種不同責任：

- 表示平台中立的 HID 按鍵語意
- 間接支援 Windows legacy 按鍵 payload 的重建

在真實硬體上，這兩個目標會分岔。特別是受 Num Lock 影響的數字鍵盤與導航鍵，當 Windows 低階 hook 收到的掃描碼值與靜態掃描碼查表預期的正規化值不同時，就可能被錯誤分類，甚至直接被丟棄。先前驗證過的 raw-values 修正之所以有效，是因為它保留了原始 Windows 欄位，但那個做法把 Windows 專有欄位洩漏進共享的 HID 模型。

因此，這份設計必須同時滿足以下兩個需求：

- 對於需要分辨數字鍵盤與導航鍵語意的 business logic，保留正確的 HID 語意
- 對於必須輸出 Windows 相容 payload 的下游消費者，保留原始 Windows native 值

## 目標

- 讓 `KeyEvent` 維持平台中立且只承載 HID 資訊。
- 引入 capture 層事件容器，以攜帶可選的 native metadata。
- 為 forwarding 保留原始 Windows `vk_code`、`scan_code` 與 `extended` 值。
- 改善 `key_event_from_windows()`，使 Num Lock 相關的數字鍵盤與導航鍵在問題硬體上仍能維持正確語意。
- 不捏造 native metadata，並維持 macOS 既有行為正常。
- 將平台特有知識限制在 adapter 與 app 邊界程式碼中。

## 交付階段切分

這份設計刻意分階段交付。

本 spec 的 Phase 1 交付內容為：

- `CapturedKeyEvent`
- `WindowsNativeKeyContext`
- 改善後、可供一般 business logic 使用的 Windows HID 語意映射
- 在 Windows 上以 `native_context` 作為主要 payload 來源的 NVDA Remote legacy forwarding

Phase 2 明確延後處理：

- 評估是否能只靠 HID 語意就穩定產生相容的 legacy payload
- 判斷 NVDA Remote 未來是否能停止依賴 `native_context` 進行 forwarding

Phase 1 不嘗試證明在 Windows 硬體上，`HID -> legacy payload` 重建已經完全可靠。

## 非目標

- 不重新設計整個輸入系統或 mode manager。
- 不引入一整套深層的跨平台 native metadata 抽象階層。
- 不把所有 Windows 按鍵映射都改成以 VK 為主。
- 不把變更擴大到其他無關、目前仍標示為 unsupported 的 legacy payload 按鍵。
- 除了事件容器遷移外，不額外改變 key echo、control mode 或 hotkey activation 的行為。

## 設計概觀

### 核心型別

`interop.key.KeyEvent`

- 維持為共享、平台中立的 HID 語意模型。
- 持續只表示：
  - `usage_page`
  - `usage`
  - `pressed`
- 不得包含任何 Windows 原始欄位。

`CapturedKeyEvent`

- 新增的跨平台輸入 capture 輸出容器。
- 放在輸入 adapter 邊界層，而不是 `interop`。
- 欄位：
  - `key_event: KeyEvent`
  - `native_context: object | None`

`WindowsNativeKeyContext`

- 新增的 Windows 專用 native metadata 型別。
- 放在 `adapters.windows` 之下。
- 欄位：
  - `vk_code: int`
  - `scan_code: int`
  - `extended: bool`

### 放置位置與依賴方向

建議放置位置：

- `KeyEvent`: `interop.key`
- `CapturedKeyEvent`: `adapters.inputs`
- `WindowsNativeKeyContext`: `adapters.windows`

依賴方向：

- 各平台 capture 實作產生 `CapturedKeyEvent`
- `application.keyboard` 與 app service 接受 `CapturedKeyEvent`
- 一般 business logic 應立即使用 `captured.key_event`，並忽略 `native_context`
- 只有平台相依的相容性 bridge 可以檢查 `native_context`
- app 層與 application 層不應直接依賴 Windows adapter 細節，除非是透過 app 邊界上的窄型 helper function

## 資料流

### Windows

1. Windows 低階 hook 收到原始 `vkCode`、`scanCode`、`flags`
2. `key_event_from_windows()` 將這些值轉成語意上的 `KeyEvent`
3. `WindowsKeyboardCapture` 輸出：
   - `CapturedKeyEvent(key_event=<hid event>, native_context=WindowsNativeKeyContext(...))`

### macOS

1. macOS event tap 收到原始事件
2. `key_event_from_macos()` 將其轉成語意上的 `KeyEvent`
3. `MacOSKeyboardCapture` 輸出：
   - `CapturedKeyEvent(key_event=<hid event>, native_context=None)`

## Windows HID 映射策略

### 原則

Windows 按鍵詮釋採用「按鍵類別分流」規則：

- 一般按鍵維持以掃描碼為主要依據
- 對於受 Num Lock 影響的數字鍵盤與導航鍵，允許使用 VK 輔助判定

這樣做可以在大部分鍵盤範圍內維持既有 HID 設計意圖，同時修正已知問題領域：某些硬體上的掃描碼格式不穩定，導致語意判定失真。

### 判定順序

`key_event_from_windows()` 應依下列順序解析 usage：

1. 先以現有靜態掃描碼表，用 `(scan_code, extended)` 查表
2. 若事件為 extended，且掃描碼看起來包含前綴或異常格式，則先正規化後再依既有規則重查
3. 若仍查不到，且 `vk_code` 屬於 Num Lock 相關的數字鍵盤/導航鍵群，則改用該鍵群專用的 VK 對 HID 對應
4. 若仍無法解析，回傳 `None`

### VK 輔助適用範圍

VK 輔助 fallback 刻意只限於 Num Lock 相關的數字鍵盤與導航鍵問題域：

- `VK_NUMPAD0` 到 `VK_NUMPAD9`
- `VK_INSERT`
- `VK_DELETE`
- `VK_HOME`
- `VK_END`
- `VK_PRIOR`
- `VK_NEXT`
- `VK_LEFT`
- `VK_RIGHT`
- `VK_UP`
- `VK_DOWN`
- `VK_DIVIDE`
- `VK_MULTIPLY`
- `VK_ADD`
- `VK_SUBTRACT`
- `VK_DECIMAL`
- `VK_NUMLOCK`

這項變更不會讓字母、主鍵區數字鍵或一般修飾鍵改成以 VK 作為預設權威來源。

## Capture 介面變更

### Input Capture Protocol

`InputCapture.set_listener()` 會從：

- `Callable[[KeyEvent], KeyEventDecision]`

改為：

- `Callable[[CapturedKeyEvent], KeyEventDecision]`

此變更會一路傳遞到：

- `adapters.inputs.base.InputCapture`
- `application.keyboard.KeyEventHandler`
- `application.keyboard.KeyboardInputService`
- 目前直接接收 `KeyEvent` 的 app service

### 一般使用規則

大多數程式碼都應把 `CapturedKeyEvent` 視為包裝器：

- 讀取 `captured.key_event`
- 忽略 `captured.native_context`

這樣可以避免 native metadata 洩漏進一般 business logic。

## NVDA Remote Legacy Bridge

NVDA Remote 需要 Windows 相容的 legacy payload 欄位。這個需求應由專用的 app 層 bridge 處理，而不是透過擴充 `KeyEvent` 來處理。

### 新增 Helper

引入：

- `legacy_payload_from_captured_event(captured: CapturedKeyEvent) -> dict[str, int | bool]`

行為如下：

1. 若 `captured.native_context` 是 Windows native context：
   - 直接使用以下欄位建立 legacy payload：
     - `vk_code`
     - `scan_code`
     - `extended`
   - `pressed` 則取自 `captured.key_event.pressed`
2. 否則：
   - fallback 回既有的 HID 型 `key_event_to_legacy_remote_payload(captured.key_event)`

在 Phase 1 中，Windows native-context 路徑是 NVDA Remote forwarding 預期採用的主要行為。HID 型 fallback 仍保留作為非 Windows 或缺少 context 時的相容路徑，不是本階段用來保證 Windows forwarding 正確性的主要策略。

### 設計理由

這樣可以把 Windows payload 保留邏輯隔離在 NVDA Remote 相容邊界：

- HID 語意正確性仍由 Windows adapter 負責
- 原始 Windows 欄位保留仍由 capture native context 負責
- legacy 重建則是 NVDA Remote 自己的責任

這些責任不再混雜在 `KeyEvent` 裡。

## App 與 Use Case 行為

### NVDA Remote

- `NvdaRemoteAppService` 與 `NvdaRemoteInputForwardingUseCase` 會改為接收 `CapturedKeyEvent`
- forwarding 程式碼會使用 `legacy_payload_from_captured_event()`
- 按鍵 suppression 與 mode 行為仍持續依賴 `captured.key_event`

### Key Echo 與共享 Mode 邏輯

- `KeyEchoAppService`、共享 mode 管理，以及 input policy 也會改為接收 `CapturedKeyEvent`
- 它們應立即解包使用 `captured.key_event`
- 除了容器型別遷移外，不預期有任何行為變更

## 測試策略

### 單元測試

新增或更新以下測試：

- `CapturedKeyEvent` 在 input capture 與 service 邊界間的傳遞
- Windows capture 會產生帶有 `WindowsNativeKeyContext` 的 `CapturedKeyEvent`
- macOS capture 會產生 `CapturedKeyEvent(native_context=None)`
- `key_event_from_windows()` 能解析完整的 keypad/navigation VK 輔助範圍
- 當標準掃描碼可用時，直接 scan path 仍優先
- `legacy_payload_from_captured_event()` 在有 Windows native context 時優先使用之
- `legacy_payload_from_captured_event()` 在沒有 native context 時 fallback 到 HID 映射

### 回歸測試

保留以下覆蓋：

- NVDA Remote control mode 啟動/停止鍵的 suppression 行為
- NVDA Remote 對 keypad/navigation 鍵的 forwarding 行為
- key echo 啟用與語音輸出行為
- macOS 上數字鍵盤與主鍵區的區分

## 風險

- listener 簽名變更會影響大量測試替身與 fake capture 物件，但大多屬於機械式調整
- 若讓 Windows native 型別檢查擴散到 bridge helper 之外，會破壞本次分層目標
- 若把 VK 輔助映射擴得太廣，可能會削弱其他非問題鍵群原本應由 scan 決定的語意

## 延後處理項目

- 研究是否能只依靠 HID 語意，以可接受的可靠度推導出 Windows legacy payload
- 若這件事能被明確證明可靠，再評估 NVDA Remote forwarding 是否可以減少或移除對 `native_context` 的依賴

## 考慮過的替代方案

### 在 `KeyEvent` 中加入 Windows 原始欄位

優點：

- 程式碼改動最少
- 已經驗證功能正確

缺點：

- 會以 Windows 專用欄位污染共享 HID 模型
- 會鼓勵未來把更多平台特例累積到錯誤的層次

### 旁路式 Native Lookup

優點：

- 表面上的介面改動較小

缺點：

- 事件關聯性脆弱
- 更容易產生時序 bug
- 更難推理與測試

提議的 `CapturedKeyEvent` 設計較佳，因為它能同時保住語意與 native fidelity，又不會破壞共享模型。

## 實作概要

1. 在輸入 adapter 邊界新增 `CapturedKeyEvent`
2. 在 Windows adapter 套件下新增 `WindowsNativeKeyContext`
3. 更新 `InputCapture`、`KeyEventHandler` 與 `KeyboardInputService`，改為傳遞 `CapturedKeyEvent`
4. 更新 Windows 與 macOS capture 實作，使其輸出 `CapturedKeyEvent`
5. 調整 `key_event_from_windows()`，改用本設計定義的按鍵類別分流解析順序
6. 在 NVDA Remote app 層新增 `legacy_payload_from_captured_event()`
7. 更新 NVDA Remote 與 Key Echo 的 service/use case，在需要時解包 `captured.key_event`
8. 更新單元測試與回歸測試
