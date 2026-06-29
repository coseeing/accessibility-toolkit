# Review Task 0: Application Boundaries and Access8Graph Transition Engine

## 結論

**目前不建議合併。**

Milestone 1 的 package boundary 重構整體合理，但 Access8Graph transition engine
尚未達到 spec 要求的使用者可見行為 parity。最嚴重的問題集中在語音呈現與 Help
流程；目前 121 個所謂 parity scenarios 只檢查 final state 與是否 beep，沒有比較
speech sequence、view、navigator mutation 或中間 AUTO steps，因此無法證明新舊
flow 等價。

## Findings

### Critical 1：狀態切換後沒有朗讀新 view／hint，拒絕操作也未重播目前 view

**引入 commit：** `5c8f84f`

**正式進入 production：** `2f84524`

**舊 flow 移除：** `f07f985`

**位置：**

- `src/apps/access8graph/navigation/engine.py:160`
- `src/apps/access8graph/navigation/actions/common.py:676`
- `src/apps/access8graph/navigation/actions/common.py:690`
- `src/apps/access8graph/navigation/presenter.py:30`
- `tests/unit/test_access8graph_transition_parity.py:213`

entry handlers 會建立 `context.view_model`，但大多回傳空的
`PresentationEffects()`；engine 也沒有在 entry 完成後將 view 的 hint/display
加入 effects。因此切換至新 state 時，presenter 通常只朗讀 close/open message，
完全沒有朗讀新選單內容。

實際結果：

```text
startup:
  cancel
  speak("功能選單開啟")

MODE + CONFIRM -> DIRECTION_LINES:
  cancel
  speak("功能選單關閉")

current view:
  ["", "松山新店線", "", "2 之 1"]
```

使用者進入路線選單後聽不到路線名稱、提示或項目位置。對以語音操作為核心的
Access8Graph，這會直接使導航流程無法可靠使用。

另外，engine 在沒有 matching rule／guard 時建立沒有 view effects 的 rejected
result；presenter 因此只 beep，不會依舊 flow 行為 cancel 並重播目前 view：

```text
MODE + UP at first item:
  beep
```

同 state 的 list movement 也會執行 source exit 與 target entry，導致每次上下移動
都多朗讀「功能選單關閉／開啟」。integration test
`tests/integration/test_access8graph_mrt_flow.py:101` 已把這個新行為當成正確結果，
但舊 flow 在 state 未變時不會執行 lifecycle close/open。

**必要修正：**

1. entry processing 必須將穩定 state 的 hint 與 current view display 加入
   macrostep effects。
2. rejected result 必須取得並朗讀目前 view，保留原本 cancel/beep/speak 語意。
3. source 與 target 相同時，不應執行 state exit/entry lifecycle；應回傳
   `HANDLED`。
4. parity tests 必須比較完整且有順序的 output calls，不只檢查 state/beep。

### Critical 2：Help 從正常 navigation flow 開啟後是空的，而且多數來源無法退出

**引入 commit：** `5c8f84f`

**驗證弱化：** `0a9ce7f`

**位置：**

- `src/apps/access8graph/navigation/engine.py:171`
- `src/apps/access8graph/navigation/actions/common.py:855`
- `src/apps/access8graph/navigation/tables/transfer.py:83`
- `src/apps/access8graph/navigation/validation.py:154`

`A_OPEN_HELP` action 先將 `context.return_state` 設成來源 state，但 engine 呼叫 HELP
entry handler 時仍傳入 transition 前的舊 snapshot。`help_entry()` 只讀
`snapshot.return_state`，因此從正常 navigation state 開啟 Help 時會建立空選單。

實際重現：

```text
DIRECTION_RUN + OPEN_HELP:
  state = HELP
  return_state = DIRECTION_RUN
  help option_count = 0
  help items = ()
```

此外，transition table 有 17 個 state 可以開啟 Help，但 HELP 的 `QUIT` 只定義
回到 `DIRECTION_RUN`。例如從 `STATIONS` 開啟 Help 後：

```text
OPEN_HELP -> transitioned to HELP
QUIT      -> rejected, remains in HELP
```

HELP confirm targets 也只有 MODE、LINES、DIRECTION_STATIONS、
DIRECTION_LINES、DIRECTION_END_POINT，無法完整表達所有 `return_state`。

`0a9ce7f` 將 Help validator 放寬成「只要存在任一 HELP outgoing edge 即可」，使這
種不完整 table 通過驗證，與 spec 要求的 Help/menu 明確 return paths 不符。

**必要修正：**

1. target entry 必須使用 action／state commit 後建立的新 snapshot。
2. HELP 的 QUIT 與 CONFIRM 必須依 immutable snapshot 中的 `return_state` 與
   selected command 定義互斥、固定 target rules。
3. validator／contract tests 必須逐一驗證每個可開啟 Help 的 source state 都有
   return path。
4. 加入由 production path 開啟 Help、瀏覽、confirm、quit 的 end-to-end tests。

### High 3：文件指定的標準完整測試命令在 collection 階段失敗

**引入 commit：** `89090fb`

**仍存在於：** `f07f985`

**位置：**

- `tests/unit/test_access8graph_transition_parity.py:27`

parity test 使用：

```python
from tests.unit.access8graph_flow_scenarios import ...
```

但 repository 的 `tests/` 並不是 Python package，`pyproject.toml` 也只將 `src`
加入 pytest python path。因此 plan 與 repository 指定的命令：

```bash
pytest tests/unit tests/integration -q
```

會在 collection 階段失敗：

```text
ModuleNotFoundError: No module named 'tests'
```

只有額外使用未記錄的：

```bash
PYTHONPATH=.:src pytest tests/unit tests/integration -q
```

才得到報告中的 `764 passed`。這表示 completion report 的驗證環境與 plan／專案
標準命令不一致。

**必要修正：**

- 將 scenario helper 改成 pytest 可直接解析的 import 位置，或正式把 tests
  package 化；不得要求未記錄的額外 `PYTHONPATH=.`。
- 修正後以原始標準命令重新跑完整 suite。

### High 4：所謂 parity suite 沒有驗證 spec 要求的 observable parity

**引入 commit：** `89090fb`

**延續於：** `5c8f84f`、`f07f985`

**位置：**

- `tests/unit/access8graph_flow_scenarios.py:19`
- `tests/unit/test_access8graph_transition_parity.py:213`

`FlowTrace` 雖收集 output calls 與 navigator fields，但 `FlowScenario` 只有
`expected_state`、`expected_success`、`expected_beep`。最終 parity test 只 assert：

1. final state
2. 是否存在 beep

它沒有比較：

- ordered speech items
- cancel/speak/beep call ordering
- hint 與 view display
- navigator mutation
- return/background state
- intermediate AUTO steps

這直接造成前述 Critical findings 在 `121 passed` 下未被發現。舊 flow 移除後，
測試也不再同時執行新舊實作，因此目前檔名中的 parity 已不代表實際 parity。

**必要修正：**

- 在修正 runtime 前，從 `89090fb^` 的 legacy behavior 補回 golden traces 或明確
  expected traces。
- 每個 scenario 比較完整 `FlowTrace`，至少包含 output、navigator、return state
  與 final state。
- 針對 speech ordering 與 AUTO chain 增加獨立 regression tests。

### Medium 5：AUTO 上限有 off-by-one，32 次合法 AUTO transition 也會失敗

**引入 commit：** `39527af`

**位置：**

- `src/apps/access8graph/navigation/engine.py:96`
- `src/apps/access8graph/navigation/engine.py:127`
- `tests/unit/test_access8graph_transition_engine.py:415`

loop 在 `steps < 32` 時執行，但完成第 32 次後立刻因 `steps >= 32` 拋出
`AutomaticTransitionCycleError`。spec 定義的是「最多允許 32 次，33 次才失敗」。

現有測試名稱為 `test_33_automatic_steps_raises_cycle_error`，但 external action 先將
counter 從 0 加到 1，因此實際執行的 AUTO rules 是 index 1 到 32，共 32 次；測試
反而固定了錯誤的 off-by-one 行為。

**必要修正：**

- 32 次 AUTO transition 應成功，準備執行第 33 次時才拋錯。
- 分別加入 32 次成功與 33 次失敗測試。

### Medium 6：typed flow contract 與實作不一致，且仍保留明確 compatibility path

**引入 commit：** `5c8f84f`

**compatibility re-export：** `a4bd539`

**位置：**

- `src/apps/access8graph/use_cases/command_dispatch.py:7`
- `src/apps/access8graph/navigation/flow.py:18`
- `src/apps/access8graph/navigation/flow.py:52`
- `src/apps/access8graph/navigation/actions/__init__.py:46`

`NavigationFlow` protocol 宣告：

```python
enter(NavigationCommand) -> TransitionResult
```

但 `TransitionNavigationFlow.enter()` 接受 `str | NavigationCommand` 並回傳
`bool`。未知字串還會被轉成 `QUIT`，可能造成非預期 state transition。

Milestone 5 又以「backward compatibility」為理由 re-export 所有 action／guard
IDs，與 spec 的「不保留 compatibility adapter／legacy path」決策相反。

**必要修正：**

- production flow 僅接受 `NavigationCommand`，並回傳 `TransitionResult`。
- dispatcher 明確處理 result mapping。
- parity test 自行在 test boundary 將 legacy command 字串轉成 enum。
- 移除 compatibility command map 與全量 re-export。

### Medium 7：presenter 吞掉所有 output exception，繞過既有錯誤停止流程

**引入 commit：** `18cef14`

**位置：**

- `src/apps/access8graph/navigation/presenter.py:18`
- `src/apps/access8graph/service.py:153`

`FlowPresenter.present()` 使用 `except Exception: pass` 吞掉所有錯誤。若
cancel/speak/beep adapter 發生例外，state 已完成 transition，但 app service
無法收到例外，因此不會送出 `ErrorRaised` 或停止 navigation。

這會留下「state 已前進但使用者完全沒聽到輸出」的 silent failure。既有
`Access8GraphAppService.handle_key_event()` 已有統一的 exception boundary，不應在
presenter 內攔截。

**必要修正：**

- presenter 不應捕捉未知例外，讓它傳遞到 app-service boundary。
- 加入 output adapter exception -> `ErrorRaised` -> stop navigation 的整合測試。

## 逐 Commit 審查紀錄

以下依實際 commit 時間由舊到新：

| Commit | 審查結果 |
|---|---|
| `e0d3e65` | Keyboard service relocation 符合 package cohesion，未發現阻擋問題。 |
| `367d450` | Speech settings port/JSON adapter 邊界合理，schema 行為由現有測試覆蓋。 |
| `9cf4568` | Speech protocols 已依角色拆分；未發現行為回歸。 |
| `5ebb562` | Speech aliases 與 shared state 退場符合 spec。 |
| `7b1fa21` | wx shell relocation 為純 ownership 調整，未發現阻擋問題。 |
| `89090fb` | 引入 characterization harness，但標準 pytest import 已失敗，且 baseline assertions 不足以證明 observable parity。 |
| `f7daebe` | Typed model 大致符合 spec。 |
| `784012f` | Snapshot value object 為 frozen；guard contract 方向正確。 |
| `0f524ac` | 初版 table validator 建立主要結構，但後續 Help 驗證被放寬。 |
| `39527af` | Macrostep/ambiguity 基礎成立，但引入 AUTO off-by-one 與 lifecycle snapshot 問題。 |
| `18cef14` | Presenter ordering abstraction合理，但吞例外且 rejected path 不保留舊輸出語意。 |
| `0a9ce7f` | 修正部分 AUTO cycle 檢查，但 Help return validation 放寬過度。 |
| `5c8f84f` | 完成 table/actions，但引入主要 speech、Help、typed contract regressions；parity test 未能攔截。 |
| `2f84524` | 原子切換讓上述問題進入 production path。 |
| `f07f985` | 在 observable parity 尚未成立時移除 legacy implementation 與 legacy characterization execution。 |
| `a4bd539` | 模組分組完成，但仍保留 compatibility re-export，且未修正上述阻擋問題。 |

## 驗證結果

執行：

```bash
pytest tests/unit tests/integration -q
```

結果：collection error，`ModuleNotFoundError: No module named 'tests'`。

執行：

```bash
pytest tests/unit tests/integration \
  --ignore=tests/unit/test_access8graph_transition_parity.py -q
```

結果：`643 passed`。

執行：

```bash
PYTHONPATH=.:src pytest tests/unit tests/integration -q
```

結果：`764 passed`。此命令額外加入 completion report 與 plan 未記錄的
`PYTHONPATH=.`。

另外以 production transition assembly 執行針對性 probe，確認：

- startup 只朗讀「功能選單開啟」
- MODE -> DIRECTION_LINES 只朗讀「功能選單關閉」
- rejected movement 只 beep
- DIRECTION_RUN -> HELP 建立 0 個 help items
- STATIONS -> HELP 後 QUIT 被 rejected 並留在 HELP

## 修正優先順序

1. 先補回完整 legacy observable traces，修正 parity suite 與標準 pytest import。
2. 修正 entry/rejected/self-transition presentation semantics。
3. 修正 Help snapshot 與所有 return-state rules／validation。
4. 修正 AUTO 32/33 邊界。
5. 收斂 typed flow contract、移除 compatibility path。
6. 移除 presenter 的 blanket exception handling。
7. 重新執行標準完整測試命令與 Access8Graph 實際導航 smoke test。

## 殘餘風險

- 本次未在 Windows/macOS 實機執行 wx、keyboard hook 或 speech backend。
- GraphML model/navigator 未重構，符合本階段 non-goals。
- 在修正完整 trace parity 前，其他 navigator mutation 或 speech ordering 回歸仍可能
  被目前測試遺漏。
