# HID-First Keyboard Input Design

## Overview

本設計將 `nvda-remote-client` 的共通底層鍵盤輸入模型全面改為 USB HID-first。平台層負責把各自截到的原生鍵盤事件正規化為中立的 HID 鍵盤事件；應用層與各 app 的邏輯只依賴 HID，不再直接依賴 Windows `vk`、`scan`、`extended` 或 macOS `key_code`。

第一階段僅支援標準鍵盤 usage page `0x07`，目標是先跑通穩定的跨平台實體鍵事件模型，並維持現有 NVDA Remote relay protocol 相容性。

## Goals

- 將專案核心鍵盤事件模型改為 HID-first。
- 讓 Windows 與 macOS 的鍵盤 capture 都輸出相同的中立事件格式。
- 讓 `application`、`key_echo`、hotkey/mode 管理與本地控制邏輯全面改用 HID 判斷。
- 維持現有 NVDA Remote wire protocol 相容性，不修改 relay 上的 `key` 訊息格式。
- 將舊有 Windows-style `vk/scan/extended` 語意限制在 protocol 邊界 adapter。

## Non-Goals

- 不在本輪支援 consumer/media keys，例如 usage page `0x0C`。
- 不在本輪處理 IME、文字輸入、字元輸出或鍵盤配置推導。
- 不在本輪重新設計 relay server 或更改網路協定格式。
- 不保證一次覆蓋所有區域鍵盤配置與所有特殊鍵。
- 不把 HID 事件直接暴露為新的對外網路協定。

## Problem Statement

目前專案內部共通模型為 Windows-style `KeyEvent(vk, scan, extended, pressed)`。Windows 平台直接產生這種事件，macOS 平台則透過查表把 `key_code` 轉成 Windows `vk/scan` 再送入上層。這造成：

- 核心層被 Windows 語意主導。
- 跨平台邏輯實際上依賴 Windows 表示法，而不是中立的實體鍵模型。
- `key_echo` 與 mode/hotkey 邏輯無法自然共用真正的平台中立判斷。
- 未來若要擴充更多平台或更多輸入來源，會持續把平台碼滲入核心。

需要將平台正規化目標從「轉成 Windows」改為「轉成 HID」。

## HID Model

### Definitions

- `usage_page`: HID 使用頁。第一階段固定使用 `0x07`，代表 Keyboard/Keypad。
- `usage`: 該使用頁中的具體鍵值，例如 `A=0x04`、`Enter=0x28`、`Escape=0x29`、`F11=0x44`。
- `pressed`: `True` 表示 key down，`False` 表示 key up。

### Core Event Shape

新的共通鍵盤事件定義如下：

```python
@dataclass(frozen=True, slots=True)
class KeyEvent:
    usage_page: int
    usage: int
    pressed: bool
```

此模型只表達實體鍵事件，不承擔字元、layout、修飾後文字或平台碼等高階語意。

## Architecture

### Layer Responsibilities

#### `adapters/*`

平台專屬輸入擷取與映射層。

- Windows: 原生事件 -> HID `KeyEvent`
- macOS: 原生事件 -> HID `KeyEvent`
- 不得向上暴露 `vk`、`scan`、`extended` 或 `key_code` 作為共通模型

#### `application/*`

只處理 HID `KeyEvent`。

- hotkey policy
- mode manager
- activation
- key echo
- app facade 對鍵盤事件的應用邏輯

#### `apps/nvda_remote/*`

依賴 HID `KeyEvent` 作為 app 內部事件模型，但在送出現有 relay protocol 前，透過單一 adapter 轉成舊的 `vk_code/scan_code/extended/pressed` payload。

#### `interop/protocol/*`

第一階段保持現有 wire format，不內建 HID network message。

## Platform Mapping Strategy

### Windows

Windows low-level keyboard hook 仍負責截取原始事件，但正規化目標改為 HID。

映射原則：

- 以 `scanCode + extended flag` 為主要依據。
- 只有在必要時才輔助參考 `vkCode`。
- 對左右修飾鍵、方向鍵、功能鍵與 keypad 相關鍵保持明確區分。

原因：

- `vkCode` 偏向 Windows 邏輯鍵語意，不足以穩定表示實體鍵位置。
- 實體鍵正規化更應依賴 scan code 與 extended flag。

Windows mapping 應集中在單一模組，例如 `adapters/windows/hid_map.py`，由 hook adapter 呼叫。

### macOS

macOS event tap 仍負責截取 `key_code` 與按下/放開事件，但不再轉成 Windows `vk/scan`，而是直接查表轉成 HID usage。

映射原則：

- 以 macOS virtual key code 對應 HID usage。
- 維持現有對一般鍵、功能鍵、方向鍵、左右修飾鍵的可識別性。
- 查表集中在單一模組，例如 `adapters/macos/hid_map.py`。

現有 `adapters/macos/keymap.py` 的角色將從「macOS -> Windows-style」改為「macOS -> HID」。

## Application Model Changes

所有上層鍵盤邏輯都改成 HID-first：

- `ModeManager`
- `InputActivationUseCase`
- `active_key_policy`
- `state_transition_hotkeys`
- `key_echo`
- `nvda_remote` 本地 start/stop control 熱鍵判斷

原本以 `event.vk == 0x7A`、`event.vk == 0x1B` 等方式判斷的地方，改為比對固定的 HID usage 常數。

建議建立共通 HID constants 或 enum，至少先覆蓋：

- 字母 A-Z
- 數字 0-9
- `Enter`
- `Escape`
- `Tab`
- `Space`
- `Backspace`
- 方向鍵
- `F1-F12`
- 左右 `Shift`
- 左右 `Control`
- 左右 `Alt/Option`
- 左右 `Meta/Command`

## Legacy Relay Protocol Compatibility

現有 NVDA Remote wire protocol 保持不變，`type="key"` payload 仍為：

```json
{
  "type": "key",
  "vk_code": 65,
  "scan_code": 30,
  "extended": false,
  "pressed": true
}
```

### Boundary Adapter

新增單一 protocol adapter，負責：

- HID `KeyEvent` -> legacy remote payload

此 adapter 是專案中唯一允許處理 `vk_code/scan_code/extended` 的位置。核心層與 app 邏輯不得直接依賴這些欄位。

### Adapter Behavior

- 僅保證第一階段支援的 `usage_page=0x07` 標準鍵盤鍵。
- 若某個 HID usage 無法可靠映射到舊 payload，應拒絕送出並產生明確的狀態通知或記錄，而不是猜測映射值。
- protocol adapter 不反向主導核心模型；它只是相容層。

## Data Flow

### Local Input Flow

1. 平台 adapter 截取原生鍵盤事件。
2. 平台 adapter 將原生事件轉成 HID `KeyEvent`。
3. `application`/app use cases 只接收 HID `KeyEvent`。
4. 若目前 app 是 `key_echo`，直接使用 HID 做本地輸出或控制判斷。
5. 若目前 app 是 `nvda_remote` 且需要轉送，則在送網路前由 legacy protocol adapter 轉成舊 payload。

### Remote Forwarding Flow

1. `nvda_remote` 收到本地 HID `KeyEvent`。
2. app 邏輯以 HID 判斷 mode/hotkey。
3. 若事件需要送往 relay，呼叫 legacy protocol adapter。
4. adapter 產生現有 `key` 訊息 payload。
5. transport/serializer 以既有流程送出。

## Migration Plan

### Step 1: Introduce HID Core Model

- 重新定義共通 `interop.key.KeyEvent`
- 建立 HID constants/enums
- 刪除或淘汰核心層對 `vk/scan/extended` 的依賴

### Step 2: Convert Platform Capture Output

- Windows hook 輸出 HID `KeyEvent`
- macOS event tap 輸出 HID `KeyEvent`
- 單元測試改驗證 HID 映射

### Step 3: Convert Application and App Logic

- 將所有 hotkey/mode/use case 判斷改成 HID usage
- 更新 `key_echo` 相關行為與測試
- 更新 `nvda_remote` 本地控制流程與測試

### Step 4: Add Legacy Protocol Adapter

- 在 `apps/nvda_remote` 或 `interop/protocol` 合適邊界新增 HID -> legacy payload 轉換器
- 更新 protocol 與 app service 測試
- 驗證與既有 relay protocol 的互通

## Testing Strategy

### Unit Tests

- Windows 原生事件到 HID usage 的映射測試
- macOS `key_code` 到 HID usage 的映射測試
- HID hotkey 判斷測試
- HID -> legacy remote payload 轉換測試

### Integration Tests

- 保持現有 relay session 測試，確認 wire format 不變
- 補一條從 HID `KeyEvent` 到傳輸 payload 的整體路徑測試

### Regression Coverage

至少覆蓋：

- `F11` 進入/退出控制
- `Escape` 與既有本地控制相關邏輯
- 一般字母鍵 press/release
- 左右修飾鍵
- 方向鍵
- keypad 與非 keypad 的差異鍵

## Risks

### Mapping Accuracy

Windows 的 HID 正規化若錯用 `vkCode` 當主要依據，容易在左右修飾鍵、方向鍵與 keypad 上失真。必須以 `scanCode + extended` 為主要映射基礎。

### Legacy Compatibility Gaps

維持舊 relay protocol 時，某些 HID 鍵可能無法 1:1 回投為 legacy `vk/scan/extended`。第一階段需要明確限制支援範圍，只保證標準 `0x07` 鍵盤鍵跑通。

### Transition Scope

全面替換會觸及：

- adapters
- application
- shared mode logic
- key echo
- nvda remote forwarding
- 測試基礎假設

因此實作需按步驟切分，避免在同一提交中同時混合模型改造與無關重構。

## Open Decisions Resolved by This Design

- 核心模型使用 HID-first，而非保留 Windows-style model。
- 第一階段只支援 usage page `0x07`。
- `KeyEvent` 保留完整 `usage_page + usage + pressed` 形狀。
- hotkey 與 mode 判斷全面改用 HID。
- relay wire protocol 維持相容，由單一 boundary adapter 做 HID -> legacy 轉換。
