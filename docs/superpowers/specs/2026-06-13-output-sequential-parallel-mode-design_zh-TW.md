# 輸出序列/平行模式設計

## 摘要

此設計為 `QueuedOutputService` 加入 `Sequential`（序列）/ `Parallel`（平行）輸出模式。序列模式下，連續的 `speak()` 呼叫保證透過共享排程器依序執行。平行模式（預設）下，每次 `speak()` 呼叫可能會中斷前一個語音。此設計透過建立 `shared_scheduler` 來奠定未來非語音輸出類型（tone、wave）的基礎：序列模式下由共享排程器將跨類型的輸出序列化，平行模式則讓各類型的專屬排程器獨立運作。

## 背景

目前的輸出鏈為：

```
QueuedOutputService  ← 面向 controller 的 protocol adapter
  └─ SpeechService   ← 後端切換、語音設定
       └─ pyttsx3 / nvda_controller  ← 使用 OutputScheduler 做序列內 chunk 排序
```

`pyttsx3` 與 `nvda_controller` 各自持有自己的 `OutputScheduler` reference，用於將語音序列內的個別 chunk 序列化（文字 → 停頓 → 文字）。目前沒有機制能強制不同 `speak()` 呼叫之間的順序。

`shared_scheduler` — 獨立於 backend 的 chunk 層級排程器 — 提供跨序列的序列化，而不干擾序列內的排序。

## 目標

- 在 `QueuedOutputService` 加入 `OutputMode.SEQUENTIAL` 與 `OutputMode.PARALLEL`
- 序列模式保證連續兩次 `speak()` 呼叫以 FIFO 順序執行
- 平行模式保留目前行為（向後相容的預設值）
- `cancel()` 清除 shared 與 speech 兩個排程器
- `shutdown()` 關閉兩個排程器
- 建立 `shared_scheduler` 模式，供未來 tone/wave 輸出類型使用

## 非目標

- 此階段不新增任何輸出類型（tone、wave）
- 不修改 `SpeechService`、`pyttsx3` 或 `nvda_controller`
- 不修改 app 層級的 `build_runtime()` 或 controller 程式碼
- 不在 UI 層整合模式切換（模式以程式方式設定）

## 架構

```
PARALLEL 模式（預設）：               SEQUENTIAL 模式：

speak("a") ──→ SpeechService          speak("a") ──→ shared_scheduler
                  │                                     │
                  ▼                                     ▼
              speech_scheduler              ┌─ speech_scheduler
              (chunk 排序)                  │   (chunk 排序)

speak("b") ──→ SpeechService              │
                  │                         speak("b") ──→ shared_scheduler（排隊中）
                  ▼                                     │
              speech_scheduler                         ▼
              (a 與 b 可能重疊)           ┌─ speech_scheduler
                                          │   (a 播完後才執行)
```

### 為何 shared scheduler 使用 `schedule(wait_done=False)` 就能保證順序？

`pyttsx3.speak(seq)` 是在 shared scheduler 的 worker thread 內同步呼叫的。在此呼叫過程中，它會**原子性**地將所有 chunk 任務塞入 speech scheduler 的 queue。因為 shared scheduler 一次只處理一個 job，`speak("a")` 的所有 chunk 一定在 `speak("b")` 的任何 chunk 之前抵達 speech scheduler，與 chunk 層級的 speech scheduler 何時執行無關。

兩個排程器之間不需要 `wait_done=True`、`notify_done()` 或任何完成回呼。順序保證來自 shared scheduler 的單執行緒 worker 一次只處理一個頂層 speak job。

## API

### `OutputMode`

```python
from enum import Enum

class OutputMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
```

### `QueuedOutputService`

```python
class QueuedOutputService:
    def __init__(self, *, speech: SpeechService) -> None:
        self._speech = speech
        self._mode = OutputMode.PARALLEL
        self._shared_scheduler = OutputScheduler()

    def set_mode(self, mode: OutputMode) -> None: ...
    def get_mode(self) -> OutputMode: ...

    def speak(self, sequence: SpeechSequence) -> None:
        # SEQUENTIAL：透過 shared_scheduler 排程
        # PARALLEL： 直接委派給 SpeechService（目前行為）

    def cancel(self) -> None:
        # 清除 shared_scheduler + SpeechService

    def shutdown(self) -> None:
        # cancel + SpeechService.shutdown() + shared_scheduler.shutdown()

    # 其餘所有方法（pause、語音設定等）不變 — 直接 pass-through 給 SpeechService
```

### 模式切換行為

在仍有任務排隊中時切換模式，**不會**回溯變更這些任務的路由。已在 `shared_scheduler` 中排隊的項目會依序完成。切換後新的 `speak()` 呼叫遵循新模式。

## 變更

| 檔案 | 變更 |
|---|---|
| `src/application/output_service.py` | 加入 `OutputMode` enum。加入 `_mode`、`_shared_scheduler` 欄位、`set_mode`/`get_mode`、`speak()` 條件路由、更新 `cancel()` 與 `shutdown()`。 |
| `tests/unit/test_output_service.py` | 加入測試：預設模式、`set_mode`/`get_mode`、序列順序保證、`cancel()` 清除 shared queue、`shutdown()` 清理 shared scheduler。 |

## 邊界情況

| 情況 | 行為 |
|---|---|
| 預設模式 | `PARALLEL` — 與目前行為完全相同 |
| SEQUENTIAL 模式下呼叫 `cancel()` | 清除 `shared_scheduler` queue 並呼叫 `SpeechService.cancel()` |
| shared queue 尚有任務時 `set_mode(PARALLEL)` | 已排隊項目仍依序執行；新呼叫直接送達 |
| `shutdown()` | 先 cancel 兩個排程器的任務，然後關閉 speech，最後關閉 shared |
| 只有 speech 輸出，尚無 tone/wave | `shared_scheduler` 作為跨 speak 序列的序列化器 — 實務上與序列內排序無功能差異，但建立了擴充點 |
| 只有 speech 時的 PARALLEL 模式 | 因為 speech 是唯一的輸出類型，所有 `speak()` 呼叫都走同一個 `speech_scheduler`，結果為 FIFO 排序。「平行」行為（各類型獨立排程器）只會在 tone/wave 加入後才變得可觀察。 |

## 測試

- `test_output_service.py` 中既有 3 個測試必須通過（預設 PARALLEL 模式）
- 新增測試：
  - `test_output_mode_enum` — `SEQUENTIAL` 與 `PARALLEL` 的值
  - `test_default_mode_is_parallel` — `get_mode()` 回傳 `PARALLEL`
  - `test_set_and_get_mode` — 兩個值的來回設定
  - `test_sequential_orders_consecutive_speak_calls` — 兩次 `speak()` 呼叫以 FIFO 順序抵達 backend
  - `test_cancel_in_sequential_clears_shared_queue` — 排隊中的 sequential speak 在 cancel 後永不執行
  - `test_shutdown_stops_shared_scheduler` — `shared_scheduler` worker thread 停止
