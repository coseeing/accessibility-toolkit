# Input/Output 解偶與 Key Echo Demo 設計

## 背景

目前專案中的輸入、輸出與 NVDA Remote 業務邏輯存在明顯耦合。

- `ClientController` 同時管理連線狀態、鍵盤輸入流程、遠端訊息路由、speech backend 控制。
- `WindowsKeyboardCapture` 與 speech outputs 雖然本質上可重用，但目前主要透過 `ClientController` 被 NVDA Remote 業務綁定。
- `SpeechBackendManager` 目前主要扮演 UI 組裝期 helper，尚未成為可被多個 app 共用的正式 output service。

未來需求不是只有 NVDA Remote。這套程式還需要支援其他 business 邏輯，因此 input/output 應被視為共享基礎能力，而不是 remote 專屬的一部分。

本次先以一個最小 demo 驗證方向：

- 保留現有 `nvda_remote` app
- 新增獨立的 `key_echo` app
- 兩者共用同一套鍵盤擷取與語音輸出能力
- `key_echo` 在收到 keydown 時讀出按下按鍵的 `vk code`

## 目標

本次設計目標如下：

1. 將輸入擷取與輸出能力從 NVDA Remote 業務邏輯中拆開。
2. 讓 `WindowsKeyboardCapture`、speech output adapters 可被不同 app 共用。
3. 以新 app `key_echo` 證明同一套 input/output 可支援另一個 business。
4. 將 speech backend 管理提升為共通 `SpeechService`。
5. 預留 tone / braille handler 介面，但本次不實作其輸出。
6. 讓 `ClientController` 退場，由 app-specific service 取代。

## 非目標

以下內容不在本次範圍：

- 重新設計所有 UI 組件或共通 UI 元件抽取
- tone output 或 braille output 的實際 adapter 實作
- 建立大型 plugin/discovery 機制
- 將整個 repo 一次完整改造成多 app monorepo 結構
- 抽出共通 `BaseAppService`

## 設計原則

### 1. Input 層只產生事件

input 基礎層的責任是忠實提供鍵盤事件，例如：

- `vk`
- `scan`
- `pressed`

它不應該預設哪些事件有意義，也不應該內建業務規則。`keydown` / `keyup` 的過濾應由 business handler 決定。

### 2. Output 層只提供能力

speech / tone / braille adapters 的責任是提供輸出能力，而不是理解 remote protocol 或 app-specific 規則。

### 3. App service 是唯一理解業務規則的地方

每個 app 應由自己的 app service 負責：

- 如何解讀 `KeyEvent`
- 何時要轉發 remote key
- 何時要本地報讀
- 何時要忽略 `keyup`

### 4. Composition root 只負責組裝

每個 app 的 `main` 入口只負責 wiring，不承載業務規則。

## 架構方向

本次採用 `2.5` 路線：

- 實作主軸是 use-case 拆分
- 新增的入口與 wiring 則直接朝 app module 的形狀設計

這代表本次不只是抽幾個 class，而是讓新 app 與重構後的 NVDA Remote 都改用一致的 app-level 組裝模式。

## 模組邊界

### Shared adapters

此區放可被多個 app 重用的外部能力：

- `WindowsKeyboardCapture`
- `WindowsHotkeyCapture`，若未來有跨 app 共用需求
- `NvdaControllerSpeechOutput`
- `Pyttsx3SpeechOutput`
- 未來的 tone / braille adapters

這些元件不應知道自己正在服務 `nvda_remote` 或 `key_echo`。

### Application

此區放共通事件與 capability 邊界：

- `KeyEventHandler`
- `KeyboardInputService`
- `OutputCapabilities`
- `SpeechService`

這一層不包含 remote 協定細節。

### apps/nvda_remote

此區只放 NVDA Remote 專屬邏輯：

- `NvdaRemoteAppService`
- remote session
- message router
- relay transport
- connection/control state 規則
- remote clipboard 規則

### apps/key_echo

此區只放 key echo 專屬邏輯：

- `KeyEchoAppService`
- `key_echo` 入口

## 新增的核心介面與物件

### `KeyEventHandler`

用途：業務層處理鍵盤事件的統一介面。

建議介面：

```python
class KeyEventHandler(Protocol):
    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision: ...
```

說明：

- `nvda_remote` 與 `key_echo` 都實作這個介面
- input service 只知道它把事件交給某個 handler

### `KeyboardInputService`

用途：在 `InputCapture` 與 `KeyEventHandler` 之間提供薄協調層。

責任：

- 綁定 `input_capture.set_listener(...)`
- 啟停 capture
- 將收到的 `KeyEvent` 轉交給當前 handler

不負責：

- remote protocol
- speech 行為
- 過濾 keydown/keyup 的業務判斷

### `SpeechService`

用途：提供單一、穩定的共通 speech façade。

責任分成三類：

1. 播放能力

- `speak(sequence)`
- `cancel()`
- `pause(is_paused)`

2. backend 管理

- `get_backend_options()`
- `get_selected_backend()`
- `set_backend(backend_id)`

3. 目前 backend 的參數控制

- `list_voices()`
- `get_voice()` / `set_voice()`
- `get_rate()` / `set_rate()`
- `get_pitch()` / `set_pitch()`
- `get_volume()` / `set_volume()`

`SpeechBackendManager` 會被提升或吸收到這個服務中，不再只是 UI wiring helper。

### `OutputCapabilities`

用途：聚合 app 可用的輸出能力。

建議形狀：

```python
@dataclass
class OutputCapabilities:
    speech: SpeechService
    tone: ToneOutput | None = None
    braille: BrailleOutput | None = None
```

說明：

- `speech` 不是 `SpeechOutput`，而是較高階的 `SpeechService`
- `tone` / `braille` 本次先預留能力欄位

## App-specific services

### `NvdaRemoteAppService`

此物件取代 `ClientController`，成為 NVDA Remote app 的核心 service。

它的責任：

- 管理 connect / disconnect
- 管理 start_control / stop_control
- 管理 hotkey toggle
- 處理本地鍵盤事件並決定是否 forward/suppress
- 接收 transport 訊息
- 協調 remote session / message router
- 接收遠端 speech / cancel / pause / clipboard
- 使用 `SpeechService` 進行本地 speech 輸出

它不應再直接擁有：

- speech backend 切換規則本身
- voice / rate / pitch / volume 的具體實作

這些應透過 `SpeechService` 完成。

### `KeyEchoAppService`

此物件是新的 demo app 核心 service。

它也實作 `KeyEventHandler`，但不碰 remote 類別。

行為規則：

- 所有 `keydown` / `keyup` 事件都會收到
- 只有 `pressed=True` 時觸發 speech
- 組出的語音內容先固定為 `VK {event.vk}`
- `keyup` 不播放 speech
- tone / braille 欄位先保留，但本次不輸出

回傳決策：

- 所有事件都回傳 `PASS_THROUGH`

理由：

- demo 目的是展示 input/output 可重用
- 不應讓它變成鍵盤接管工具
- 按鍵照常送到目前焦點程式，同時本地報讀

## `ClientController` 退場策略

本次不保留 `ClientController` 作為 façade，而是直接讓它退場。

新的結構中：

- `NvdaRemoteAppService` 取代其 app-specific 職責
- `KeyboardInputService` 取代其 input 綁定職責
- `SpeechService` 取代其 speech control façade 職責

## 現有責任搬移對照

### 從 `ClientController` 搬到 `NvdaRemoteAppService`

- `connect()` / `disconnect()`
- `start_control()` / `stop_control()`
- `_forward_key_event()`
- `_handle_transport_message()`
- `_on_status()`
- hotkey toggle 邏輯
- remote clipboard push 規則
- remote message routing 協調

### 從 `ClientController` 搬到 `SpeechService`

- speech backend 切換
- voice / rate / pitch / volume 的查詢與設定
- speak / cancel / pause 的統一 façade

### 從 `ClientController` 搬到 `KeyboardInputService`

- `input_capture.set_listener(...)`
- capture start/stop 協調

### `OutputManager` 的處理

`OutputManager` 不應保留現狀。

原因：

- 它目前價值過薄
- 還夾帶了 remote clipboard 送出行為
- 邊界不夠乾淨

本次建議：

- 不再把它作為共通核心
- app service 直接透過 `OutputCapabilities` 使用 speech/tone/braille
- remote clipboard 由 `NvdaRemoteAppService` 自己管理

## Key Echo Demo 設計

### 入口

新增獨立入口，例如：

- `src/apps/key_echo/main.py`

此入口負責：

- 建立 `WindowsKeyboardCapture`
- 建立 `SpeechService`
- 建立 `KeyEchoAppService`
- 建立 `KeyboardInputService`
- 啟動 capture

### 行為

啟動後：

- 持續監聽鍵盤
- `keydown` 時報讀 `vk code`
- `keyup` 不報讀
- 所有按鍵仍 pass through

### 語音內容

初版固定讀法：

- `"VK 65"`
- `"VK 112"`

本次不做：

- 按鍵名稱本地化
- scan code 報讀
- 組合鍵語意化報讀

## NVDA Remote App 行為保留要求

重構後，`nvda_remote` 必須保留以下能力：

1. 可連線與斷線
2. 可開始與停止 control
3. 可接收遠端 speech
4. 可切換 speech backend
5. 可操作 voice / rate / pitch / volume
6. remote transport 與協定邏輯只存在於 `nvda_remote`

## 錯誤處理原則

### `SpeechService`

- 如果切換到不存在的 backend，應回傳明確錯誤
- 如果 backend 建立失敗，應讓 app 得知目前 speech unavailable
- speech backend 內部例外應在 adapter/service 層被記錄，不讓 app service 因單次播放崩潰

### `KeyboardInputService`

- 如果 capture 無法啟動，應將錯誤直接回傳給 app 入口
- input service 不吞掉無法安裝 hook 的錯誤

### `KeyEchoAppService`

- 若 `speech` 不可用，事件仍應回傳 `PASS_THROUGH`
- 不因 speech 播放失敗而阻斷輸入事件處理

### `NvdaRemoteAppService`

- 保留現有連線與 transport 錯誤邏輯
- 將 remote-specific 例外限制在 app 邊界，不污染 shared input/output

## 測試策略

### 單元測試

1. `KeyboardInputService`
- 驗證會將 capture 事件轉交給 handler
- 驗證 start/stop 會呼叫 capture 對應方法

2. `SpeechService`
- 驗證 backend 切換
- 驗證 speech control API 轉發到 current backend
- 驗證 unknown backend 的錯誤處理

3. `KeyEchoAppService`
- 驗證 `keydown` 時會呼叫 `speech.speak(...)`
- 驗證 `keyup` 時不會播放
- 驗證永遠回傳 `PASS_THROUGH`

4. `NvdaRemoteAppService`
- 驗證 key forwarding / suppress 規則仍符合原行為
- 驗證 remote speech/cancel/pause 流程仍可導到 `SpeechService`

### 整合測試

1. `key_echo` app wiring
- 用假的 capture 與假的 speech service 驗證整條輸入到輸出鏈路

2. `nvda_remote` app wiring
- 驗證 remote payload -> router -> speech service 流程仍成立

## 驗收標準

1. `nvda_remote` 既有主要流程不變
- 仍可連線
- 仍可開始/停止 control
- 仍可接收遠端 speech
- 仍可切換 speech backend

2. `key_echo` 可獨立啟動
- 不依賴 remote transport
- 啟動後開始接收鍵盤事件

3. `key_echo` 在 `keydown` 時會報讀 vk code
- 例如按下 `A`，會念出對應 vk 數值
- `keyup` 不發 speech

4. 共享邊界成立
- `WindowsKeyboardCapture` 不知道自己服務哪個 app
- `SpeechService` 可同時被 `nvda_remote` 與 `key_echo` 使用
- `RelayTransport` 只留在 `nvda_remote`

5. tone / braille 擴充點已存在
- app service constructor 可接受這些 capability
- 本次不要求實作輸出行為

## 實作順序建議

1. 新增 `SpeechService`
2. 新增 `KeyEventHandler` 與 `KeyboardInputService`
3. 建立 `OutputCapabilities`
4. 建立 `KeyEchoAppService` 與獨立入口
5. 將 `ClientController` 的 NVDA Remote 職責搬到 `NvdaRemoteAppService`
6. 調整現有 UI 與 wiring 改接新 service
7. 移除 `ClientController`

## 開放決策

本次已明確決定以下事項：

- 採 `2.5` 路線，而非保守局部拆分
- `ClientController` 直接退場
- `SpeechBackendManager` 升級為完整 `SpeechService`
- `key_echo` 使用獨立新入口
- `keydown` / `keyup` 都由 input 層提供
- `key_echo` 僅在 `keydown` 時報讀
- `key_echo` 所有按鍵預設 pass through
- tone / braille 先保留 handler/capability，不做實作

