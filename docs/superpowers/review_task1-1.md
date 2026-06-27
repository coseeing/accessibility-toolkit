# Review 1-1: Uncommitted Review Fixes

## 審查範圍

`05a1ecc` 之後沒有新增 git commit。此次修正目前全部位於未提交的 working tree：

- 8 個已修改檔案
- 1 個新增測試檔 `tests/unit/test_access8graph_speech_regression.py`

因此本次無法依「新增 commit」排序審查；以下以 `05a1ecc..working tree` 的實際 diff
為審查範圍。未修改或提交使用者的程式變更。

## 結論

**大部分修正已完成，但仍不建議結案。**

已完成：

- startup、state transition、self-transition、rejected presentation semantics
- hint 只朗讀一次
- view items 不再重複
- rejected 恢復 beep -> cancel -> speak
- Help QUIT 可返回所有目前可開啟 Help 的來源 state
- 恰好 32 次 AUTO 成功，第 33 次才失敗
- 標準完整測試通過，結果為 `772 passed`

仍未完成：

1. Help CONFIRM 對不同 `return_state` 仍使用錯誤的固定 target。
2. 完整 121-scenario golden-trace parity 仍未建立。

另有一項新架構問題：composition layer 開始直接 import transition engine 的私有
helpers。

## Findings

### Critical 1：Help CONFIRM 沒有依 `return_state` 分支，會跳到錯誤的 state

**狀態：Critical 2 僅完成 QUIT，CONFIRM 仍未修正**

**位置：**

- `src/apps/access8graph/navigation/tables/transfer.py:94`
- `src/apps/access8graph/navigation/tables/transfer.py:110`
- `src/apps/access8graph/navigation/actions/transfer.py:14`

本次新增了完整的 Help QUIT guards/rules，這部分修正正確。但 Help CONFIRM 仍只依
所選 command 使用單一固定 target：

```text
selected "m" -> MODE
selected "v" -> LINES
selected "s" -> DIRECTION_STATIONS
selected "l" -> DIRECTION_LINES
selected "e" -> DIRECTION_END_POINT
```

這沒有考慮 Help 是從哪個 state 開啟。

實際 probe：

```text
STATIONS + OPEN_HELP + CONFIRM("l")
  expected: LINES
  actual:   DIRECTION_LINES

SOURCE_STATIONS + OPEN_HELP + CONFIRM("l")
  expected: SOURCE_LINES
  actual:   DIRECTION_LINES

UNDIRECTION_STATIONS + OPEN_HELP + CONFIRM("l")
  expected: UNDIRECTION_LINES
  actual:   DIRECTION_LINES
```

舊 flow 的 `HelpState.onok()` 會先回到原 state，再執行該 state 的 help command；
因此同一個 `"l"`／`"s"` 必須依 `return_state` 有不同 target 與 action mutation。

新增的 speech regression tests 只驗證 Help QUIT，沒有驗證 Help CONFIRM。

**必要修正：**

1. Help CONFIRM rules 必須同時以 `return_state` 與 `selected_id` 建立互斥 guards。
2. 每條規則使用來源家族對應的固定 target：
   - generic stations/lines
   - direction stations/lines
   - undirected stations/lines
   - source stations/lines
   - destination stations/lines
   - run mode/browser
3. action mutation 也必須依來源 navigator family 執行。
4. 為每個 Help item／來源 state 組合增加 confirm regression tests。

### High 2：完整 golden-trace parity 仍未完成

**狀態：review_task1 High 3 未修正**

**位置：**

- `tests/unit/access8graph_flow_scenarios.py:28`
- `tests/unit/test_access8graph_transition_parity.py:218`
- `tests/unit/test_access8graph_speech_regression.py:1`

新增的 speech regression file 對 7 個高風險路徑加入 exact output assertions，成功
攔住上一輪的 startup、hint、duplicate view 與 rejected ordering 問題；這是有效的
改進。

但原本 121 個 scenarios 仍只檢查：

- final state
- 是否 beep

沒有比較已收集在 `FlowTrace` 內的：

- ordered output calls
- navigator fields
- background/return state

也沒有保存／比較 AUTO intermediate steps。新增 7 個測試不能取代 spec 與 plan
要求的完整 scenario parity，因此其他 transition family 仍可能存在未被發現的
speech ordering 或 navigator mutation 回歸。

**必要修正：**

- 為全部 scenarios 加入完整 expected `FlowTrace` 或等價 golden data。
- exact compare output calls、direction/undirection navigator fields、
  return/background state 與 final state。
- AUTO scenarios 必須記錄並比較 intermediate transitions。

### Medium 3：`MrtFlowFactory` 直接依賴 engine 私有 helpers

**狀態：本次新增的架構問題**

**位置：**

- `src/apps/access8graph/use_cases/navigation.py:19`
- `src/apps/access8graph/use_cases/navigation.py:103`

為修正 startup presentation，`MrtFlowFactory` 現在直接 import：

```python
from apps.access8graph.navigation.engine import (
    _current_view_effects,
    _merge_effects,
)
```

這使 composition/use-case layer 依賴 engine 的私有實作細節，且
`tests/unit/test_access8graph_speech_regression.py` 又複製同一段 startup 組裝流程。
後續只要 engine effect model 改變，factory 與 tests 都必須同步修改。

**建議修正：**

- 將初始化 macrostep／initial presentation 提供成
  `TransitionNavigationFlow.start()`、engine public method，或獨立 public
  presentation assembler。
- `MrtFlowFactory` 只負責組裝並呼叫公開 API，不 import underscore helpers。
- 測試透過正式 factory/public initialization path 驗證 startup。

## 已完成修正驗證

### Presentation semantics

實際輸出：

```text
startup:
  cancel
  speak("功能選單開啟", hint, "方向探索", "3 之 1")

MODE + DOWN:
  cancel
  speak("線性探索", "3 之 2")

MODE + UP:
  cancel
  speak("方向探索", "3 之 1")

MODE + rejected UP:
  beep
  cancel
  speak("方向探索", "3 之 1")
```

未再發現 hint 重播或 view items 重複。

### Help QUIT

新增 guards/rules 已涵蓋：

- DIRECTION_RUN
- UNDIRECTION_RUN
- PLAN_RUN
- STATIONS / LINES
- DIRECTION_STATIONS / DIRECTION_LINES
- UNDIRECTION_STATIONS / UNDIRECTION_LINES
- SOURCE_STATIONS / SOURCE_LINES
- DESTINATION_STATIONS / DESTINATION_LINES

抽查 DIRECTION_RUN、DIRECTION_STATIONS、UNDIRECTION_RUN 均可正確返回。

### AUTO 32/33

engine 現在先查詢及評估下一條 AUTO rule，再檢查 step limit：

- 完成 32 次後若沒有 matching rule：成功
- 準備執行第 33 次 matching rule：拋出
  `AutomaticTransitionCycleError`

新增測試已分別涵蓋兩種情況。

## 測試結果

### 完整測試

```bash
pytest tests/unit tests/integration -q
```

結果：`772 passed`。

### 針對性修正測試

```bash
pytest \
  tests/unit/test_access8graph_transition_engine.py::test_exactly_32_auto_steps_with_no_more_rules_succeeds \
  tests/unit/test_access8graph_transition_engine.py::test_32_automatic_steps_succeed_33_raises_cycle_error \
  tests/unit/test_access8graph_speech_regression.py -q
```

結果：`9 passed`。

### Help CONFIRM probe

由 STATIONS、SOURCE_STATIONS、UNDIRECTION_STATIONS 開啟 Help 並 confirm `"l"`，
三者均錯誤進入 `DIRECTION_LINES`，證實 Critical finding。

## 建議修正順序

1. 完成 Help CONFIRM 的 `return_state + selected_id` 固定 target matrix。
2. 補齊全部 121 scenarios 的 golden-trace parity。
3. 將 startup presentation 收斂為 transition flow 的公開 API。
4. 提交目前 working-tree 修正後，再以 commit 範圍執行下一輪 review。

## 殘餘風險

- 修正尚未 commit，後續 diff 可能變動，無法建立穩定 commit-level 審查基準。
- 目前完整測試雖通過，但仍未驗證完整 observable parity。
- 本次未在 Windows/macOS 實機執行 speech backend、wx 或 keyboard hook。
