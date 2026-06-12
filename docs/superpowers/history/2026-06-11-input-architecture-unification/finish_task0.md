# Input Architecture Unification — 完成報告

## 概述

依據 [spec](specs/2026-06-11-input-architecture-unification-design.md) 與 [plan](plans/2026-06-11-input-architecture-unification-implementation.md)，完成 `nvda_remote` 與 `key_echo` 的 input lifecycle 統一化重構。

兩個 app 現已採用相同的 `idle hotkey / active keyboard` 輸入生命週期模型。

## 完成準則驗證

| # | 準則 | 狀態 |
|---|------|------|
| 1 | `nvda_remote` 與 `key_echo` 皆使用 `idle hotkey / active keyboard` lifecycle | ✅ |
| 2 | `key_echo` 擁有正確的 `HotkeyCapture` idle 啟用路徑 | ✅ |
| 3 | Active 狀態的退出鍵在 active keyboard pipeline 內處理 | ✅ |
| 4 | 共享的 input lifecycle 與 transition policy 元件已提取 | ✅ |
| 5 | App facades 不再包含主要的 capture-switching state machine | ✅ |
| 6 | Shutdown/teardown 正確停止所有 captures | ✅ |
| 7 | 現有 UI controller 介面保持相容 | ✅ |
| 8 | 測試直接覆蓋共享 lifecycle rollback 與 app-level hotkey 行為 | ✅ |

## 新增/修改的共享元件

### `src/application/input/` (新增)

| 檔案 | 用途 |
|------|------|
| `activation.py` | `InputActivationUseCase` — capture lifecycle transitions，含 rollback 邏輯 |
| `state_transition_hotkeys.py` | `StateTransitionHotkeyPolicy` — idle 熱鍵對映 |
| `active_key_policy.py` | `ActiveKeyEventPolicy` — active 鍵盤路由，含退出鍵偵測 |
| `__init__.py` | 公開 exports |

### App Facade 改寫

- **`src/apps/nvda_remote/facade.py`**: 組合 `InputActivationUseCase` + `ActiveKeyEventPolicy` 取代自有的 state machine
- **`src/apps/key_echo/facade.py`**: 新增 `HotkeyCapture` 支援，組合共享元件
- **`src/apps/key_echo/main.py`**: 啟動時以 `hotkey_capture.start()` 取代 `input_service.start()`

### Use Case 簡化

- **`src/apps/nvda_remote/use_cases/control_mode.py`**: 移除 capture start/stop，僅保留 business state 與 status
- **`src/apps/key_echo/use_cases/echo_control.py`**: 移除 `KeyboardInputService` 依賴，僅保留 echo state

## 測試覆蓋

**248 tests passed, 0 failed**

| 測試檔案 | 新增內容 |
|----------|---------|
| `tests/unit/test_input_activation.py` | 2 測試 (enter_active 成功/rollback) |
| `tests/unit/test_input_policies.py` | 2 測試 (hotkey match, exit key routing) |
| `tests/unit/test_key_echo_app_service.py` | 4 新測試 (hotkey path, escape exit, idle mode, shutdown) |
| `tests/unit/test_nvda_remote_app_service.py` | 1 新測試 (F11 hotkey capture path) |

## Commit 列表

```
b22ea8f test: verify unified input runtime wiring
9c8cb9d fix: wire input capture listener, implement set_active callback for key_echo
ee8a783 refactor: unify key echo input lifecycle
d4bddff fix: remove dead code, fix test for public API, remove duplicate test
4260c4b refactor: route nvda remote through shared input lifecycle
93edac4 fix: add is_active guard, track hotkey stop, rollback in exit_active
4e9b338 feat: add shared input lifecycle components
5552dc4 chore: remove unused import, follow naming convention
797c165 fix: correct hotkey capture path test setup
6b5feec fix: remove broken assertion in idle f11 hotkey test
76cff16 test: add input lifecycle regression coverage
```

## 變更統計

```
15 files changed, 1274 insertions(+), 173 deletions(-)
```
