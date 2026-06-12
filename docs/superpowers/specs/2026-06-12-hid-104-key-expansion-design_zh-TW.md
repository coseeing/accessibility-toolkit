# HID 104 鍵擴充設計

## 摘要

本設計把目前只有部分 `usage page` `0x07` 覆蓋的 HID-first 鍵盤模型，擴充到完整 ANSI 104-key，再加上 ISO 額外鍵 `NonUsBackslash`。目標是讓共通輸入模型對一般桌機鍵盤使用場景完整可用，同時保留目前 relay wire format，並維持 relay 邊界的清楚責任分工。

這是既有 HID-first 遷移的擴充，不是重新設計整體架構。HID 仍然是應用程式內部唯一的共通鍵盤表示法。平台 adapter 仍負責把原生事件正規化成 HID，而 `apps/nvda_remote` 仍是唯一會把 HID 轉回 legacy `vk_code/scan_code/extended/pressed` payload 的邊界。

## 目標

- 在共通 HID 模型中補齊完整 ANSI 104-key 覆蓋。
- 把 ISO 額外鍵加入共通 HID 模型與平台正規化層。
- 補齊 Windows 與 macOS 的平台映射。
- 補齊 ANSI 104-key 在 legacy relay adapter 的轉換能力。
- 保持目前 control mode 的安全規則：不支援 relay 的鍵要在本機被 suppress 並記 log，不可 pass through。

## 非目標

- 不在本輪加入 JIS 專用鍵。
- 不更動 relay wire format。
- 不加入 consumer/media keys 或其他 `0x07` 以外的 `usage page`。
- 不重新設計目前 adapter 分層，也不引入 code generation 來生成 mapping table。
- 不保證 ISO 額外鍵一定能在 legacy relay 中穩定轉送。

## 範圍

### 納入範圍

#### ANSI 104-Key 覆蓋

下列鍵組都必須在 HID 中有完整表示，且能被 Windows 與 macOS 平台 adapter 正規化：

- 字母：`A-Z`
- 數字：`0-9`
- 基本控制鍵：`Enter`、`Escape`、`Backspace`、`Tab`、`Space`、`CapsLock`
- 主鍵區標點：
  - `Minus`
  - `Equals`
  - `LeftBracket`
  - `RightBracket`
  - `Backslash`
  - `Semicolon`
  - `Quote`
  - `Grave`
  - `Comma`
  - `Period`
  - `Slash`
- 功能鍵：`F1-F12`
- 導航／編輯區：
  - `Insert`
  - `Delete`
  - `Home`
  - `End`
  - `PageUp`
  - `PageDown`
  - `Up`
  - `Down`
  - `Left`
  - `Right`
- 修飾鍵：
  - `LeftControl`
  - `RightControl`
  - `LeftShift`
  - `RightShift`
  - `LeftAlt`
  - `RightAlt`
  - `LeftMeta`
  - `RightMeta`
- Numpad：
  - `Keypad0-Keypad9`
  - `KeypadDecimal`
  - `KeypadDivide`
  - `KeypadMultiply`
  - `KeypadSubtract`
  - `KeypadAdd`
  - `KeypadEnter`
  - `KeypadEquals`

#### ISO 額外鍵

- `NonUsBackslash` 納入下列範圍：
  - HID 常數
  - Windows 正規化，前提是有穩定的 scan-code 映射
  - macOS 正規化，前提是有穩定的 virtual-key 映射
  - 本地應用程式行為

### 不納入範圍

- JIS 專用鍵
- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- application/menu key

這些鍵未來可以再處理，但本輪刻意排除，讓範圍維持在使用者要求的 104-key 配置加上 ISO 額外鍵。

## 架構

架構本身不變：

- `src/interop/key/*` 定義 HID 常數與共通 `KeyEvent`
- `src/adapters/windows/*` 把 Windows 事件正規化成 HID
- `src/adapters/macos/*` 把 macOS 事件正規化成 HID
- `src/application/*` 與 `src/apps/*` 只使用 HID
- `src/apps/nvda_remote/legacy_key_payload.py` 仍是唯一的 HID -> legacy relay 轉換層

這次是既有查表與測試的受控擴充，不改變分層與資料流。

## 設計決策

### 1. 繼續以 HID 作為唯一共通輸入模型

不引入新的平行模型。擴充後的鍵集合仍直接加到既有 HID-first 表示法中：

```python
@dataclass(frozen=True, slots=True)
class KeyEvent:
    usage_page: int
    usage: int
    pressed: bool
```

這延續先前 HID 遷移的架構決策，避免把 Windows 專屬語意重新帶回核心層。

### 2. 依鍵盤區域整理 HID 常數

目前的 `hid.py` 不應該只是一路往下塞常數，而是要依區塊分組，保持平面、清楚、可維護：

- 英數區
- 主鍵區標點
- 功能鍵
- 導航／編輯鍵
- 修飾鍵
- numpad
- ISO 額外鍵

這只是可讀性與維護性的整理，不應引入新的抽象層。

### 3. 明確區分主鍵區與 Numpad

擴充後的映射必須保留這些看起來相似、但 HID 上不同的鍵：

- 主鍵區 `Enter` vs `KeypadEnter`
- 主鍵區數字 vs `Keypad0-Keypad9`
- 主鍵區 `Minus` vs `KeypadSubtract`
- 主鍵區 `Equals` vs `KeypadEquals`
- 主鍵區 `Period` vs `KeypadDecimal`
- 主鍵區 `Slash` vs `KeypadDivide`

這個區分是 correctness 的必要條件，也是這次要把 HID 擴充補完整的重要原因。

### 4. ANSI 104-Key 必須可經由 Relay 相容層轉送

所有列在範圍內的 ANSI 104-key，都必須被 legacy relay adapter 支援：

- HID -> `vk_code`
- HID -> `scan_code`
- HID -> `extended`

即使 relay protocol 本身不變，這件事也必須成立。

### 5. ISO 額外鍵可以只保證本地 HID

`NonUsBackslash` 應加入共通 HID 模型與平台 adapter。但若無法為 legacy relay 找到可靠映射，則不要求一定能被轉送。

如果 relay 邊界仍不支援該鍵：

- adapter 應丟出 `ValueError`
- forwarding logic 應記 log 並在 control mode 下 suppress
- 測試必須明確驗證這個行為

這樣可以讓邊界責任清楚，不去發明不穩定的相容行為。

## 檔案層級變更

### `src/interop/key/hid.py`

補上缺少的 HID 常數：

- 剩餘主鍵區標點
- 導航／編輯鍵
- `CapsLock`
- numpad 鍵
- `NonUsBackslash`

這個檔案仍維持為單一、聚焦的常數定義模組。

### `src/adapters/windows/hid_map.py`

擴充 scan-code 映射，涵蓋：

- 剩餘標點鍵
- 導航／編輯鍵
- `CapsLock`
- numpad 鍵
- 若 Windows scan-code 行為穩定，則加入 ISO 額外鍵

Windows 映射仍應優先依賴：

- `scanCode`
- `extended`

只有在確實需要處理歧義時，才輔助參考 `vkCode`。

### `src/adapters/macos/hid_map.py`

擴充 macOS virtual-key 映射，涵蓋：

- 剩餘標點鍵
- 導航／編輯鍵
- `CapsLock`
- numpad 鍵
- 若 key-code 行為穩定，則加入 ISO 額外鍵

和先前 HID 遷移一樣，這層仍維持純查表轉換。

### `src/apps/nvda_remote/legacy_key_payload.py`

擴充 legacy adapter，讓 ANSI 104-key 覆蓋完整：

- 標點鍵
- 導航／編輯鍵
- 若沿用既有 protocol 語意可接受，則納入 `CapsLock`
- numpad 鍵

`NonUsBackslash` 只有在映射可靠時才加入；否則應明確維持 unsupported，而不是猜值。

### `src/apps/nvda_remote/use_cases/input_forwarding.py`

不需要新增新的行為模型。維持目前契約：

- 可支援的 HID 鍵 -> relay payload -> 本機 suppress
- control mode 下不支援 relay 的 HID 鍵 -> log + 本機 suppress

這比先前的 pass-through bug 安全，這輪應維持不變。

## 資料流

### 本地輸入

1. 平台 adapter 截取原生鍵盤事件。
2. 平台 adapter 映射成 HID `KeyEvent`。
3. 共通 application/app 邏輯只消費 HID。
4. `key_echo` 與本地 mode 邏輯繼續直接使用 HID usage。

### 遠端轉送

1. `nvda_remote` 收到 HID `KeyEvent`。
2. 若事件屬於 ANSI 104-key 且 relay 相容，則交由 `legacy_key_payload.py` 轉換。
3. 若事件是 ISO 額外鍵且沒有穩定 relay 映射，則拒絕轉換。
4. control mode 下，forwarding logic 對 unsupported relay 鍵記 log 並 suppress。

## 測試策略

### 單元測試：HID 常數

為新增的 HID 常數加入直接測試：

- 標點鍵 usage
- numpad usage
- `NonUsBackslash`

### 單元測試：Windows 映射

加入以下映射測試：

- `Semicolon`
- `Quote`
- `Comma`
- `Period`
- `Slash`
- `LeftBracket`
- `RightBracket`
- `Backslash`
- `Grave`
- numpad 數字
- numpad 運算鍵
- `KeypadEnter`
- 若有實作，則加入 ISO 額外鍵

### 單元測試：macOS 映射

加入對應的 macOS 測試：

- 主鍵區標點
- numpad 數字
- numpad 運算鍵
- `KeypadEnter`
- 若有實作，則加入 ISO 額外鍵

### 單元測試：Legacy Relay Adapter

加入以下 relay payload 轉換測試：

- 標點鍵
- 導航／編輯鍵
- numpad 鍵
- 與 relay 相容性有關的 meta / modifier 鍵

若 `NonUsBackslash` 維持 unsupported：

- 加一個明確的 failing-conversion test
- 驗證 `ValueError`

### 單元測試：Forwarding 行為

確認 unsupported relay 鍵：

- 不會送 payload
- 不會漏回本機
- 會回傳 `SUPPRESS`

### 回歸預期

完成後應達成：

- 主鍵區標點在本地 HID use case 與 relay forwarding 中都可運作
- numpad 鍵與主鍵區同形鍵保持區分
- ISO 額外鍵在 HID 中可用，即使 relay conversion 仍不支援也沒關係

## 風險

### 映射歧義

最大的 correctness 風險來自：

- 主鍵區與 numpad 鍵混淆
- ANSI `Backslash` 與 ISO 額外鍵混淆
- Windows 中依賴 `extended` 區分的鍵

這些都必須靠明確測試覆蓋，不可依賴推論。

### Legacy Relay 限制

即使 HID 模型擴充完整，relay 仍依賴舊的 Windows-style payload。這對 ANSI 104-key 是可接受的，但 ISO 支援必須明確保持條件式。

### 表格成長

mapping 檔會明顯變大。這輪的對策應該是清楚分組與聚焦測試，而不是再引入新的抽象層。

## 建議做法

建議採用「查表擴充」的實作方式：

- 保持目前架構不變
- 依鍵盤區域整理常數與 mapping
- 完整補齊 ANSI 104-key relay 相容性
- ISO 額外鍵先補本地 HID，relay 僅在映射穩定時才加入

這是在不把工作擴大成另一場重構的前提下，最小但正確、也最符合使用者需求的擴充方式。
