# Review Task 1：Transition Table Integrity 修正驗證

## 審閱範圍

依 `docs/superpowers/finish_task1.md` 所列 commit，並按實際提交時間由舊到新審閱：

1. `fee60b9` — `fix: validate access8graph transition rule integrity`

Completion report 本身的文件 commit 未列出，因此不納入程式碼審閱。對照文件：

- `docs/superpowers/review_task0.md`
- `docs/superpowers/specs/2026-06-27-application-boundaries-and-access8graph-transition-engine-design.md`
- `docs/superpowers/plans/2026-06-27-application-boundaries-and-access8graph-transition-engine-implementation.md`

## 結論

**前次兩項 Medium findings 均已完成修正；未發現 `fee60b9` 引入新的功能或架構問題。**

修正發生在 lookup index 建立前，能讓 malformed extension table 在 assembly 階段
以一致的 `TransitionTableValidationError` 失敗，符合 spec 的 fail-fast 契約。
新增 duplicate check 也同時處理 guarded 與 unguarded exact duplicates，不再產生
`rules` 與 `index` 數量不一致的 table。

本次 scoped fix 可通過 review。不過 repository 仍有一個不屬於 `fee60b9` 的
hash-order-dependent integration test；因此目前不能宣稱標準完整 suite 穩定全綠。

## Findings

**未發現由本次修正造成的 Critical、High、Medium 或 Low finding。**

## 前次 Findings 修正驗證

### Medium 1：未知 state／command 與 invalid initial state

**狀態：已修正**

`_validate_rule_types()` 現在於 `_build_index()` 與 reachability analysis 前驗證：

- `initial_state` 必須是 `NavigationStateId`
- rule `source` 必須是 `NavigationStateId`
- rule `command` 必須是 `NavigationCommand`
- rule `target` 必須是 `NavigationStateId`

原始重現案例目前全部得到預期 exception：

```text
source    TransitionTableValidationError
command   TransitionTableValidationError
target    TransitionTableValidationError
initial   TransitionTableValidationError
```

因此 unknown command／target 不再通過 validation，unknown source／initial state
也不再洩漏 `AttributeError`。

### Medium 2：重複 guarded rule

**狀態：已修正**

`_validate_duplicates()` 在 index 建立前比較 tuple 與 set 的數量，任何完全相同的
`TransitionRule` 都會被拒絕。原始 duplicate guarded probe 現在得到：

```text
duplicate TransitionTableValidationError duplicate transition rule
```

這同時避免了：

- matching guard 在 runtime 產生必然 ambiguity
- `TransitionTable.rules` 去重、但 `TransitionTable.index` 保留重複項目的內部不一致

既有 duplicate unguarded validation 仍保留，用於拒絕同一 source／command 下
內容不同的多個 unguarded rules；兩層檢查的責任沒有衝突。

## Commit 審閱紀錄

| Commit | 審閱結果 |
|---|---|
| `fee60b9` | 修改僅涉及 transition table validation 與 focused negative tests。型別檢查先於 ID、index、reachability 檢查；exact duplicate 檢查先於 index assembly。兩項前次 findings 均已封閉，未見新回歸。 |

## 驗證結果

### Focused tests

```bash
pytest \
  tests/unit/test_access8graph_transition_table.py \
  tests/unit/test_access8graph_transition_engine.py \
  tests/unit/test_access8graph_navigation_model.py -q
```

結果：

```text
39 passed in 0.10s
```

另直接重跑 invalid source、command、target、initial state 與 duplicate guarded rule
五組原始 probes，全部得到 `TransitionTableValidationError`。

### Static verification

```bash
git diff --check fee60b9^ fee60b9
python3 -m compileall -q src tests
```

兩者均成功且無輸出。`fee60b9` 的 changed files 僅有：

```text
src/apps/access8graph/navigation/validation.py
tests/unit/test_access8graph_transition_table.py
```

### Full suite

```bash
pytest tests/unit tests/integration -q
```

本次結果：

```text
1 failed, 792 passed in 2.41s
```

唯一失敗：

```text
tests/integration/test_access8graph_mrt_flow.py::
test_undirected_station_navigation_speaks_station_after_moving_right
```

這是 `finish_task1.md` 已揭露的既有 hash-order-dependent assertion，且 production
path 與該測試均不在 `fee60b9` diff 中。固定 seed 重現結果：

```text
PYTHONHASHSEED=1  pass
PYTHONHASHSEED=2  pass
PYTHONHASHSEED=3  fail
PYTHONHASHSEED=4  fail
```

因此它不是本次 validator 修正造成的新問題，也不推翻本次 scoped fix 的通過結論；
但在該 nondeterminism 修正前，完整 suite 仍可能隨 hash seed 隨機失敗。

## 殘餘風險

- 既有 undirected station navigation 測試／行為依賴集合或 graph traversal 順序，
  需要獨立修正或將 assertion 改為符合明確 deterministic contract。
- Windows/macOS speech backend、wx UI 與 keyboard hook 未在實機驗證；本 commit
  未修改這些路徑。
