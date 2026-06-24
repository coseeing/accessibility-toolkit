# 數字鍵盤 NumLock HID 舊式 Payload 設計

## 問題

`nvda_remote` 目前在 `WindowsNativeKeyContext` 存在時，會直接把 Windows 鍵盤事件以原生
Windows 的 `vk_code`、`scan_code` 和 `extended` 值轉送到遠端。其他平台則會退回把 HID
usage 轉成同樣的 Windows 風格 payload。

這個退回路徑目前無法表達 Windows / NVDA 在 NumLock 關閉時，主方向鍵和數字鍵盤按鍵之間的
差異。例如：

- 主方向鍵向下：`vk=0x28`、`scan=80`、`extended=True`
- NumLock 關閉時的數字鍵盤 2：`vk=0x28`、`scan=80`、`extended=False`
- NumLock 開啟時的數字鍵盤 2：`vk=0x62`、`scan=80`、`extended=False`

NVDA 會用 `vk_code` 加上 `extended` 這組值來區分像 `downArrow`、`numpad2` 和
`numLockNumpad2` 這些手勢。少了這個差異，遠端 NVDA 就收不到預期的數字鍵盤手勢。

## 目標

在所有平台上，包含 Windows 在內，`nvda_remote` 轉送都能走 HID 到 Windows 風格 payload 的
路徑。Windows 上應可透過一個變數開關，選擇要直接轉送原生 `WindowsNativeKeyContext`
payload，或使用 HID 轉出的 payload。

HID 事件仍然保留為實體按鍵身分，而 `CapturedKeyEvent` 會帶上選出數字鍵盤正確
Windows 風格 payload 所需的可選 NumLock 狀態。

## 資料模型

在 `CapturedKeyEvent` 新增這個欄位：

```python
num_lock_on: bool | None = None
```

其意義如下：

- `True`：擷取來源知道 NumLock 是開啟的。
- `False`：擷取來源知道 NumLock 是關閉的。
- `None`：擷取來源沒有提供可靠的 NumLock 狀態。

`KeyEvent` 維持不變，仍然只代表 HID usage page、usage 與按下狀態。

替 `nvda_remote` 新增一個 Windows 轉送模式開關，例如：

```python
use_windows_native_key_payload: bool = False
```

其意義如下：

- `False`：即使在 Windows 上，也使用統一的 HID 到 Windows 風格 converter。
- `True`：保留目前 Windows 行為，在有 `WindowsNativeKeyContext` 時直接轉送其中的原生值。

預設值應為 `False`，讓新的跨平台路徑成為一般路徑。Windows 原生路徑則保留為明確啟用的相容或診斷模式。

## 轉送資料流

`nvda_remote` 的預設轉送流程改為：

```text
platform capture
-> CapturedKeyEvent(key_event=HID usage, num_lock_on=...)
-> legacy_payload_from_captured_event()
-> key_event_to_legacy_remote_payload(event, num_lock_on=...)
-> RemoteMessageType.KEY payload
```

當 `use_windows_native_key_payload=False` 時，`legacy_payload_from_captured_event()` 在這段
payload 轉換應忽略 `WindowsNativeKeyContext`，一律呼叫 HID converter。

當 `use_windows_native_key_payload=True` 且存在 `WindowsNativeKeyContext` 時，converter 應保留
目前 Windows 行為：

```text
platform capture
-> CapturedKeyEvent(key_event=HID usage, native_context=WindowsNativeKeyContext(...))
-> legacy_payload_from_captured_event(use_windows_native_key_payload=True)
-> native Windows vk_code / scan_code / extended payload
-> RemoteMessageType.KEY payload
```

`WindowsNativeKeyContext` 可以留在程式庫中，用於這個明確啟用的 Windows 原生模式、其他用途或
未來診斷。它不應成為預設 `nvda_remote` 轉送路徑的必要條件。

## 數字鍵盤對應規則

converter 應使用下列完整的數字鍵盤對照表：

| HID usage | `num_lock_on=True` | `num_lock_on=False` |
| --- | --- | --- |
| `KEYPAD_0` | `vk=0x60, scan=82, extended=False` | `vk=0x2D, scan=82, extended=False` |
| `KEYPAD_1` | `vk=0x61, scan=79, extended=False` | `vk=0x23, scan=79, extended=False` |
| `KEYPAD_2` | `vk=0x62, scan=80, extended=False` | `vk=0x28, scan=80, extended=False` |
| `KEYPAD_3` | `vk=0x63, scan=81, extended=False` | `vk=0x22, scan=81, extended=False` |
| `KEYPAD_4` | `vk=0x64, scan=75, extended=False` | `vk=0x25, scan=75, extended=False` |
| `KEYPAD_5` | `vk=0x65, scan=76, extended=False` | `vk=0x0C, scan=76, extended=False` |
| `KEYPAD_6` | `vk=0x66, scan=77, extended=False` | `vk=0x27, scan=77, extended=False` |
| `KEYPAD_7` | `vk=0x67, scan=71, extended=False` | `vk=0x24, scan=71, extended=False` |
| `KEYPAD_8` | `vk=0x68, scan=72, extended=False` | `vk=0x26, scan=72, extended=False` |
| `KEYPAD_9` | `vk=0x69, scan=73, extended=False` | `vk=0x21, scan=73, extended=False` |
| `KEYPAD_DECIMAL` | `vk=0x6E, scan=83, extended=False` | `vk=0x2E, scan=83, extended=False` |
| `KEYPAD_DIVIDE` | `vk=0x6F, scan=53, extended=True` | `vk=0x6F, scan=53, extended=True` |
| `KEYPAD_MULTIPLY` | `vk=0x6A, scan=55, extended=False` | `vk=0x6A, scan=55, extended=False` |
| `KEYPAD_SUBTRACT` | `vk=0x6D, scan=74, extended=False` | `vk=0x6D, scan=74, extended=False` |
| `KEYPAD_ADD` | `vk=0x6B, scan=78, extended=False` | `vk=0x6B, scan=78, extended=False` |
| `KEYPAD_ENTER` | `vk=0x0D, scan=28, extended=True` | `vk=0x0D, scan=28, extended=True` |
| `KEYPAD_EQUALS` | `vk=0xBB, scan=89, extended=False` | `vk=0xBB, scan=89, extended=False` |

說明：

- `KEYPAD_0..9` 與 `KEYPAD_DECIMAL` 會依 `num_lock_on` 改變 `vk_code`。
- 它們的 `scan_code` 在 NumLock 開關之間保持不變。
- 它們的 `extended` 也維持 `False`，讓 NVDA 看到的是數字鍵盤語意，而不是主導航區語意。
- `KEYPAD_DIVIDE`、`KEYPAD_MULTIPLY`、`KEYPAD_SUBTRACT`、`KEYPAD_ADD`、`KEYPAD_ENTER` 與
  `KEYPAD_EQUALS` 不論 `num_lock_on` 為何，都維持相同對應。
- `HID.NUM_LOCK` 本身也維持目前的對應，不使用 `num_lock_on`。

當 `num_lock_on is None` 時，維持現有的對應行為。實務上就是在尚未取得可靠 NumLock 狀態前，
先沿用 `legacy_key_payload.py` 目前對該 HID usage 的 mapping。

主方向鍵仍然要維持獨立。舉例來說，`HID.DOWN` 仍然應對應到
`vk=0x28`、`scan=80`、`extended=True`。

## 平台擷取行為

Windows 擷取應該讀取 `GetKeyState(VK_NUMLOCK)`，並在送出 captured event 時把
`CapturedKeyEvent.num_lock_on` 設成已知的布林值。

如果 macOS 目前沒有可靠的來源可取得 NumLock 狀態，可以先把 `num_lock_on` 設為 `None`。
這個欄位讓 macOS 之後可以在不改變轉送合約的前提下補上 NumLock 狀態。

## NumLock 轉送行為

在 `nvda_remote` 控制模式中，`HID.NUM_LOCK` 是特殊情況。它應該送到遠端，同時也要交給本機
系統處理。

這和一般遠端控制按鍵不同：

| 行為 | 送到遠端 | 交給本機系統 | Pipeline result |
| --- | --- | --- | --- |
| 一般遠端按鍵 | 是 | 否 | `send_to_system=False`, `app_result=HANDLED_STOP` |
| 控制模式中的 `HID.NUM_LOCK` | 是 | 是 | `send_to_system=True`, `app_result=HANDLED_STOP` |
| 非控制模式中的 `HID.NUM_LOCK` | 否 | 是 | `send_to_system=True`, `app_result=UNHANDLED` |

`HID.NUM_LOCK` 需要交給本機系統處理，因為本機 NumLock 狀態會用來替後續數字鍵盤事件填入
`CapturedKeyEvent.num_lock_on`。它也需要送到遠端，讓控制端可以改變遠端機器的 NumLock 狀態。

key down 和 key up 都應該轉送：

```text
HID.NUM_LOCK pressed=True  -> vk=0x90, scan=69, extended=True, pressed=True
HID.NUM_LOCK pressed=False -> vk=0x90, scan=69, extended=True, pressed=False
```

目前 `nvda_remote` 中過早回傳的 `should_pass_through_system_toggle()` 邏輯應調整，讓控制模式中的
`HID.NUM_LOCK` 可以走這個「轉送 + 交給本機系統」路徑。非控制模式可以維持目前只交給本機系統的行為。

## 測試

需要新增的重點測試：

- `HID.KEYPAD_0..9` 與 `HID.KEYPAD_DECIMAL` 在 `num_lock_on=True` 時的對應。
- `HID.KEYPAD_0..9` 與 `HID.KEYPAD_DECIMAL` 在 `num_lock_on=False` 時的對應。
- `HID.KEYPAD_0..9` 與 `HID.KEYPAD_DECIMAL` 在 `num_lock_on=None` 時維持現有行為。
- `HID.KEYPAD_DIVIDE`、`HID.KEYPAD_MULTIPLY`、`HID.KEYPAD_SUBTRACT`、`HID.KEYPAD_ADD`、
  `HID.KEYPAD_ENTER` 與 `HID.KEYPAD_EQUALS` 在 NumLock 開關下保持不變。
- 主方向鍵，特別是 `HID.DOWN`，仍然要對應到 `extended=True`。
- `legacy_payload_from_captured_event()` 在 `use_windows_native_key_payload=False` 時要忽略
  `WindowsNativeKeyContext`，並使用 HID 加上 `num_lock_on`。
- `legacy_payload_from_captured_event()` 在 `use_windows_native_key_payload=True` 且存在
  `WindowsNativeKeyContext` 時，要保留目前 Windows 原生 payload 行為。
- Windows 擷取要從 `GetKeyState(VK_NUMLOCK)` 填入 `CapturedKeyEvent.num_lock_on`。
- 控制模式中的 `HID.NUM_LOCK` key down 和 key up 要送到遠端，同時回傳 `send_to_system=True`。
- 非控制模式中的 `HID.NUM_LOCK` 要只交給本機系統，不送到遠端。
