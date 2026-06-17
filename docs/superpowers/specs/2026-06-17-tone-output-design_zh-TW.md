# Tone 輸出設計

日期：2026-06-17

## 目標

在 client 中加入真正可用的 tone 輸出，並讓 `nvda_remote` 支援遠端 tone 播放，同時維持與現行 NVDA Remote 行為相容的協定。

這項工作必須滿足以下需求：

- 其他 client 傳來的遠端 tone 會在本機播放。
- `nvda_remote` 使用的線上協定格式要和 NVDA Remote 既有的 `TONE` 訊息形狀一致。
- tone 播放只使用預設輸出裝置。
- repository 內不得匯入 NVDA runtime 相依模組。
- 語音序列化仍維持只處理 speech；tone 不加入 `SpeechSequence`。

## 現況

這個 repository 目前已經把輸出能力拆開：

- `speech` 透過 `SpeechSequence` 建模並傳輸。
- `tone` 以可選 capability 的形式存在於 `OutputCapabilities`。
- `braille` 也獨立分離。

但 tone 支援目前還不完整：

- `src/adapters/outputs/tone.py` 目前只是 logging stub。
- `src/interop/protocol/messages.py` 的遠端協定還沒有 tone 訊息。
- message router 與 output manager 都沒有處理 tone 的路徑。
- `access8graph` 目前可以要求本機播放失敗提示音，但前提是有注入真正的 `ToneOutput`。

## NVDA 相容性限制

這次實作應遵循 NVDA 目前對 speech 與 tone 的分工：

- NVDA Remote 使用 `RemoteMessageType.TONE = "tone"`。
- tone payload 使用 `hz`、`length`、`left`、`right`。
- 遠端 tone 與遠端 speech 分開處理。
- NVDA 不會把 tone 建模成 `SPEAK` 使用的 speech sequence 內部 command。

因此，這個 repo 在 `nvda_remote` 上應比照這種做法，而不是另外引入像 `BEEP` 這樣的新訊息型別，或是在 speech serialization 中加入人工定義的 `BeepCommand`。

## 建議做法

新增專用的遠端 `TONE` 訊息，以及真正可播放的 `ToneOutput` backend。

選這個做法的原因：

- 它與 NVDA Remote 現有的協定形狀與語意一致。
- 它能維持 `speech` 與 `tone` 的責任邊界清楚。
- 它符合目前 `OutputCapabilities` 的設計。
- 它也讓未來擴充其他輸出類型更直接，例如 `WAVE`，而不用把不相干的輸出硬塞進 speech model。

不採用的替代方案：

- 把 `BeepCommand` 加進 `SpeechSequence`：這會把非 speech 行為混進 speech model，也會偏離 NVDA Remote 的做法。
- 現在就引入通用 output event envelope：這會增加抽象層，但沒有解決眼前更具體的問題。

## 設計

### 1. Tone backend

將 `src/adapters/outputs/tone.py` 裡的 logging stub，替換成真正可用的實作：產生 PCM samples，並透過平台的預設音訊輸出裝置播放。

設計限制：

- 不得依賴 NVDA runtime 模組，例如 `config`、`extensionPoints`、`nvwave`、`NVDAHelper.localLib`。
- 可以重用 `ref/nvda/source/tones.py` 的高層次演算法，但 runtime 整合部分必須改寫成適合本 repository 的版本。
- 輸出裝置一律使用預設裝置，不新增 tone 輸出裝置設定。
- 實作必須支援 `left` 與 `right` 的立體聲平衡。
- 播放前應先對無效值與邊界值做防禦性正規化。

預期 backend 行為：

- `hz` 會轉成固定取樣率下可播放的波形。
- `length` 控制毫秒級的持續時間。
- `left` 與 `right` 會分別調整左右聲道振幅。
- backend 若播放失敗，只記錄 log，不得讓 app 或 network session 崩潰。

### 2. 協定

擴充 `src/interop/protocol/messages.py`，加入：

- `RemoteMessageType.TONE = "tone"`

Payload 結構：

- `hz`：以赫茲表示的數值頻率
- `length`：以毫秒表示的數值長度
- `left`：左聲道音量數值，慣例範圍 `0..100`
- `right`：右聲道音量數值，慣例範圍 `0..100`

這個形狀會刻意與 NVDA Remote 對齊。

### 3. 路由

擴充 `src/interop/protocol/routing/message_router.py`，加入專門處理 tone 的路徑：

- 在 `MessageRouter.__init__` 新增 `on_tone` callback
- 處理 `RemoteMessageType.TONE`
- 驗證並正規化 payload
- 將有效值轉送給 callback
- 對格式錯誤的 payload，沿用既有的 `invalid_message` status 回報路徑

驗證規則：

- `hz`、`length`、`left`、`right` 必須可轉成數值
- 最終播放值應限制在安全範圍內
- 若欄位無法轉型，該訊息視為 invalid

Tone 訊息不需要額外的 serializer hook，因為它們是一般 JSON payload，不像 `SPEAK` 需要還原 speech sequence。

### 4. Output manager 與 capabilities

擴充 `src/application/services.py`，讓 `OutputManager` 除了 speech 與 clipboard 外，也能處理 tone：

- 接受可選的 `tone_output`
- 新增 `handle_tone(hz, length, left, right)`
- 若沒有設定 tone backend，則 noop

這樣可以保留目前只配置 speech 的 runtime 或測試行為。

`OutputCapabilities` 已經有可選的 `tone` 欄位，因此不需要重新設計這個 model。

### 5. Runtime 組裝

更新 runtime/bootstrap 的組裝方式，讓相關 app 能拿到真正的 tone backend：

- `nvda_remote` 應注入真正的 `tone` capability，讓遠端 `TONE` 訊息可在本機播放
- `access8graph` 也應共用同一個 backend，讓它的本機失敗提示音真的會出聲
- 其他 app 若目前不需要，可以繼續不設定 `tone`

這次變更不包含 UI 或 config 工作：

- 不提供 tone 裝置選擇器
- 不儲存 tone backend 選擇
- 不新增 tone 設定畫面

### 6. 範圍邊界

這份設計刻意不做以下事情：

- 不把 tone command 加進 `SpeechSequence`
- 不變更既有 speech serializer 行為，除了原本就有的 speech 支援外不再擴充
- 不加入 wave 播放的遠端轉送
- 不加入可由使用者設定的 tone 輸出路由

## 資料流

### 遠端 tone 播放

1. 遠端 peer 傳送 `type: "tone"`，並附上 `hz`、`length`、`left`、`right`。
2. 本地 transport 將 JSON payload 反序列化。
3. `MessageRouter` 辨識到 `RemoteMessageType.TONE`。
4. router 驗證 payload，並呼叫 `on_tone(hz, length, left, right)`。
5. `OutputManager.handle_tone(...)` 將請求轉送給已設定的 `ToneOutput`。
6. 本地 tone backend 透過預設輸出裝置播放該 beep。

### 本機 app 的 tone 播放

1. 像 `access8graph` 這樣的 app 呼叫 `outputs.tone.beep(...)`。
2. 共用的 tone backend 會在本機播放該 tone。

## 錯誤處理

Tone 相關失敗不得影響 app 穩定性。

規則如下：

- 缺少 tone capability：noop。
- 遠端 payload 無效：送出 `invalid_message` status event。
- 播放 backend 發生例外：記錄 log 後返回。
- 數值不支援或不合理：安全地 clamp 或直接短路返回。

這與目前 repository 對輸出行為的整體偏好一致，也就是優先確保韌性。

## 測試策略

### 單元測試

新增或擴充以下測試：

- `RemoteMessageType.TONE` 是否存在，以及 router 是否會正確 dispatch
- router 對 tone 訊息的 invalid payload 處理
- `OutputManager.handle_tone(...)`
- `nvda_remote` service 收到遠端 tone 時的行為
- `access8graph` 使用真正 backend contract 時的本機 tone 行為
- tone backend 的參數正規化與失敗處理

### 整合層信心

若單元測試已能證明以下事項，這次實作就不一定需要很重的音訊整合測試：

- 協定路徑能正確 dispatch
- runtime 會在需要的地方組裝真正的 tone backend
- backend 對受限輸入能產生預期的呼叫或 buffer

## 實作備註

實作時應優先遵循目前 repository 的結構：

- 協定變更留在 `src/interop/protocol`
- 播放實作留在 `src/adapters/outputs`
- 協調與組裝變更留在 `src/application` 與 app runtime assembly

在移植 NVDA 的 tone 產生邏輯時，應盡量縮小複製範圍，並把 repository 專屬調整隔離在這個 repo 的 tone adapter 內，讓相依邊界維持清楚。

## 已確認的開放決策

以下決策已在 brainstorming 過程中確認：

- 必須支援遠端 tone 播放
- `nvda_remote` 協定必須與現有 NVDA Remote 行為一致
- 使用 `TONE`，不是新建 `BEEP` 訊息
- 不新增 speech `BeepCommand`
- tone 一律使用預設音訊輸出裝置

## 成功條件

當以下條件都成立時，這項工作就算完成：

- `nvda_remote` 收到遠端 `tone` 訊息時，會在本機播放
- `access8graph` 的本機失敗提示音也會透過同一個 backend 發聲
- tone 播放所用的協定名稱與 payload 形狀都與 NVDA Remote 一致
- tone 播放不依賴 NVDA runtime
- 既有 speech transport 行為維持不變
