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

核心思路：**在 `key_event_from_windows()` 中增加 VK → HID 備援查表**。當掃描碼無法匹配時，使用 Windows 已正規化的 VK 碼來決定 HID usage。

### 變更內容

只修改 `src/adapters/windows/hid_map.py`：

```python
# 新增 VK → HID 備援對照表（僅涵蓋數字鍵盤與導航鍵）
_VK_TO_USAGE: dict[int, int] = {
    0x23: HID.END,        # VK_END
    0x24: HID.HOME,       # VK_HOME
    0x25: HID.LEFT,       # VK_LEFT
    0x26: HID.UP,         # VK_UP
    0x27: HID.RIGHT,      # VK_RIGHT
    0x28: HID.DOWN,       # VK_DOWN
    0x21: HID.PAGE_UP,    # VK_PRIOR
    0x22: HID.PAGE_DOWN,  # VK_NEXT
    0x2D: HID.INSERT,     # VK_INSERT
    0x2E: HID.DELETE,     # VK_DELETE
    0x60-0x69: HID.KEYPAD_0-9,  # VK_NUMPAD0-9
    0x6A-0x6F: HID.KEYPAD_*,    # VK_MULTIPLY, ADD, SUBTRACT, DECIMAL, DIVIDE
    0x90: HID.NUM_LOCK,   # VK_NUMLOCK
    0xF2: HID.INTERNATIONAL3,
}

def key_event_from_windows(*, vk_code, scan_code, extended, pressed):
    usage = _SCAN_TO_USAGE.get((scan_code, extended))
    if usage is None and extended and scan_code > 0xFF:
        # 硬體可能將 E0 前綴內嵌在掃描碼中 → 遮罩低位元組重試
        usage = _SCAN_TO_USAGE.get((scan_code & 0xFF, extended))
    if usage is None:
        # scan code 無法匹配 → 用 VK 查表備援
        usage = _VK_TO_USAGE.get(vk_code)
    if usage is None:
        return None
    return KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=pressed)
```

### 為何這樣就夠了

- VK 碼是 Windows 已經正規化過的結果，**不受硬體掃描碼格式影響**
- 查表順序：scan code → E0 遮罩 → VK 備援，三層遞補
- `KeyEvent` 保持純 HID 格式，無任何 Windows 特定欄位，平台中立性完整保留
- 不需要改 keyboard_hook、legacy_key_payload 等任何其他模組

### 修正後的流程

```
Windows 低階掛鉤
  │ vk=35 (VK_END), scan=硬體特定值, extended=True, pressed=True
  ▼
key_event_from_windows()
  │ 1. (scan, extended) 查表 → 失敗（硬體回報非標準 scan code）
  │ 2. scan & 0xFF 遮罩查表 → 失敗
  │ 3. _VK_TO_USAGE.get(0x23) → HID.END ✓
  │ KeyEvent(usage_page=7, usage=0x4D, pressed=True)
  ▼
key_event_to_legacy_remote_payload()
  │ HID.END → (35, 79, True)
  ▼
遠端 payload: {vk_code: 35, scan_code: 79, extended: True, pressed: True}
  │ VK_END (End 鍵) ✓
```

## 相關 Commit

```
53a6f22 fix: use VK code as HID fallback when scan code lookup fails
```
