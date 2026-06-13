# Output 三層架構說明

`KeyEchoRuntime`（以及 `NvdaRemoteRuntime`）中有三個與 speech output 相關的欄位，它們形成逐層封裝的架構：

## 層級總覽

```
QueuedOutputService  ← facade 給 controller 用
  ├─ SpeechService   ← backend 管理與切換
  │    └─ SpeechBackendManager → pyttsx3 / NVDA Controller
  └─ OutputScheduler ← worker thread 序列化排程
```

---

## 1. `OutputScheduler` — 排程引擎

- **位置**：`src/application/output_scheduler.py:77`
- **職責**：在獨立 daemon thread 中**序列化**所有 speech 任務，確保一次只有一個在執行
- **核心機制**：
  - `schedule(owner, action)` — 將任務放入 FIFO queue，worker thread 逐一取出執行
  - `CancellationToken` — 可中途取消正在執行或排隊中的任務
  - `OutputFuture` — 支援 `.then()` chaining 的 Future，可在任務完成後串接下一步
  - `schedule_break(owner, seconds)` — 插入靜音間隔（break between chunks）
  - `cancel_current()` / `cancel_all()` — 取消當前或所有排隊任務
- **它不關心** speech 內容是什麼，只負責何時執行、可否取消、順序控制

## 2. `SpeechService` — 後端管理

- **位置**：`src/application/speech_service.py:6`
- **職責**：管理 **speech backend**（pyttsx3 TTS 引擎 vs NVDA Controller），負責 backend 切換以及 voice/rate/pitch/volume 設定
- **核心機制**：
  - 內部持有 `SpeechBackendManager`（`src/application/speech_backends.py:14`）
  - `speak(sequence)` → 委派給當前 backend 的 `speak()`
  - `cancel()` / `pause()` → 委派給當前 backend
  - `set_backend(id)` → 切換 backend 時會先 cancel 舊的再建立新的
  - `list_voices()` / `get_voice()` / `set_voice()` 等設定 API
- **它不關心** 排程與序列化

## 3. `QueuedOutputService` — 對外統一介面

- **位置**：`src/application/output_service.py:28`
- **職責**：實作 `SpeechOutputService` protocol，作為 controller（`NvdaRemoteAppService` / `KeyEchoAppService`）的唯一 speech 入口，隔離 controller 與 `SpeechService` 的相依
- **目前實作**：pure pass-through decorator
  - `speak()` / `cancel()` / `pause()` → 直接委派給內部 `SpeechService`
  - 所有 voice/rate/pitch/volume 設定 → 委派給 `SpeechService`
  - `shutdown()` → cancel 當前 speech + `scheduler.shutdown()`
- **排程實際路徑**：`QueuedOutputService.speak()` 本身沒有直接呼叫 scheduler，但背後 `SpeechService` → `pyttsx3.speak()` 會在**同一個** scheduler 上做 `add_speak_task()` 排程，所以序列化效果是有的，只是邏輯落在 backend 層而非這一層
- 它持有 `OutputScheduler` 的 reference 只為了 `shutdown()` 時能關閉 worker thread

## Scheduler 的兩個注入點

同一個 `OutputScheduler` instance 被注入到兩處：

```
QueuedOutputService ─── 持有 scheduler (shutdown 用)
         │
         ▼
    SpeechService ─── 不認識 scheduler
         │
         ▼
    pyttsx3 / nvda ─── 持有 scheduler (add_speak_task / notify_done 用)
```

## 為何分三層？

| 層 | 關注點 | 若無此層會怎樣 |
|---|---|---|
| `OutputScheduler` | 並行控制：誰先誰後、可否取消、timeout | 多個 `speak()` 同時呼叫會互相覆蓋，無法確保順序 |
| `SpeechService` | 後端抽象：pyttsx3 / NVDA Controller 切換、語音設定 | controller 需要知道後端細節，無法執行期切換 TTS 引擎 |
| `QueuedOutputService` | 對外合約：統一的 `SpeechOutputService` protocol，隔離 controller | controller 直接依賴 `SpeechService`，耦合度上升 |

## 潛在簡化方向

`QueuedOutputService` 是最薄的一層，排程能力是 backend 提供而非它提供。兩個方向可選：

1. **保留 `QueuedOutputService`**：維持現狀，作為 protocol adapter 隔離 controller 與 backend 實作細節；命名保留了未來加入 tone/wave play 等非語音輸出的擴充空間
2. **拔掉 `QueuedOutputService`**：讓 controller 直接依賴 `SpeechService`，但需要另尋 `scheduler.shutdown()` 的呼叫點
