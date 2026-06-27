# Review Task 2: Access8Graph Review Corrections

## 審查範圍

依 `docs/superpowers/finish_task2.md` 所列 commit，並按 commit 時間由舊到新審查：

1. `386a6ad fix: complete access8graph review corrections`

後續 `911a5d2 docs: record task 1 review completion` 未列於完成報告，因此不納入
程式碼審查。工作樹內其他未追蹤或已刪除文件亦不在本次審查範圍。

對照文件：

- `docs/superpowers/specs/2026-06-27-application-boundaries-and-access8graph-transition-engine-design.md`
- `docs/superpowers/plans/2026-06-27-application-boundaries-and-access8graph-transition-engine-implementation.md`
- `docs/superpowers/review1-1.md`

## 結論

**大部分修正已完成，但完整 AUTO golden-trace parity 仍有缺口。**

前次 Help CONFIRM、公開 startup API 與固定 golden fixture 等問題均已修正，完整
測試也通過。未發現本次程式修正造成新的功能性回歸。

## Findings

### High 1：AUTO golden trace 未記錄 intermediate transition sequence

**狀態：前次 High 2 部分完成**

**位置：**

- `tests/unit/test_access8graph_transition_parity.py:179`
- `tests/unit/test_access8graph_transition_parity.py:196`
- `tests/unit/test_access8graph_transition_parity.py:241`
- `tests/unit/data/access8graph_legacy_traces.json`

本次已將全部 121 個 scenario 改為固定 golden trace 比較，且確實比較：

- ordered output calls
- direction/undirection navigator fields
- return/background state
- final state

但是 `capture_transition_trace()` 對 AUTO 只呼叫一次
`engine.dispatch(NavigationCommand.AUTO)`，最後建立的 `FlowTrace` 也只有 macrostep
結束後的 observable state。它沒有保存每一步 AUTO transition 的 source、rule、
target 或順序。

因此以下錯誤仍可能無法被 golden test 發現：

```text
expected: A -> AUTO -> B -> AUTO -> C
actual:   A -> AUTO -> D -> AUTO -> C
```

只要兩條路徑最後產生相同 final state、navigator fields 與合併後 presentation
effects，現有 golden comparison 就會通過。這與前次 review 明確要求「AUTO
scenarios 必須記錄並比較 intermediate transitions」仍有落差。

**必要修正：**

- 在 parity trace 中加入 AUTO step sequence，例如
  `(source_state, action_id, target_state)`。
- 由 engine 提供可測試但不洩漏 mutable context 的 macrostep trace，或在測試用
  observer 中記錄每次成功 commit。
- 將 AUTO scenarios 的預期 step sequence 固定到 golden data，並加入「相同終態、
  不同中間路徑」會失敗的 regression test。

## 已完成修正驗證

### Help CONFIRM 與 QUIT

目前 13 個可開啟 Help 的來源 state 均有 QUIT 返回規則。16 個 CONFIRM 規則以
`return_state + selected_id` 建立互斥 guard，涵蓋：

- generic、direction、undirected、source、destination 的 station/line 切換
- direction、undirected、plan run 的 mode/browser 動作

undirected 分支會修改 `undirection_nav`，其餘對應分支修改
`direction_nav`。前次錯誤固定跳至 `DIRECTION_LINES` 的問題已排除。

### Startup 與 presentation

`MrtFlowFactory` 已改呼叫公開的 `TransitionNavigationFlow.start()`，不再 import
engine 的 `_current_view_effects` 或 `_merge_effects`。startup、self-transition、
state transition 與 rejected presentation 的測試均通過；rejected 維持
`beep -> cancel -> speak`，hint 不會在 self-transition 重複。

### AUTO 邊界

engine 會先確認是否仍有 matching AUTO rule，再檢查 step limit。測試證明：

- 恰好完成 32 次且無下一條 matching rule：成功
- 第 33 條 matching rule：拋出 `AutomaticTransitionCycleError`

### Golden trace

121 個 scenario 與 121 筆固定 golden data 的 ID 完全相符。除上述 AUTO
intermediate sequence 缺口外，現有 trace 欄位均執行 exact comparison。

## 測試結果

針對性測試：

```bash
pytest \
  tests/unit/test_access8graph_transition_parity.py \
  tests/unit/test_access8graph_transition_table.py \
  tests/unit/test_access8graph_transition_engine.py \
  tests/unit/test_access8graph_speech_regression.py \
  tests/integration/test_access8graph_mrt_flow.py -q
```

結果：`175 passed`。

完整測試：

```bash
pytest tests/unit tests/integration -v
```

結果：`786 passed`。

## 殘餘風險

- AUTO intermediate transition sequence 尚未固定為 regression contract。
- 本次未在 Windows/macOS 實機驗證 speech backend、wx UI 與 keyboard hook。
