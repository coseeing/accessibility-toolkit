# Numpad Num Lock 傳送異常問題分析與修正

## 問題現象

在 nvda_remote 控制模式（按 F11 進入）下，本機已開啟 Num Lock 時，數字鍵盤按鍵可正確傳送到遠端並輸入數字。但當**本機關閉 Num Lock** 時，數字鍵盤按鍵仍會在遠端輸入數字，而不是執行導航功能（如 End、Home、方向鍵等）。也就是說，數字鍵盤按鍵的行為無法反映 Num Lock 的開關狀態。

## 根本原因

### 問題發生的資料流

當使用者在控制模式下按下數字鍵盤 1（Num Lock 關閉），Windows 低階鍵盤掛鉤（Low-Level Keyboard Hook）會收到以下原始資料：

```
vkCode  = 35   (VK_END，代表 End 鍵)
scanCode = 79  (數字鍵盤 1 的硬體掃描碼)
flags   = 0x01 (LLKHF_EXTENDED，延伸鍵旗標)
```

### HID 重構前的行為（正常）

在 HID 重構前，Windows 的原始 VK（虛擬鍵碼）直接被用於建構遠端 payload，因此遠端收到的 `vk_code=35` 即 `VK_END`（End 鍵），遠端會正確執行導航行為。

### HID 重構後的行為（異常）

HID 重構後，鍵盤事件統一轉換為 HID usage（平台中立格式），再透過靜態查表函式 `key_event_to_legacy_remote_payload()` 將 HID usage 映射回 Windows VK/掃描碼/延伸旗標。

問題出在 **Windows → HID 的轉換步驟**，即 `key_event_from_windows()` 函式。此函式使用 `(scan_code, extended)` 作為查表鍵：

```python
_SCAN_TO_USAGE = {
    (79, False): HID.KEYPAD_1,   # Num Lock ON  → 數字鍵盤 1
    (79, True):  HID.END,        # Num Lock OFF → End 鍵
}
```

這個查表邏輯在**測試中**正確，因為測試使用標準掃描碼（79）。但在**部分真實硬體**上，`KBDLLHOOKSTRUCT.scanCode` 欄位可能包含 **E0 前綴**（例如 `0xE04F` = 57423），而非單純的 `0x4F`（79）。

此時查表失敗，`key_event_from_windows()` 回傳 `None`：

```python
scan_code = 57423  # 0xE04F（含 E0 前綴）

_SCAN_TO_USAGE.get((57423, True))  # → None，查不到

# key_event_from_windows() 回傳 None
# → 掛鉤判定為 PASS_THROUGH（不轉發，也不抑制）
# → 按鍵在本地端正常處理，但不會傳送到遠端
```

## 修正方式

核心思路：**將原始 Windows 值（vk/scan/extended）保留在 KeyEvent 的可選欄位上**，`key_event_to_legacy_remote_payload()` 偵測到這些值時，直接使用原始值建構遠端 payload，不經過 HID → Legacy 靜態查表。

### 變更的檔案

| 檔案 | 變更內容 |
|------|---------|
| `src/interop/key/key_event.py` | `KeyEvent` 新增 `vk`（`int | None`）、`scan`（`int | None`）、`extended`（`bool`）三個可選欄位，預設值為 `None`。覆寫 `__eq__` / `__hash__` 僅比較 HID 核心欄位（`usage_page`、`usage`、`pressed`） |
| `src/adapters/windows/hid_map.py` | `key_event_from_windows()` 將原始值一併傳入 `KeyEvent`；新增 `raw_key_event_from_windows()` 保證即使掃描碼無法映射 HID usage，也回傳 KeyEvent（usage=0），且保留原始值 |
| `src/adapters/windows/keyboard_hook.py` | 改用 `raw_key_event_from_windows()` 取代 `key_event_from_windows()` |
| `src/apps/nvda_remote/legacy_key_payload.py` | `key_event_to_legacy_remote_payload()` 檢查 `event.vk` 與 `event.scan` 是否都不為 `None`，若是則直接使用原始值；否則走原有的 HID → Legacy 查表（macOS 等平台） |

### 修正後的流程

```
Windows 低階掛鉤
  │ vk=35, scan=任意值（可能含 E0 前綴或不認識）, extended=True, pressed=True
  ▼
raw_key_event_from_windows()
  │ HID 查表可能失敗（usage=0），但原始 Windows 值完整保留
  │ KeyEvent(usage=0, vk=35, scan=..., extended=True, pressed=True)
  ▼
NvdaRemoteInputForwardingUseCase.handle()
  ▼
key_event_to_legacy_remote_payload()
  │ 檢測到 vk != None 且 scan != None
  │ → 直接使用原始值
  ▼
遠端 payload: {vk_code: 35, scan_code: ..., extended: True, pressed: True}
  │ 無論 scan_code 為何，vk_code=35 (VK_END) 保證遠端正確行為 ✓
```

### 平台中立性說明

`vk` / `scan` / `extended` 為**可選欄位**，預設值為 `None`：

- **Windows**：`raw_key_event_from_windows()` 會填入這些值
- **macOS** 及其他平台：不填入（維持 `None`），`key_event_to_legacy_remote_payload()` 自動退回到 HID → Legacy 查表
- **KeyEvent 比對**：`__eq__` / `__hash__` 僅比較 HID 核心欄位，不影響跨平台的事件比對

### 嘗試過但無效的方案

曾嘗試在 `key_event_from_windows()` 中將掃描碼遮罩到低位元組（`scan_code & 0xFF`）來處理 E0 前綴，但在真實硬體上測試無效。推測硬體回報的掃描碼格式變化不僅限於 E0 前綴，因此保留原始值是唯一可靠的方案。

## 相關 Commit

```
3d3f496 fix: restore raw Windows VK/scan/extended values on KeyEvent
         for reliable legacy forwarding
```
