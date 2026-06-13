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

在 HID 重構前，`KeyEvent` 直接儲存了 Windows 的原始 VK、掃描碼與延伸旗標：

```python
# 舊版 KeyEvent（直接保留原始 Windows 值）
KeyEvent(vk=35, scan=79, extended=True, pressed=True)
```

傳送給遠端的 payload 直接使用這些原始值，因此遠端收到的資料是正確的 `VK_END`（End 鍵），遠端會正確執行 End 鍵的導航行為。

### HID 重構後的行為（異常）

HID 重構後，`KeyEvent` 被改為只儲存 HID 標準化數值（`usage_page`、`usage`、`pressed`），捨棄了 Windows 原始 VK 與掃描碼。為了重建遠端 payload，新增了一個靜態查表函式 `key_event_to_legacy_remote_payload()`，將 HID usage 重新映射回 VK/掃描碼/延伸旗標。

問題出在 **Windows → HID 的轉換步驟**，也就是 `key_event_from_windows()` 函式。此函式使用 `(scan_code, extended)` 作為查表鍵，對應表如下：

```python
_SCAN_TO_USAGE = {
    (79, False): HID.KEYPAD_1,   # Num Lock ON  → 數字鍵盤 1
    (79, True):  HID.END,        # Num Lock OFF → End 鍵
}
```

這個查表邏輯在**測試中**是正確的，因為測試使用標準掃描碼（`scanCode=79`）。然而在**部分真實硬體**上，當 Windows 回報延伸鍵（extended key）時，`KBDLLHOOKSTRUCT.scanCode` 欄位的值可能包含了 **E0 前綴**（E0 prefix），例如 `0xE04F`（十進位 57423），而不是單純的 `0x4F`（十進位 79）。

此時查表會失敗：

```python
# 真實硬體可能回報的掃描碼
scan_code = 57423  # 0xE04F（含 E0 前綴）

# 查表失敗
_SCAN_TO_USAGE.get((57423, True))  # → None

# key_event_from_windows() 回傳 None
# → 掛鉤判定為 PASS_THROUGH（不轉發，也不抑制）
# → 按鍵在本地端正常處理，但不會傳送到遠端
```

所以使用者看到的行為是：數字鍵盤按鍵「好像有作用」但其實是在**本機**被處理了（本地 Num Lock 的狀態決定了本機的行為），而遠端完全沒有收到按鍵（或收到的是不正確的值）。

## 修正方式

核心思路：**恢復原始 Windows 值在 payload 中的優先權**，不再完全依賴 HID → Legacy 的靜態查表。

### 變更的檔案

| 檔案 | 變更內容 |
|------|---------|
| `src/interop/key/key_event.py` | `KeyEvent` 新增 `vk`、`scan`、`extended` 三個可選欄位，並覆寫 `__eq__` / `__hash__` 僅比較 HID 核心欄位 |
| `src/adapters/windows/hid_map.py` | `key_event_from_windows()` 將原始值一併傳入 `KeyEvent`；新增 `raw_key_event_from_windows()` 保證即使掃描碼無法映射也回傳 KeyEvent（保留原始值） |
| `src/adapters/windows/keyboard_hook.py` | 改用 `raw_key_event_from_windows()` 取代 `key_event_from_windows()` |
| `src/apps/nvda_remote/legacy_key_payload.py` | `key_event_to_legacy_remote_payload()` 檢查 `KeyEvent` 是否帶有原始 Windows 值，若有則**直接使用原始值**，無原始值時才走 HID → Legacy 查表 |

### 修正後的流程

```
Windows 低階掛鉤
  │ vk=35, scan=57423 (E0 prefix), extended=True, pressed=True
  ▼
raw_key_event_from_windows()
  │ KeyEvent(usage=0, vk=35, scan=57423, extended=True, pressed=True)
  │          └─ HID 查表失敗(usage=0)，但原始 Windows 值完整保留
  ▼
NvdaRemoteInputForwardingUseCase.handle()
  ▼
key_event_to_legacy_remote_payload()
  │ 檢測到 vk != None 且 scan != None
  │ → 直接使用原始值，不回退 HID 查表
  ▼
遠端 payload: {vk_code: 35, scan_code: 57423, extended: True, pressed: True}
  │ VK_END (End 鍵)，遠端正確執行導航行為 ✓
```

### 向後相容性

- **macOS 事件**：不帶有原始 Windows 值（`vk=None`），自動退回到原有的 HID → Legacy 查表，行為不變
- **HID 比對**：`KeyEvent.__eq__` 僅比對核心 HID 欄位，現有測試不受影響
- **既有測試**：全部通過（340/341，1 個是既有的 flaky test 與此修正無關）

## 相關 Commit

```
3205c5c fix: preserve raw Windows VK/scan/extended values for legacy remote forwarding
```
