# Review Task 1: Review Fix Verification

## 結論

**修正尚未完成，目前仍不建議合併。**

本次限定審查的 commit 依實際提交時間為：

1. `240d833` — `fix: entry view presentation, self-transition lifecycle, help snapshot, auto boundary, typed contract`
2. `05a1ecc` — `refactor: remove compatibility re-exports from actions init`

`review_task0.md` 的 High 3、Medium 6、Medium 7 已實質修復；Critical 1、
Critical 2、High 4、Medium 5 仍未完整完成。`240d833` 另外引入 self-transition
重複朗讀 view 與每次重播 hint 的新回歸。

## Findings

### Critical 1：語音呈現仍未達 parity，且 self-transition 新增重複朗讀

**修正狀態：部分修正，並產生新問題**

**位置：**

- `src/apps/access8graph/navigation/engine.py:158`
- `src/apps/access8graph/navigation/engine.py:170`
- `src/apps/access8graph/navigation/engine.py:198`
- `src/apps/access8graph/navigation/actions/common.py:411`
- `src/apps/access8graph/use_cases/navigation.py:98`
- `src/apps/access8graph/navigation/presenter.py:27`

`240d833` 已做到：

- state transition 後加入新 view display
- rejected result 加入目前 view
- source == target 時不再執行 exit/entry lifecycle

但目前仍有三個問題。

#### 1. Self-transition 會重複兩次 view items

list movement action 本身已回傳新 view：

```python
PresentationEffects(view_items=_list_view_items(vm))
```

engine 的 same-target branch 又合併 `_current_view_effects(context)`，因此 label 與
position 會重複兩次。

實際結果：

```text
MODE + DOWN:
  speak(
    "請使用上下鍵選擇導航模式",
    "線性探索",
    "3 之 2",
    "線性探索",
    "3 之 2",
  )
```

這是 `240d833` 新引入的回歸。

#### 2. Hint 每次移動都重播

`_current_view_effects()` 每次都從 view model 讀取永久保存的 `hint`。目前沒有
「本 state 已朗讀過 hint」的狀態，因此每次 UP/DOWN/HOME/END 都會重新朗讀提示。
舊 flow 的 `state.hint` 在首次朗讀後會設為 false。

#### 3. Startup 與 rejected cancel semantics 仍不完整

`MrtFlowFactory` 的 startup path 直接呼叫 `mode_entry()`，沒有經過
`_current_view_effects()`，因此啟動時仍只朗讀：

```text
"功能選單開啟"
```

沒有朗讀 mode hint、目前項目與位置。

rejected path 現在會 beep + speak current view，但 `FlowPresenter` 沒有先 cancel；
舊 flow 是 beep 後執行 cancel + speak current view。

**必要修正：**

1. presentation data 應只有單一 owner；action 與 engine 不可同時加入相同 view。
2. hint 必須只在進入 state 後第一次呈現，self-transition 不重播。
3. startup 必須使用與一般 state entry 相同的穩定 presentation pipeline。
4. rejected path 必須明確恢復既有 cancel/beep/speak 順序。
5. 加入 exact ordered output assertions，而非只檢查某段文字存在。

### Critical 2：Help 僅修正內容建立，非 `DIRECTION_RUN` 來源仍無法退出

**修正狀態：部分修正**

**位置：**

- `src/apps/access8graph/navigation/actions/common.py:855`
- `src/apps/access8graph/navigation/tables/transfer.py:83`
- `src/apps/access8graph/navigation/validation.py:154`

`240d833` 已改用 fresh snapshot，且 `help_entry()` 改讀
`context.return_state`。從 `DIRECTION_RUN` 開啟 Help 時，現在確實能建立兩個 Help
項目並返回。

但是 table 仍只有：

```text
HELP + QUIT + return_is_direction_run -> DIRECTION_RUN
```

Access8Graph 有 17 個 states 可開啟 Help。從 `STATIONS` 開啟後的實際結果仍是：

```text
OPEN_HELP -> TRANSITIONED, state=HELP, return_state=STATIONS
QUIT      -> REJECTED, state=HELP
```

HELP confirm 也沒有依所有 `return_state + selected command` 提供完整固定 target
rules。completion report 已將此列為 known gap，因此「Critical 2 已修復」的宣稱
不成立。

**必要修正：**

- 為每個可開啟 Help 的來源 state 定義互斥 QUIT／CONFIRM return rules。
- validator 必須驗證每個 Help source 都有完整 return coverage。
- 加入 STATIONS、LINES、direction/undirected selection、route planning、run
  states 的 Help open/confirm/quit tests。

### High 3：完整 golden-trace parity 仍被延後，無法驗證修正沒有新增回歸

**修正狀態：未修正**

**位置：**

- `tests/unit/access8graph_flow_scenarios.py:28`
- `tests/unit/test_access8graph_transition_parity.py:218`
- `tests/integration/test_access8graph_mrt_flow.py:101`

parity test 仍只檢查 final state 與是否 beep，沒有比較：

- ordered speech items
- cancel/speak/beep 順序
- hint 是否只朗讀一次
- view display 是否重複
- navigator mutation
- return/background state
- AUTO intermediate steps

因此本輪新增的「hint 每次重播」與「view 重複兩次」仍可在 `764 passed` 下通過。

completion report 表示完整 golden-trace comparison 因工作量而延後，但這是原始
spec 與 implementation plan 的明確驗收條件，也是 `review_task0` High 4 的必要
修正，不能視為額外工作。

**必要修正：**

- 將每個 scenario 的完整 expected `FlowTrace` 固定下來。
- exact compare output calls、navigator fields、return state 與 final state。
- integration tests 不可只使用 `in` 判斷部分 speech 字串。

### Medium 4：AUTO 上限仍有 off-by-one，恰好 32 次的穩定 chain 仍會失敗

**修正狀態：未修正**

**位置：**

- `src/apps/access8graph/navigation/engine.py:102`
- `tests/unit/test_access8graph_transition_engine.py:415`

修正後在 while loop 開頭先執行：

```python
if steps >= MAX_AUTO_STEPS:
    raise AutomaticTransitionCycleError(...)
```

當第 32 次 AUTO transition 完成後，loop 回到開頭便立即拋錯，尚未先檢查目前 state
是否已沒有 AUTO rule。因此「恰好 32 次後穩定」仍會失敗。

針對性 probe 建立只有 32 次 AUTO transition、之後沒有第 33 條 matching rule 的
chain，結果仍為：

```text
AutomaticTransitionCycleError:
exceeded maximum AUTO steps (32)
```

新測試雖命名為 `test_32_automatic_steps_succeed_33_raises_cycle_error`，但只驗證有
第 33 次嘗試時會拋錯，沒有獨立驗證 32 次後穩定能成功。

**必要修正：**

- 每輪先查詢／評估是否存在下一條 matching AUTO rule；只有準備執行第 33 條時才
  拋錯。
- 拆成兩個測試：32 次後無 matching rule 成功、存在第 33 次 matching rule 失敗。

## 已完成修正

### High 3（前次編號）：標準 pytest collection

已修正。執行：

```bash
pytest tests/unit tests/integration -q
```

結果：`764 passed`。

新增 `tests/__init__.py`、`tests/unit/__init__.py` 並更新 pytest python path 後，無需
額外 `PYTHONPATH=.`。

### Medium 6：Typed flow contract 與 compatibility path

已修正：

- `TransitionNavigationFlow.enter()` 僅接受 `NavigationCommand`
- 回傳 `TransitionResult`
- string command map 已移除
- parity test 在 test boundary 轉譯 legacy strings
- `05a1ecc` 已移除大量 action/guard compatibility re-exports

### Medium 7：Presenter 吞例外

已修正。`FlowPresenter.present()` 不再使用 blanket `except Exception: pass`，
presenter test 也驗證例外會向 app-service boundary 傳遞。

## 逐 Commit 審查

### `240d833` — 2026-06-27 14:39:08 UTC

正確完成：

- 標準 pytest import/path 修正
- target entry 使用 fresh snapshot
- typed flow contract
- presenter exception propagation
- self-transition 不再執行 close/open lifecycle

未完成或新問題：

- Help return rules 未補
- golden-trace parity 未補
- AUTO 32-step boundary 仍錯誤
- same-target presentation 重複 view 並重播 hint
- startup 與 rejected cancel semantics 仍不完整

### `05a1ecc` — 2026-06-27 14:39:49 UTC

移除 compatibility re-export 的方向正確，未發現此 commit 直接新增行為問題。

## 驗證結果

### 完整測試

```bash
pytest tests/unit tests/integration -q
```

結果：`764 passed`。

### 針對性測試

```bash
pytest \
  tests/unit/test_access8graph_flow_presenter.py \
  tests/unit/test_access8graph_transition_engine.py \
  tests/integration/test_access8graph_mrt_flow.py -q
```

結果：`24 passed`。

### 手動 runtime probes

確認結果：

- startup 仍只朗讀「功能選單開啟」
- MODE + DOWN 會重播 hint，且 label/position 各出現兩次
- rejected movement 為 beep + speak，未 cancel
- DIRECTION_RUN Help 已有項目且可退出
- STATIONS Help 有項目，但 QUIT 被 rejected
- 恰好 32 次 AUTO transition 後穩定仍拋
  `AutomaticTransitionCycleError`

## 建議修正順序

1. 先建立完整 ordered golden traces，讓後續修正可被驗證。
2. 統一 presentation effects ownership，修正 startup、self-transition、rejected
   semantics。
3. 完成所有 Help return-state rules 與 validator coverage。
4. 修正 AUTO 32/33 邊界並拆開成功／失敗測試。
5. 重跑標準完整 suite 與 Access8Graph speech smoke test。

## 殘餘風險

- 現有 `764 passed` 無法覆蓋完整 speech/navigator parity。
- 本次未在 Windows/macOS 實機測試 speech backend、wx 或 keyboard hook。
- 在 golden trace 補齊前，仍可能存在其他 output ordering 或 navigator mutation
  回歸。
