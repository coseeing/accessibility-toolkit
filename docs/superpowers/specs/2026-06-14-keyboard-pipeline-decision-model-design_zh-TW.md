# Keyboard Pipeline Decision Model 設計

## 問題

目前的鍵盤處理模型，將兩個本質不同的關注點壓縮成單一最終決策：

- 擷取到的事件是否應往下傳給作業系統
- 應用程式是否已處理該事件，以及應用程式內部處理是否應停止

目前 capture / app 邊界使用的是只有兩個值的決策模型：

- `SUPPRESS`
- `PASS_THROUGH`

這個模型實際上只支援兩種有效組合：

- 不送給系統 + app 已處理事件
- 送給系統 + app 沒有處理事件

它無法表達第三種合法組合：

- 送給系統 + app 也執行自己的功能

這個缺口目前已在 Windows `Num Lock` 與 `key_echo` 的組合上具體浮現：

- 系統必須收到 `Num Lock`，才能讓 `Num Lock` 狀態維持同步
- `key_echo` 也應該照常對這顆鍵執行自己的功能

## 目標

引入一套理論上較正確的 keyboard pipeline 模型，將下列兩個面向明確分開：

- 面向系統的 pass-through 行為
- app 內部的 handling 狀態

本次第一個具體使用情境包括：

- Windows 上的 `key_echo` 應將 `Num Lock` 往下傳給系統
- `key_echo` 也應在 app 邏輯內照常處理該鍵
- Windows 上的 `nvda_remote` 也應將 `Num Lock` 往下傳給本機系統
- 本階段 `nvda_remote` 不應將 `Num Lock` 轉送到遠端

## 非目標

- 本階段不引入 `AppPostProcessingStage`
- 本階段不將這套機制擴充到 `Caps Lock` 或 `Scroll Lock`
- 本 spec 不重設計 legacy payload forwarding

## 設計摘要

此設計引入兩種分開的結果型別：

1. `AppKeyEventResult`
   用來描述 app 內部的 handling 狀態。

2. `KeyboardPipelineResult`
   用來描述對 capture adapter 暴露的最終 pipeline 輸出。

此設計刻意不再保留最終 `KeyEventDecision` enum 作為正式模型。
capture / app 邊界應直接回傳 `KeyboardPipelineResult`。

本階段的 pipeline 刻意維持最小化，只包含三段：

1. `SystemPassThroughPolicyStage`
2. `ModeHandlingStage`
3. `DecisionAssembly`

本階段不納入 `AppPostProcessingStage`。

## 核心型別

### `AppKeyEventResult`

這是 app 內部的結果模型，供以下元件使用：

- `ModeManager`
- `ActiveKeyEventPolicy`
- 各 app use case，例如 `KeyEchoInputUseCase`

可用值：

- `UNHANDLED`
  - app 這一層沒有處理該事件
- `HANDLED_CONTINUE`
  - app 這一層已處理該事件
  - app 內部流程應繼續往下一個 handler/stage 執行
- `HANDLED_STOP`
  - app 這一層已處理該事件
  - app 內部流程應在此停止

重要邊界：

- 這個型別不負責決定事件是否要送給作業系統
- `HANDLED_CONTINUE` 純粹是 app pipeline 內部的控制訊號
- 它不代表「要送給系統」
- 它代表「這一段已處理事件，但 app pipeline 應繼續執行」

### `KeyboardPipelineResult`

這是 app service 回傳給 capture adapter 的最終結果型別。

欄位：

- `send_to_system: bool`
- `app_result: AppKeyEventResult`

含義：

- `send_to_system` 是 capture adapter 唯一必須使用的欄位，用來決定系統事件應 suppress 還是 pass through
- `app_result` 保留 app 內部語意，供測試、除錯記錄與未來擴充使用

## Pipeline Stages

### 1. `SystemPassThroughPolicyStage`

責任：

- 判斷擷取到的事件是否應往下傳給作業系統

輸出：

- `pass_through_to_system: bool`

這一段不負責：

- 回傳最終 adapter 決策
- 執行 app side effect

本階段的初始 policy：

- 在 Windows 上，若捕獲的是 `Num Lock` 事件，則設 `pass_through_to_system=True`
- 其他事件預設為 `False`

這一段可以檢查 `CapturedKeyEvent.native_context`，用來判斷事件是否來自 Windows。

在本階段，這一段是固定的前置 policy，不依賴 `ModeHandlingStage` 的輸出，也不依賴任何 `AppKeyEventResult`。
雖然技術上它也可以放在 pipeline 較後面計算，但本 spec 刻意將它放在最前面，因為它表達的是 system-facing 的邊界 policy，而不是 app-handling semantics。

### 2. `ModeHandlingStage`

責任：

- 執行 mode manager 與 mode/use case 主邏輯

輸出：

- `AppKeyEventResult`

這一段擁有的 app 行為包括：

- active mode 的退出處理
- `key_echo` 的語音行為
- 既有 app-local 鍵盤處理邏輯

它不負責決定系統是否應收到該事件。

### 3. `DecisionAssembly`

責任：

- 組合：
  - `pass_through_to_system`
  - 最終 `AppKeyEventResult`
- 產生 `KeyboardPipelineResult`

組裝規則：

- `send_to_system=False` + `UNHANDLED`
  - `KeyboardPipelineResult(send_to_system=False, app_result=UNHANDLED)`
- `send_to_system=False` + `HANDLED_CONTINUE`
  - `KeyboardPipelineResult(send_to_system=False, app_result=HANDLED_CONTINUE)`
- `send_to_system=False` + `HANDLED_STOP`
  - `KeyboardPipelineResult(send_to_system=False, app_result=HANDLED_STOP)`
- `send_to_system=True` + `UNHANDLED`
  - `KeyboardPipelineResult(send_to_system=True, app_result=UNHANDLED)`
- `send_to_system=True` + `HANDLED_CONTINUE`
  - `KeyboardPipelineResult(send_to_system=True, app_result=HANDLED_CONTINUE)`
- `send_to_system=True` + `HANDLED_STOP`
  - `KeyboardPipelineResult(send_to_system=True, app_result=HANDLED_STOP)`

重點是：pipeline 不再把這些狀態壓縮成會遺失資訊的 enum。

## 資料流

新的鍵盤處理流程如下：

1. capture adapter 發出 `CapturedKeyEvent`
2. app service 執行 `SystemPassThroughPolicyStage`
3. app service 執行 `ModeHandlingStage`
4. app service 組裝 `KeyboardPipelineResult`
5. capture adapter 只使用 `send_to_system` 來決定是否 suppress 或 pass 系統事件

這樣可以把分層明確化：

- system pass-through 是邊界層關心的事
- handling semantics 是 app 層關心的事

## `key_echo` 在此模型下的應用

### echo mode 中的一般按鍵

- pass-through policy：`False`
- echo mode 會處理此鍵並朗讀
- mode handling 回傳 `HANDLED_STOP`
- 最終結果：
  - `send_to_system=False`
  - `app_result=HANDLED_STOP`

效果：

- 系統不會收到這顆鍵
- app 行為維持既有狀態

### echo mode 中的 Windows `Num Lock`

- pass-through policy：`True`
- echo mode 仍照常對這顆鍵執行自己的功能
- `KeyEchoInputUseCase` 回傳 `HANDLED_CONTINUE`
- 最終結果：
  - `send_to_system=True`
  - `app_result=HANDLED_CONTINUE`

效果：

- Windows 會收到 `Num Lock`，因此系統 `Num Lock` 狀態可維持同步
- `key_echo` 也仍會對這顆鍵執行自己的功能

這是先前缺少的組合第一次被明確表達：

- 送給系統
- app 也處理事件

## 本階段的 `nvda_remote` 範圍

本階段的 `nvda_remote` 會採用新的 pipeline result 模型，以及共用的 Windows `Num Lock` pass-through policy。

這表示：

- service 層會適配新的 pipeline result 型別
- Windows `Num Lock` 會先往下傳給本機系統，再決定後續 app 邏輯
- 本階段 `Num Lock` 不會流入既有的 remote forwarding 路徑
- 其他既有 controlling / forwarding 行為應維持不變

## 受影響元件

- `src/adapters/inputs/base.py`
  - listener 回傳契約將從目前的單一最終決策模型改掉
- `src/application/input/`
  - 新增 `AppKeyEventResult`
  - 新增 `KeyboardPipelineResult`
  - 新增 keyboard pipeline 組裝邏輯
- `src/apps/shared/mode_manager.py`
  - 改回傳 `AppKeyEventResult`
- `src/application/input/active_key_policy.py`
  - 改回傳 `AppKeyEventResult`
- `src/apps/key_echo/use_cases/echo_input.py`
  - 一般鍵回傳 `HANDLED_STOP`
  - echo mode 中的 Windows `Num Lock` 回傳 `HANDLED_CONTINUE`
- `src/apps/key_echo/service.py`
  - 改為組裝與執行 keyboard pipeline
- `src/apps/nvda_remote/service.py`
  - 適配新的結果模型
  - 套用共用的 Windows `Num Lock` pass-through 行為
- `src/adapters/windows/keyboard_hook.py`
  - 改為使用 `send_to_system`
- `src/adapters/macos/keyboard_hook.py`
  - 同步調整 listener 回傳型別，並使用 `send_to_system`

## Migration Plan

1. 先引入新的核心結果型別：
   - `AppKeyEventResult`
   - `KeyboardPipelineResult`
2. 更新 capture listener 介面，改為回傳 `KeyboardPipelineResult`
3. 更新 Windows 與 macOS adapter，使其只讀取 `send_to_system`
4. 更新 `ModeManager` 與 `ActiveKeyEventPolicy`，改回傳 `AppKeyEventResult`
5. 更新 `key_echo` use case 與 service，使其使用新 pipeline
6. 讓 `nvda_remote` 適配新介面，並在 forwarding 前套用共用的 Windows `Num Lock` pass-through

## 測試策略

### 單元測試

- `SystemPassThroughPolicyStage`
  - Windows `Num Lock` -> `send_to_system=True`
  - 非 Windows 或非 `Num Lock` -> `False`
- `ModeManager`
  - 無 active mode -> `UNHANDLED`
  - exit key -> `HANDLED_STOP`
- `KeyEchoInputUseCase`
  - 一般鍵 -> `HANDLED_STOP`
  - echo mode 中的 Windows `Num Lock` -> `HANDLED_CONTINUE`
- decision assembly
  - 驗證 `send_to_system` 與 `app_result` 都會被保留，不會被有損壓縮

### Adapter 測試

- Windows 與 macOS keyboard hook 都只依 `send_to_system` 決定：
  - `True` -> pass through
  - `False` -> suppress

### App service 測試

- `key_echo`
  - 一般鍵 -> app 會處理，系統不會收到
  - Windows `Num Lock` -> app 會處理，系統也會收到
- `nvda_remote`
  - Windows `Num Lock` -> 本機系統會收到，且不會轉送到遠端
  - 其他既有 controlling 行為不應回歸

## 設計理由

先前的設計之所以失敗，是因為它試圖用單一壓縮後的 decision 來同時表達：

- system pass-through 行為
- app handling semantics

這份 spec 透過以下方式修正：

- 將 system pass-through 明確化為邊界層關心的事項
- 將 app handling state 明確化為 app 層關心的事項
- 在最終 pipeline result 中同時保留這兩個維度

這樣得到的模型會更正確、更容易推理，也更容易在後續階段擴充。
