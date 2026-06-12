# Input Architecture Unification Design

## 摘要

這份 spec 定義 app-service 拆分之後的下一個重構階段：統一 `nvda_remote` 與 `key_echo` 使用的鍵盤與快速鍵輸入架構。

這一階段的目標，是讓兩個 app 採用相同的生命週期模型：

- `idle`：只執行 `HotkeyCapture`
- `active`：停止 `HotkeyCapture`，改由完整的鍵盤 `InputCapture` pipeline 處理

這個階段**不**會重新設計 output 架構、加入 typed domain events，或把輸入裝置泛化到鍵盤與快速鍵以外的類型。

## 目標

1. 讓 `nvda_remote` 與 `key_echo` 收斂到同一套輸入生命週期模型。
2. 把共用的輸入生命週期與轉換政策邏輯，從 app facade 中抽出來。
3. 保持 app-specific 的業務處理與共用的輸入 state machine 邏輯分開。
4. 確保 active 與 idle 的 capture 模式不會重疊。
5. 維持目前 UI-facing controller 的行為。

## 非目標

- 重設 output 架構
- 在整個 app 中導入 typed event/state flow
- 泛化到 gamepad、braille keyboard、media key，或其他未來的裝置
- 從 `nvda_remote` 移除平台專屬的 `HotkeyCapture` 實作
- 把所有平台 capture 機制收斂成單一實體實作

## 問題說明

目前兩個 app 使用相近的概念，但輸入生命週期政策不同：

- `nvda_remote`
  - idle/connected：使用 `HotkeyCapture`
  - active/controlling：停止 `HotkeyCapture`，改用鍵盤 `InputCapture`
- `key_echo`
  - 目前把狀態切換快速鍵與 active key handling 混在鍵盤驅動的路徑中
  - 前一輪修正已證明，快速鍵可達性與 capture 生命週期很容易糾纏在一起

因此會出現這些問題：

- capture 生命週期規則沒有被表達成一個可重用模型
- 不同 app 對狀態切換快速鍵的處理方式不同
- facade 還承擔了太多輸入協調的知識
- 測試有覆蓋 app 行為，但共用的生命週期合約還沒有被明確表達出來

## 期望模型

兩個 app 都應該採用同一種輸入生命週期：

### Idle

- `HotkeyCapture` 執行中
- 鍵盤 `InputCapture` 停止中
- 只監聽用來進入 active 模式的狀態切換快速鍵

### Active

- `HotkeyCapture` 停止中
- 鍵盤 `InputCapture` 執行中
- 一般鍵盤事件透過 app 的 active keyboard pipeline 處理
- active 狀態下的退出鍵，要在 active keyboard pipeline 內處理，而不是靠另一條 parallel hotkey capture

## App 行為

### `nvda_remote`

- idle：
  - `F11` 進入 control mode
- active：
  - `F11` 離開 control mode
  - 其他按鍵照 remote input forwarding 規則處理

### `key_echo`

- idle：
  - `Enter` 進入 echo mode
- active：
  - `Escape` 離開 echo mode
  - 其他按鍵照 echo playback 規則處理

## 架構方向

共用程式碼應該表達 input state machine。app-specific 程式碼則提供：

- 進入 idle 的快速鍵 mapping
- active 狀態下的退出鍵規則
- active 狀態下的 key handling 行為

共用層不需要知道「control mode」或「echo mode」的業務細節，只需要處理泛用的 active/inactive transitions。

## 建議元件

### `InputActivationUseCase`

共用 use case，負責 capture 生命週期的轉換。

責任：

- 進入 active mode
- 離開 active mode
- 確保 `HotkeyCapture` 與鍵盤 `InputCapture` 互斥
- 在 start/stop 部分失敗時能安全恢復
- 暴露目前的 activation state

規則：

- `enter_active()`
  - 如果 `HotkeyCapture` 正在執行，就先停掉
  - 如果鍵盤 `InputCapture` 沒有執行，就啟動它
  - 只有在鍵盤 capture 真的跑起來之後，才標記為 active
- `exit_active()`
  - 如果鍵盤 `InputCapture` 正在執行，就先停掉
  - 必要時再啟動 `HotkeyCapture`
  - 只有在轉換安全恢復之後，才標記為 idle

失敗行為：

- 如果進入 active 時鍵盤 capture 啟動失敗：
  - 盡可能恢復 idle 的 hotkey capture
  - 不要讓 state 保持在 active
  - 透過呼叫端提供的 error callback 回報錯誤
- 如果離開 active 時 hotkey capture 無法重新啟動：
  - 回報錯誤
  - 除非 capture 狀態真的符合模型，不然不要宣告 idle 成功

### `StateTransitionHotkeyPolicy`

共用 policy，用來處理 idle 狀態下會啟動 app 的快速鍵。

責任：

- 接受 app 提供的 hotkey mapping
- 把 idle hotkey event 對應成 transition action
- 不知道 app 的業務行為

例子：

- `nvda_remote`: `F11 -> enter_active`
- `key_echo`: `Enter -> enter_active`

這個 policy 只會在 idle 狀態下生效，而且只會透過 `HotkeyCapture` 使用。

### `ActiveKeyEventPolicy`

共用的 active-state routing policy，搭配 app 提供的 handler。

責任：

- 只在 active 狀態下處理 keyboard events
- 辨識 app 的 active-state exit key
- 把非退出鍵路由給 app-specific 的 active handler

例子：

- `nvda_remote`
  - exit key: `F11`
  - non-exit 行為: remote key forwarding
- `key_echo`
  - exit key: `Escape`
  - non-exit 行為: speak / echo key events

這個 policy 應該回傳 `KeyEventDecision`，並且負責 active keyboard path 的 exit-key routing 決策。

### App-Specific Active Handlers

app-specific 邏輯要留在共用 lifecycle state machine 之外。

例子：

- `nvda_remote`
  - remote forwarding logic
  - remote control 專用的 local suppression 規則
- `key_echo`
  - speech echo 行為
  - echo 專用的 suppression 規則

## 資料流

### Idle Path

1. app 綁定 `HotkeyCapture` handler
2. 收到 idle hotkey event
3. `StateTransitionHotkeyPolicy` 檢查是否符合 app 的 activate hotkey
4. `InputActivationUseCase.enter_active()` 切換 capture 的擁有權
5. app-specific 的 start action 執行
   - `start_control()` 或 `start_echo()`

### Active Path

1. app 綁定鍵盤 `InputCapture` listener
2. 收到 keyboard event
3. `ActiveKeyEventPolicy` 檢查是否為 app 的 exit key
4. 如果是 exit key：
   - app-specific 的 stop action 執行
   - `InputActivationUseCase.exit_active()` 恢復 idle capture mode
5. 否則：
   - app-specific 的 active key handler 執行

## Facade 責任

這次重構之後，app facade 應該要：

- 組合共用的 input lifecycle / policy components
- 連接 app-specific handlers 與 callbacks
- 暴露既有的 UI-facing methods

app facade 不應該：

- 直接擁有主要的 capture 轉換 state machine
- 重複實作 idle/active capture 切換邏輯
- 重複實作 state-transition hotkey routing 邏輯

## 平台 / Capture 策略

這一階段標準化的是 policy model，不是底層平台機制。

也就是說：

- `nvda_remote` 可以保留現有的 `HotkeyCapture` 實作
- `key_echo` 應該擁有相同的生命週期形狀：idle hotkey capture、active keyboard capture
- 只要平台專屬的 capture 物件符合共用控制合約，就仍然是可接受的

我們標準化的是：

- 每個 capture 什麼時候執行
- 轉換如何發生
- 快速鍵規則放在哪裡

我們不標準化的是：

- 為所有平台與模式提供一個通用的實體 capture backend

## 錯誤處理

共用 input lifecycle code 必須避免半切換狀態。

要求：

- 正常情況下，不得同時存在 active 的 hotkey capture 與 active 的 keyboard capture
- state flag 不能在只剩 hotkey capture 執行時還宣稱 active
- state flag 不能在 keyboard capture 仍掌控 pipeline 時還宣稱 idle
- capture start/stop 失敗，必須回報到現有的 status/error reporting

`nvda_remote` 與 `key_echo` 可以有不同的使用者訊息，但 rollback 的預期應該一致。

## 測試策略

### 共用單元測試

針對抽出的共用 input lifecycle / policy components，增加直接測試：

- idle -> active 的轉換
- active -> idle 的轉換
- keyboard capture start 失敗時的 rollback
- hotkey capture 重啟失敗時的回報
- capture 之間的互斥性

### App-level 測試

#### `nvda_remote`

- idle `F11` 進入 control
- active `F11` 離開 control
- 非退出鍵的 forwarding 行為維持不變

#### `key_echo`

- idle `Enter` 進入 echo
- active `Escape` 離開 echo
- active 狀態下的一般按鍵仍然會 echo speech
- idle 狀態下的非 hotkey 會 pass through

### Runtime / Integration 預期

- runtime 一開始在 idle mode
- idle mode 只擁有 `HotkeyCapture`
- active mode 只擁有 keyboard `InputCapture`
- shutdown 會乾淨地停止所有 active captures

## 完成條件

以下條件都滿足時，這個階段才算完成：

1. `nvda_remote` 與 `key_echo` 都採用 `idle hotkey / active keyboard` 生命週期。
2. `key_echo` 擁有正確的 `HotkeyCapture` idle 啟動路徑。
3. active 狀態下的退出鍵，都在 active keyboard pipeline 內處理。
4. 共用的 input lifecycle 與 transition policy components 已經抽出。
5. app facades 不再擁有主要的 capture-switching state machine。
6. shutdown / teardown 會正確停止所有 captures。
7. 現有 UI controller surface 維持相容。
8. 測試會直接覆蓋共用生命週期 rollback 與 app-level 快速鍵行為。

## 建議檔案方向

實際檔名可以調整，但結構上應該往下面這個方向收斂：

```text
src/application/input/
  activation.py
  state_transition_hotkeys.py
  active_key_policy.py

src/apps/nvda_remote/
  facade.py
  use_cases/
    remote_active_input.py

src/apps/key_echo/
  facade.py
  use_cases/
    echo_active_input.py
```

共用的 input lifecycle 應該放在 `application/`，而 app-specific 的 active 行為則保留在各自的 app-local modules。
