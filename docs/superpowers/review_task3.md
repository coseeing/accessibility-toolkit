# Review Task 3: AUTO Golden Trace

## 審查範圍

依 `docs/superpowers/finish_task3.md` 所列 commit，並按 commit 時間由舊到新審查：

1. `16c5da8 test: trace access8graph auto transitions`

後續 `47c3c31 docs: record task 3 review completion` 未列於完成報告，因此不納入
程式碼審查。

對照文件：

- `docs/superpowers/specs/2026-06-27-application-boundaries-and-access8graph-transition-engine-design.md`
- `docs/superpowers/plans/2026-06-27-application-boundaries-and-access8graph-transition-engine-implementation.md`
- `docs/superpowers/review_task2.md`

目前工作樹另有尚未提交的車站左右移動朗讀修正。為避免該變更影響審查結果，本次
測試於 detached `16c5da8` temporary worktree 執行。

## Findings

**未發現 Critical、High、Medium 或 Low finding。**

前次 `review_task2.md` 指出的 AUTO intermediate transition sequence 缺口已完成
修正，未發現這次修正引入新的 transition、presentation 或 mutable-state 問題。

## 修正驗證

### Immutable AUTO trace

`TransitionResult.auto_steps` 使用 immutable tuple，單一步驟內容為：

```text
(source_state, action_id, target_state)
```

其中 state 與 action 都是 immutable identifier，沒有保存
`NavigationContext`、navigator 或其他 mutable object reference。

### 記錄邊界

engine 的記錄行為符合預期：

- 一般 external non-AUTO transition 不會加入 `auto_steps`。
- external transition 後發生的成功 AUTO commit 會依執行順序加入。
- 直接 dispatch `NavigationCommand.AUTO` 時，第一個 AUTO commit 不會遺漏。
- action rejected 或未 commit target 的步驟不會被記為成功 AUTO commit。
- 多步 AUTO macrostep 會回傳 ordered tuple，不依賴 transition table 的集合順序。

### Golden parity

`FlowTrace` 已納入 `auto_steps`，全部 121 筆固定 golden trace 都具有此欄位。六個
single-option AUTO scenario 分別保存其實際 source、action 與 target：

- direction lines
- undirected lines
- source stations / lines
- destination stations / lines

新增 regression test 也證明 final state 相同但 AUTO action/path 不同時，不會與
golden trace 相等。

## 測試結果

於 detached `16c5da8` worktree 執行針對性測試：

```bash
pytest \
  tests/unit/test_access8graph_transition_engine.py \
  tests/unit/test_access8graph_transition_parity.py -q
```

結果：`149 passed`。

完整測試：

```bash
pytest tests/unit tests/integration -q
```

結果：`787 passed`。

隔離 worktree 原先缺少未受 Git 追蹤的
`Access8Graph/tests/test.graphml`，補入主工作區相同 fixture 後完整測試通過；
第一次的 13 個 `FileNotFoundError` 屬測試環境缺件，不是本 commit 回歸。

## 結論

`16c5da8` 已完成前次 review 要求，可結束 AUTO golden-trace finding。這次新增的
trace contract 與既有 macrostep、presentation ordering 及 fixed-target
transition design 相容。

## 殘餘風險

- Windows/macOS speech backend、wx UI 與 keyboard hook 未在實機驗證。
- 目前主工作樹的車站左右移動朗讀修正不屬於 `finish_task3.md` 所列 commit，
  因此不包含在本次通過結論內。
