# 特殊鍵與 JIS HID 擴充設計

## 摘要

本設計延續既有 HID-first 鍵盤模型，補上前一輪 `hid-104-key-expansion` 刻意排除的特殊鍵與 JIS 專用鍵處理。目標不是重新設計輸入架構，而是在不更動現有 relay wire format 的前提下，讓更多實體鍵能被 Windows 與 macOS 正規化為 HID，並在 legacy relay 相容層中採取「能穩定 relay 就 relay，否則明確 local-only」的策略。

本輪涵蓋兩類擴充：

- 特殊控制鍵：`PrintScreen`、`ScrollLock`、`Pause`、`NumLock`、application/menu key
- JIS 專用鍵：常見日文鍵盤專用鍵位，先完整納入 HID 與平台正規化，再依 relay 穩定性決定是否支援遠端轉送

整體分層維持不變。HID 仍然是 `src/` 內唯一的共通鍵盤表示法；`apps/nvda_remote/legacy_key_payload.py` 仍然是唯一可以處理 `vk_code/scan_code/extended` 的邊界 adapter。

## 背景

前一輪 `docs/superpowers/specs/2026-06-12-hid-104-key-expansion-design_zh-TW.md` 已把 HID-first 模型擴充到完整 ANSI 104-key 與 ISO 額外鍵 `NonUsBackslash`，並明確把下列鍵排除在範圍外：

- JIS 專用鍵
- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- application/menu key

目前程式碼也反映同樣邊界：

- `src/interop/key/hid.py` 尚未定義上述特殊鍵與 JIS 鍵
- Windows/macOS HID mapping 尚未補齊這些鍵
- `src/apps/nvda_remote/legacy_key_payload.py` 尚未處理這些鍵的 relay 相容轉換

因此這一輪的性質是既有 HID 擴充的 follow-up，而不是架構重做。

## 目標

- 在共通 HID 常數中補上特殊控制鍵與常見 JIS 專用鍵。
- 補齊 Windows 與 macOS 的 native event -> HID 正規化。
- 讓可穩定表示的特殊鍵支援 legacy relay payload 轉換。
- 讓 JIS 鍵完整可用於本地 HID-first 邏輯，即使其中一部分無法 relay。
- 維持 control mode 的安全規則：unsupported relay key 一律記 log 並本機 suppress，不可 pass-through。

## 非目標

- 不更動現有 NVDA Remote `type="key"` wire format。
- 不新增 consumer/media keys 或其他 `usage page` `0x07` 以外的鍵類。
- 不把 relay 相容性邏輯散落到 Windows/macOS adapter。
- 不為無法辯護的特殊鍵或 JIS 鍵發明近似 legacy 映射。
- 不保證所有 JIS 鍵都能 end-to-end relay。

## 範圍

### 納入範圍

#### 特殊控制鍵

下列鍵納入共通 HID 模型，並優先嘗試做到 end-to-end relay：

- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- application/menu key

#### JIS 專用鍵

本輪將常見 JIS 專用鍵完整納入 HID 與平台正規化。至少包含：

- `NonUsHash`
- `International1`
- `International3`
- `International4`
- `International5`

若平台事件模型可穩定辨識更多日文鍵盤專用 usage，可同樣納入；但本設計不要求超出「常見 JIS 專用鍵」的完整地區鍵盤研究。

### 可能 local-only 的鍵

下列類型即使納入 HID，也可能因 legacy payload 無法穩定表達而維持 local-only：

- 部分 JIS 專用鍵
- `Pause`，若平台或 legacy 對應出現不可穩定重建的情況
- 任何需要猜測 `scan_code`、複合事件或模糊 `extended` 語意的鍵

## 架構

本輪不更動分層：

- `src/interop/key/*`：定義 HID 常數與共通 `KeyEvent`
- `src/adapters/windows/*`：Windows 原生事件 -> HID
- `src/adapters/macos/*`：macOS 原生事件 -> HID
- `src/application/*` 與 `src/apps/*`：只消費 HID
- `src/apps/nvda_remote/legacy_key_payload.py`：HID -> legacy relay payload

設計原則仍是：

- 平台層只做 native -> HID 正規化
- 核心層與 app 層只依賴 HID
- relay 相容性只在單一邊界處理

## 設計決策

### 1. 採用 HID-first + relay-best-effort

本輪不會因為 relay 相容性有限，就延後把鍵納入 HID。所有目標鍵都應先進入共通 HID 模型與平台 adapter；relay 則採 best-effort：

- 可穩定表達成 `vk_code/scan_code/extended` 的鍵：支援 relay
- 無法穩定表達的鍵：明確 local-only

這讓核心模型保持完整，也避免舊 relay 邊界反向主導整個輸入系統的表達能力。

### 2. 不以「可抓到事件」等同於「可 relay」

某鍵能從 Windows hook 或 macOS event tap 捕獲，不代表它就應該直接納入 legacy relay adapter。relay 支援的判準必須更嚴格：

- 是否存在單一且可辯護的 `vk_code`
- 是否存在穩定的 `scan_code`
- `extended` 語意是否明確
- 是否不會把不同 HID usage 錯誤合併成相同 legacy 鍵

若答案是否定的，則該鍵應維持 local-only。

### 3. JIS 先完整進 HID，再逐一評估 relay

本輪不採「先挑少數 JIS 鍵試做」的策略，而是先把常見 JIS 專用鍵完整納入 HID 常數與平台 mapping。這樣可以：

- 讓 `key_echo`、本地控制與未來 app 邏輯能立即看見這些鍵
- 把「本地可辨識」與「可遠端 relay」的能力清楚分開
- 避免把 JIS 鍵永久卡在前置研究狀態

relay 層對 JIS 的策略是逐一審核，而不是一次全開。

### 4. 不做近似降級映射

若某 JIS 鍵沒有可靠 legacy 對應，不應把它降級映成某個看起來相近的 ANSI 鍵；若某特殊鍵的 `scan_code` / `extended` 表示含糊，也不應硬塞近似值。

禁止的行為包含：

- 把 JIS 專用鍵映成一般標點鍵
- 把 application/menu key 映成其他修飾鍵或字元鍵
- 用不穩定的複合 Windows 鍵序列假裝單一 legacy payload

這些做法都會破壞 HID distinction，並讓遠端行為不可預期。

### 5. Unsupported relay key 維持 suppress + log

本輪不新增新的 forwarding 狀態模型。若 `legacy_key_payload.py` 拒絕某 HID 鍵：

- `key_event_to_legacy_remote_payload()` 應丟出 `ValueError`
- `NvdaRemoteInputForwardingUseCase` 應記錄清楚 log
- control mode 下回傳 `SUPPRESS`

這延續前一輪修正後的安全邏輯，避免 unsupported key 在遠端控制時意外作用在本機。

## 鍵級別策略

### 優先 end-to-end relay 的鍵

下列鍵應優先嘗試補齊 HID、平台 mapping 與 legacy relay mapping：

- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- application/menu key

其中若某鍵在 relay 邊界上無法建立穩定對應，可退回 local-only，但必須有明確測試與文件說明，不可默默缺漏。

### JIS 鍵策略

JIS 鍵分成兩層能力：

- `HID-capable`：一定要支援。Windows/macOS 若能穩定辨識，必須映成對應 usage。
- `Relay-capable`：只有在 legacy payload 對應明確時才支援。

因此，JIS 鍵在本輪的完成定義不是「全部都能 relay」，而是：

- 共通 HID 可表示
- 平台層能正規化
- relay 能力逐鍵明確決定，而不是模糊未知

## 檔案層級變更

### `src/interop/key/hid.py`

新增以下 HID 常數群組：

- 特殊控制鍵：`PRINT_SCREEN`、`SCROLL_LOCK`、`PAUSE`、`NUM_LOCK`、`APPLICATION`
- JIS 常數：`NON_US_HASH`、`INTERNATIONAL1`、`INTERNATIONAL3`、`INTERNATIONAL4`、`INTERNATIONAL5`

維持同一檔案內按區塊分組，不引入新的抽象層。

### `src/adapters/windows/hid_map.py`

補上 Windows `scanCode + extended (+ vkCode only when necessary)` 到新增 HID usage 的映射。

原則：

- 仍以 `scanCode + extended` 為主
- 只有在某些特殊鍵需要排歧義時才輔助參考 `vkCode`
- 若 JIS 鍵無法穩定映射，不新增脆弱規則

### `src/adapters/macos/hid_map.py`

補上 macOS virtual key code 到新增 HID usage 的映射。

原則：

- JIS 部分優先補齊，因為 macOS 對日文鍵盤佈局通常有更直接的 key code 區分
- 其餘特殊鍵只有在目前 event tap 路徑真的能穩定捕獲時才加入

### `src/apps/nvda_remote/legacy_key_payload.py`

新增可辯護的 legacy 映射：

- 對特殊控制鍵：若存在穩定 `vk_code/scan_code/extended`，則加入 `_USAGE_TO_LEGACY`
- 對 JIS 鍵：逐鍵判斷；可支援者加入，不可支援者維持 `ValueError`

這個模組仍是唯一知道 legacy payload 細節的位置。

### `src/apps/nvda_remote/use_cases/input_forwarding.py`

行為模型不變，但測試要擴充到新的 local-only 鍵：

- unsupported 特殊鍵：`SUPPRESS + log`
- unsupported JIS 鍵：`SUPPRESS + log`

## 資料流

### 本地輸入

1. 平台 adapter 捕獲原生鍵盤事件。
2. Windows/macOS mapping 將事件轉成 HID `KeyEvent`。
3. `application` / `apps` 只依賴 HID。
4. 即使某鍵不能 relay，本地 app 邏輯仍可辨識它。

### 遠端轉送

1. `nvda_remote` 收到 HID `KeyEvent`。
2. 若 `legacy_key_payload.py` 可穩定轉換，產生既有 `key` payload。
3. 若無法穩定轉換，拋出 `ValueError`。
4. forwarding use case 記 log 並在 control mode 下 suppress 該鍵。

## 測試策略

### 單元測試：HID 常數

在 `tests/unit/test_hid_keys.py` 補上：

- 特殊控制鍵的 usage 值測試
- JIS 常數的 usage 值測試
- 與既有 ANSI/ISO 鍵的 distinction 測試

### 單元測試：Windows adapter

在 `tests/unit/test_windows_adapters.py` 補上：

- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- application/menu key
- 每個納入範圍的 JIS 鍵

測試必須直接驗證 hook callback 產生的 HID `KeyEvent`，不能只測 helper function。

### 單元測試：macOS adapter

在 `tests/unit/test_macos_adapters.py` 補上：

- 可由 event tap 穩定收到的特殊控制鍵
- 納入範圍的 JIS 鍵

若某鍵在 macOS 路徑上無法穩定取得，測試應明確標記設計限制，而不是省略。

### 單元測試：legacy relay adapter

在 `tests/unit/test_nvda_remote_legacy_key_payload.py` 補上兩類測試：

- `relay-capable`：驗證 payload 值精準正確
- `local-only`：驗證拋出 `ValueError`

這份測試應成為每顆新增鍵 relay 能力的唯一真相來源。

### 單元測試：forwarding safety

在 `tests/unit/test_nvda_remote_use_cases.py` 補上：

- unsupported 特殊鍵在 control mode 下被 suppress
- unsupported JIS 鍵在 control mode 下被 suppress
- log 內容包含足夠辨識資訊，便於後續追蹤

## 風險

### 1. 特殊鍵在平台間語意不完全對稱

像 `Pause`、`PrintScreen` 這類鍵在不同平台與不同底層事件模型中的表示方式，可能不是一般單鍵的穩定對應。即使本地能抓到，也不代表 relay 可重建一致行為。

### 2. JIS 與 legacy relay 之間存在根本語意落差

JIS 鍵盤的部分專用鍵在 HID 上有清楚 usage，但 legacy relay 仍受限於 Windows-style `vk/scan/extended`。這代表「HID 支援」與「relay 支援」本來就不會完全重疊。

### 3. 錯誤的降級映射比明確 unsupported 更危險

若為了追求表面上的 relay 覆蓋率而使用近似 mapping，會讓遠端實際收到錯鍵，這比清楚地 local-only 更難 debug，也更容易造成控制模式下的誤操作。

## 結論

本輪應把特殊鍵與 JIS 鍵視為既有 HID 擴充的下一個受控階段：先把鍵納入 HID 與平台正規化，然後在 relay 邊界採 best-effort，對無法穩定表示的鍵維持 explicit local-only。這樣可以在不破壞現有架構與安全模型的前提下，擴大共通鍵盤輸入模型的真實覆蓋範圍。
