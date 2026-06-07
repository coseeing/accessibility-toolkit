# Speech Backend Selection Design

## 概述

本文件定義一個功能：讓 Windows GUI 在執行中選擇並切換本機語音輸出後端。這個功能適用於獨立運作的 NVDA Remote client，且不影響 relay 連線、鍵盤轉送、剪貼簿同步或 session 狀態。

GUI 會提供一個下拉選單，且只會有兩個後端選項：

- `NVDA Controller`
- `pyttsx3`

在 relay session 已經連線的狀態下，使用者仍然可以切換目前使用的後端。切換時必須乾淨地停止目前正在使用的語音輸出，並把後續的 `SPEAK`、`CANCEL`、`PAUSE_SPEECH` 請求改送到新的後端，不需要重新連線 relay。

## 目標

- 讓使用者能在 Windows GUI 中選擇本機語音後端。
- 支援在已連線狀態下即時切換後端。
- 維持 relay/session/control 邏輯與具體語音後端實作的獨立性。
- 保留既有的 `SpeechOutput` 抽象介面。
- 在本機有執行 NVDA 時，仍可繼續使用 `NVDA Controller`。
- 提供獨立於 NVDA 的 `pyttsx3` 後端。

## V1 不包含的範圍

- 加入自動偵測後端或 `auto` 模式。
- 加入 macOS 或 Linux 的語音後端。
- 修改 NVDA Remote protocol。
- 修改鍵盤擷取、熱鍵處理或剪貼簿同步行為。
- 在應用程式其他地方另外再加入第二套語音後端選擇 UI。

## 建議架構

建議採用一個簡單的 application 層後端管理器，外加兩個具體的語音輸出 adapter。

### 分層

#### `interop`

核心的 protocol/session/routing 職責維持不變，只是 `CANCEL` 與 `PAUSE_SPEECH` 仍然會路由到統一的語音輸出介面。

職責維持如下：

- 解碼 inbound protocol message
- 將 `SPEAK`、`CANCEL`、`PAUSE_SPEECH` 與 clipboard message 路由到 application service
- 保持 protocol 邏輯與 GUI、平台 API 相互獨立

#### `application`

新增一個語音後端管理器，負責目前正在使用的語音輸出實作。

職責：

- 保存目前選到的 backend id
- 建立並替換目前 active 的 `SpeechOutput` backend
- 在切換後端時取消舊輸出
- 對 UI 暴露目前 active backend 的名稱與狀態

#### `adapters`

新增具體的 Windows 語音後端實作：

- `NvdaControllerSpeechOutput`
- `Pyttsx3SpeechOutput`

#### `ui`

新增一個下拉選單，列出兩個支援的後端。

職責：

- 顯示可用的後端清單
- 當使用者變更選項時通知 controller
- 顯示目前選到的後端

## 語音後端模型

### Backend ID

使用穩定的內部 backend id，不直接把 UI label 當成資料儲存。

- `nvda_controller`
- `pyttsx3`

UI 可以顯示使用者可讀的標籤，但 application 層內部與持久化都應使用 backend id。

### 後端切換規則

- 下拉選單永遠顯示兩個選項。
- Windows 上的預設選項是 `NVDA Controller`。
- 在連線中切換下拉選單必須立即生效。
- 切換離開目前後端時，必須先呼叫該後端的 `cancel()`，避免舊語音殘留。
- 切換後端時，不可斷開 relay 連線，也不可重設控制狀態。

## 執行流程

### 初始啟動

1. UI 初始化語音後端下拉選單。
2. Application 依照目前選擇的 backend id 建立初始語音後端。
3. 目前的 `SpeechOutput` 會被傳入 controller 與 output manager。
4. relay session 的行為維持不變。

### 執行中切換

1. 使用者在連線中或未連線時變更下拉選單。
2. UI 將新的 backend id 傳給 application layer。
3. Application layer 呼叫目前 backend 的 `cancel()`。
4. Application layer 建立新的 backend。
5. controller 與 output manager 之後的所有 `SPEAK`、`CANCEL`、`PAUSE_SPEECH` 都會走新的 backend。
6. relay session 維持連線。

### Inbound Speech Flow

1. Transport 收到 `SPEAK` message。
2. `MessageRouter` 將它正規化成 `NormalizedSpeech`。
3. `OutputManager` 把正規化後的 speech 傳給目前 active backend。
4. 目前的 backend 負責實際朗讀文字。

### Inbound Cancel/Pause Flow

1. Transport 收到 `CANCEL` 或 `PAUSE_SPEECH` message。
2. `MessageRouter` 將請求交給 application 的 output manager。
3. 目前的 backend 收到 `cancel()` 或 `pause(is_paused)`。

## 後端規格

### `NvdaControllerSpeechOutput`

這個後端保留目前 NVDA controller DLL 的整合方式。

職責：

- 透過既有 runtime resource path 載入 vendored NVDA controller DLL
- 透過 NVDA controller API 朗讀正規化文字
- 在需要時取消目前語音

備註：

- 當使用者想讓 NVDA 處理本機語音時，這個後端維持優先。
- 它仍然需要本機 NVDA 正在執行，才會真的有語音輸出。

### `Pyttsx3SpeechOutput`

這個後端透過 `pyttsx3` 提供本機系統 TTS。

職責：

- 初始化系統 TTS engine
- 使用本機 Windows 的語音引擎朗讀正規化文字
- 在呼叫 `cancel()` 時停止目前語音
- 對 `pause(is_paused)` 提供 best-effort 行為；如果 engine 不支援真正 pause/resume，則需明確文件化限制，並視為 no-op 或 stop-only

備註：

- 這個後端的設計目標是不需要本機 NVDA 也能運作。
- 它不應依賴 NVDA controller DLL。

## UI 設計

### 下拉選單

在 Windows 主視窗中加入一個標示清楚的下拉選單，位置可放在連線控制區附近。

下拉選單項目為：

- `NVDA Controller`
- `pyttsx3`

這個控制項應該：

- 預設為目前設定的 backend
- 在連線中保持可用
- 當使用者選擇不同項目時立即套用

### 狀態處理

UI 不應該在使用者不知情的情況下自行切換 backend。

建議行為：

- 切換成功時，下拉選單維持在新選項。
- 切換失敗時，維持舊 backend 並顯示錯誤對話框。
- 如果啟動時目前 backend 無法使用，應清楚提示錯誤，只有在 application 明確選擇時才做 fallback。

## 設定

將選擇的 backend id 持久化到 client 設定檔，讓使用者重新啟動時能保留選擇。

建議持久化規則：

- 儲存 backend id，不儲存 UI label
- 啟動時讀取已儲存的 backend id
- 如果讀到未知值，回退到 `nvda_controller`

## 錯誤處理

- 如果選到 `NVDA Controller` 但 DLL 無法載入，應顯示清楚的錯誤訊息，並保留目前 backend。
- 如果 `pyttsx3` 初始化失敗，應顯示清楚的錯誤訊息，並保留目前 backend。
- 如果切換時有語音正在播放，必須先取消舊 backend，再建立新 backend。
- 如果新 backend 初始化失敗，必須還原舊 backend 並繼續運作。

## 測試策略

### 單元測試

- backend 選擇與 backend id 持久化
- UI 下拉選單事件有正確送到 controller / application 層
- 執行中切換 backend 時會取消上一個 backend
- `NvdaControllerSpeechOutput` 仍可正確 speak 與 cancel
- `Pyttsx3SpeechOutput` 可正確 speak 與 stop

### 整合測試

- 以 `NVDA Controller` 啟動，切換到 `pyttsx3`，確認後續語音路由到新 backend
- 以 `pyttsx3` 啟動，切換到 `NVDA Controller`，確認不斷線也能切換路由
- 驗證切換後 `CANCEL` 仍能中斷目前語音

### Windows 手動檢查

- 連線到 relay session 後確認下拉選單可見
- 在語音播放中從 `NVDA Controller` 切到 `pyttsx3`
- 在已連線狀態下切回 `NVDA Controller`
- 確認 backend 變更過程中 relay 連線仍然維持
- 確認鍵盤與剪貼簿行為不受影響

## 實作備註

- speech backend manager 應該放在 `application` 層，不要放在 `ui`。
- backend 專用程式碼要隔離在 `adapters`。
- 不要讓 UI 直接 instantiate backend 實作。
- 保留既有的 `SpeechOutput` 介面，讓 router / output manager 可以維持穩定。
- 維持 vendored DLL 載入的 runtime resource helper；新的 system TTS backend 不應依賴它。
