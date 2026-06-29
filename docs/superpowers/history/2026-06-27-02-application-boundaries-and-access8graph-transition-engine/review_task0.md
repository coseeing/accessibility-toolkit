# Code Review：Application Boundaries and Access8Graph Transition Engine

## 結論

**建議修正後再合併。**

主要功能與既有行為測試均通過，先前 review 所指出的 presentation、Help、
AUTO trace 與 typed contract 問題也已在後續 commits 修正。但 transition table
的完整性驗證仍有兩個缺口，與 spec／plan 明列的負向驗證契約不符；這些問題會讓
錯誤的 extension configuration 通過啟動期驗證，延後到 runtime 才失敗。

## Findings

### Medium 1：validator 沒有驗證 rule 的 state／command 型別，未知 ID 可通過或造成非預期例外

**引入 commit：** `0f524ac`

**目前位置：**

- `src/apps/access8graph/navigation/validation.py:46`
- `src/apps/access8graph/navigation/validation.py:70`
- `src/apps/access8graph/navigation/validation.py:90`
- `src/apps/access8graph/navigation/validation.py:118`

Spec 明確要求 `TransitionTableValidator` 拒絕 unknown command、state、action 與
guard ID，但 `_validate_ids()` 目前只檢查 action 與 guard。Python dataclass 的型別
提示不會在 runtime 強制執行，因此 extension 若誤用字串或錯誤 enum，validator
不會可靠地拒絕：

- unknown command 可直接通過 validation；
- unknown target state 可直接通過 validation；
- unknown source state 會在 reachability error formatting 時洩漏
  `AttributeError`，而不是 `TransitionTableValidationError`。

針對性 probe 結果：

```text
unknown_source  AttributeError 'str' object has no attribute 'value'
unknown_command ACCEPTED
unknown_target  ACCEPTED
```

unknown target 一旦被 transition commit，`NavigationContext.current_state` 就不再是
`NavigationStateId`，後續 snapshot、lookup 與錯誤訊息都可能在 runtime 失敗。
這破壞了「組裝時驗證，接受 command 前拒絕錯誤 table」的設計目標。

**建議修正：**

1. 在建立 index 前，以 `isinstance` 明確驗證 `source`／`target` 為
   `NavigationStateId`、`command` 為 `NavigationCommand`。
2. 對 invalid initial state 同樣先做型別驗證。
3. 對 unknown source、target、command、initial state 各加入負向測試，並統一要求
   `TransitionTableValidationError`。

### Medium 2：完全相同的 guarded rule 可重複註冊，必然在 runtime 形成 ambiguity

**引入 commit：** `0f524ac`

**目前位置：**

- `src/apps/access8graph/navigation/validation.py:41`
- `src/apps/access8graph/navigation/validation.py:47`
- `src/apps/access8graph/navigation/validation.py:100`
- `src/apps/access8graph/navigation/engine.py:89`

Plan 的 negative integrity matrix 要求 validator 拒絕 duplicate rule。目前
`_validate_unguarded_conflicts()` 只拒絕多個 unguarded rules，沒有檢查完全相同的
guarded rule。兩筆相同 guarded rule 會同時保留在 `index`；當 guard 為 true 時，
engine 會取得兩個 matches 並拋出 `AmbiguousTransitionError`。

針對性 probe 使用兩筆完全相同的：

```python
TransitionRule(MODE, DOWN, MODE, ActionId("a"), GuardId("g"))
```

validation 成功，且 lookup 中保留兩筆 rule：

```text
duplicate_guarded_accepted 2
```

`TransitionTable.rules` 隨後又轉成 `frozenset`，使公開的 rule collection 顯示一筆，
但 `index` 實際有兩筆；同一個 table 內部因此出現不一致表示。

**建議修正：**

1. 在建立 index 前檢查 `len(rules_tuple) != len(set(rules_tuple))`，直接拒絕任何
   exact duplicate。
2. 新增 guarded duplicate 負向測試，並驗證不會建立 `rules`／`index` 數量不一致
   的 table。

## 逐 Commit 審閱紀錄

以下依 commit 時間由舊到新審閱，範圍嚴格限定為 `39a9c30675..HEAD`：

| Commit | 審閱結果 |
|---|---|
| `e0d3e65` | Keyboard service relocation 符合 package boundary。 |
| `367d450` | Speech settings persistence 已移至 adapter 並保留 schema 行為。 |
| `9cf4568` | Speech ports 已依 consumer role 拆分。 |
| `5ebb562` | Compatibility aliases 移除，NVDA Remote state ownership 正確。 |
| `7b1fa21` | wx shell ownership 移至 `ui.shared`，未見行為變更。 |
| `89090fb` | 建立 legacy characterization baseline；後續 commits 補齊 golden trace。 |
| `f7daebe` | Typed command/state/result model 符合 fixed-target 設計。 |
| `784012f` | Snapshot 為 frozen value object，guard input boundary 正確。 |
| `0f524ac` | Validator 主體成立，但留下本次兩項 integrity findings。 |
| `39527af` | Macrostep、ambiguity 與 AUTO engine 建立；後續修正邊界問題。 |
| `18cef14` | Presentation abstraction建立；後續修正 output semantics。 |
| `0a9ce7f` | 修正初版 AUTO cycle detection；Help validation 後續補強。 |
| `5c8f84f` | 完整 actions/table/flow 建立；初版 parity 問題已由後續 commits 修正。 |
| `2f84524` | Production 切換至 typed command 與 transition engine。 |
| `f07f985` | Legacy state flow 移除，未殘留舊 import。 |
| `a4bd539` | Actions/tables 依 concern 分組並補 extension 文件。 |
| `240d833` | 修正 entry/self-transition/help/AUTO/typed contract 的第一輪問題。 |
| `05a1ecc` | 移除 actions compatibility re-exports。 |
| `386a6ad` | 完成 Help、presentation、golden speech trace 等 review 修正。 |
| `911a5d2` | 僅文件紀錄，未見程式問題。 |
| `16c5da8` | AUTO intermediate steps 納入 immutable golden trace。 |
| `47c3c31` | 僅文件紀錄，未見程式問題。 |
| `b219644` | 補齊 run-state 移動後 view rebuild 與整合測試；未見新功能回歸。 |

## 驗證

執行：

```bash
pytest tests/unit tests/integration -q
```

結果：

```text
788 passed in 1.63s
```

另執行：

- `python3 -m compileall -q src tests`：通過。
- 最終 architecture scan：未發現已移除的 application imports、speech aliases、
  wx 舊路徑、dynamic state dispatch 或 dynamic target contract；唯一 match 是測試
  對 `allowed_targets` 不存在的 assertion。
- 針對 validator 執行 malformed rule 與 duplicate guarded rule probes，確認上述
 兩項 findings。

## 審閱範圍與工作樹狀態

審閱過程中工作樹已有使用者進行中的文件搬移：原本位於
`docs/superpowers/` 的既有 `finish_task*.md`／`review_task*.md` 顯示為刪除，
對應內容出現在未追蹤的 `docs/superpowers/history/`。本次未修改、還原或提交這些
既有變更，只新增本檔案。

本次未在 Windows/macOS 實機驗證 wx、speech backend 與 keyboard hook；這些仍屬
平台整合殘餘風險。
