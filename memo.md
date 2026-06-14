# Num Lock 數字鍵盤傳送異常 — 除錯與修正歷程

## 問題

在 nvda_remote 控制模式（F11）下，本機 Num Lock 關閉時，按下數字鍵盤按鍵（如數字鍵盤 1），遠端仍收到數字 1，而非 End 鍵。也就是說數字鍵盤的行為無法反映 Num Lock 狀態。此問題在 HID 重構後才出現。

## 調查過程

### 1. 資料流追蹤

Windows 低階鍵盤掛鉤收到按鍵事件的原始資料：

```
Num Lock ON,  數字鍵盤 1: vk=97 (VK_NUMPAD1), scan=79, extended=False
Num Lock OFF, 數字鍵盤 1: vk=35 (VK_END),     scan=79, extended=True
```

HID 重構後的處理流程：

```
Windows hook → key_event_from_windows(scan, extended) → HID usage
                                                            │
                                     key_event_to_legacy_remote_payload()
                                                            │
                                         遠端 payload {vk_code, scan_code, extended}
```

### 2. 靜態查表驗證

`key_event_from_windows()` 使用 `(scan_code, extended)` 查表：

```python
(79, False): HID.KEYPAD_1    # Num Lock ON
(79, True):  HID.END         # Num Lock OFF
```

`key_event_to_legacy_remote_payload()` 將 HID 轉回 legacy 格式：

```python
HID.KEYPAD_1 → (97, 79, False)   # VK_NUMPAD1
HID.END      → (35, 79, True)    # VK_END
```

**測試中**這段雙向轉換完全正確，Num Lock 資訊沒有流失。

### 3. 根因定位

問題在於**部分鍵盤硬體**回報的 `KBDLLHOOKSTRUCT.scanCode` 格式與測試中使用的標準值不同。硬體可能將 E0 前綴或其他旗標內嵌在 scan code 欄位中（例如 `0xE04F` = 57423，而非 `0x4F` = 79），導致 `(57423, True)` 無法匹配查表中的 `(79, True)`。

`key_event_from_windows()` 回傳 `None` → 掛鉤判定為 `PASS_THROUGH` → 按鍵在本地端放行，**不轉發到遠端**。

## 嘗試過的方案

### 方案 A：在 KeyEvent 保留原始 Windows 值（commit `3d3f496`）

在 `KeyEvent` 上新增 `vk`、`scan`、`extended` 可選欄位，`key_event_to_legacy_remote_payload()` 偵測到這些值時直接使用，不經過 HID 查表。

- **優點**：原始 Windows 值完全保留，不受任何查表失敗影響
- **缺點**：`KeyEvent` 滲入了 Windows 特有形欄位，破壞 HID 平台中立性

### 方案 B：掃描碼遮罩（commit `5fc58c1`）

在 `key_event_from_windows()` 中將 scan code 遮罩到低位元組（`scan_code & 0xFF`）後重試查表。

- **優點**：只改一行，完全不影響 `KeyEvent` 或其他模組
- **缺點**：在真實硬體上測試**無效**，推測硬體回報的異常格式不僅限於 E0 前綴

### 方案 C：VK → HID 備援查表（commit `53a6f22`）← 最終採用

在 `key_event_from_windows()` 中增加第三層備援：當 scan code 查表失敗時，使用 Windows 已正規化的 VK 碼來查表取得 HID usage。

```python
def key_event_from_windows(*, vk_code, scan_code, extended, pressed):
    usage = _SCAN_TO_USAGE.get((scan_code, extended))       # 第一層
    if usage is None and extended and scan_code > 0xFF:
        usage = _SCAN_TO_USAGE.get((scan_code & 0xFF, extended))  # 第二層
    if usage is None:
        usage = _VK_TO_USAGE.get(vk_code)                   # 第三層（備援）
    if usage is None:
        return None
    return KeyEvent(...)
```

`_VK_TO_USAGE` 涵蓋數字鍵盤及導航鍵的 VK → HID 對應。

- **優點**：修正在 `hid_map.py` 一個檔案內完成；`KeyEvent` 保持純 HID 格式；不影響 keyboard_hook、legacy_key_payload 等任何其他模組
- **缺點**：無

## 設計討論

### Scan Code vs VK Code 本質

| | Scan Code（掃描碼） | VK Code（虛擬鍵碼） |
|---|---|---|
| **代表意義** | 按鍵的實體位置 | 按鍵的功能意義 |
| **Num Lock 影響** | 不受影響，數字鍵盤 1 永遠是 scan=79 | 受影響，Num Lock ON 時為 `VK_NUMPAD1`，OFF 時為 `VK_END` |
| **來源** | 鍵盤硬體直接回報，格式可能因硬體而異 | Windows 根據鍵盤狀態正規化後的結果，跨硬體一致 |

### HID 是否能表達所有 Windows 按鍵

可以。HID Keyboard usage page（0x07）涵蓋所有標準鍵盤按鍵，包括數字鍵盤（`KEYPAD_*`）與導航鍵（`END`、`HOME` 等）。問題不在 HID 的涵蓋範圍，而在 **Windows → HID 轉換步驟**：`key_event_from_windows()` 依賴 scan code 查表，而 scan code 在不同硬體上格式不一致。

### 為何不用 VK 當主路徑

因為 HID 標準本身就是以實體按鍵位置（類似 scan code）為基礎的模型。現有 scan code 查表在絕大多數情況下是正確的，VK 只作為備援處理硬體異常情況。如果 VK 當主路徑，反而失去了 HID 模型的設計意圖。

### macOS 是否有類似問題

macOS 沒有 Num Lock 機制，也不會收到異常的 scan code 格式。`key_event_from_macos()` 使用 `key_code` 直接查表轉 HID，不涉及 scan code，因此不需要 VK 備援。

## 最終架構

```
Windows 低階掛鉤
  │ vk, scan（可能含硬體異常格式）, extended, pressed
  ▼
key_event_from_windows()
  ├─ 1. (scan, extended) 查表          ← 主路徑
  ├─ 2. (scan & 0xFF, extended) 查表   ← E0 前綴遮罩
  └─ 3. _VK_TO_USAGE[vk] 查表         ← VK 備援
  │
  ▼
KeyEvent(usage_page=7, usage=HID usage, pressed=True)  ← 純 HID，無平台欄位
  │
  ▼
key_event_to_legacy_remote_payload()
  │ HID usage → legacy (vk_code, scan_code, extended)
  ▼
遠端 payload
```

## 相關 Commit

| Commit | 說明 |
|--------|------|
| `53a6f22` | fix: use VK code as HID fallback when scan code lookup fails |
| `58156f0` | docs: update numlock.md with final VK fallback approach |
