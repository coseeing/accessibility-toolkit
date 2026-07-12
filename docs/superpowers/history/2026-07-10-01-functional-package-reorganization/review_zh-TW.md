# Functional Package Reorganization - 主代理審閱

## 審閱範圍

本次審閱由主代理針對下列文件進行：

- `docs/superpowers/finish_task.md`
- `docs/superpowers/specs/2026-07-10-functional-package-reorganization-design.md`
- `docs/superpowers/plans/2026-07-10-functional-package-reorganization-implementation.md`

僅審閱完成報告中列出的八個 commit，並依時間順序檢視。之後也會把最終工作樹當成整體結果再確認一次。當主代理發現 bug 或規格不符時，會交由專門的 sub-agent 修正；主代理會獨立審查修正後的 diff，並重新執行相關驗證。以上流程持續進行，直到沒有阻擋性問題為止。

## Commit 順序與評估

| 順序 | Commit | 規劃任務 | 主代理評估 |
|---:|---|---|---|
| 1 | `b6056a3` - `refactor: move scheduling and events by function` | Task 1 | 乾淨 |
| 2 | `916dadb` - `refactor: consolidate toolkit input package` | Task 2 | 找到並修正了公開的巢狀套件 API 落差 |
| 3 | `96124e5` - `refactor: consolidate toolkit output package` | Task 3 | 乾淨；僅有少量 commit 範圍內的觀察 |
| 4 | `710bc01` - `refactor: move mode lifecycle into interaction` | Task 4 | 乾淨 |
| 5 | `d850a72` - `refactor: consolidate toolkit remote package` | Task 5 | commit 層級的 root API 落差；在目前基線中已修正 |
| 6 | `cbaed7e` - `refactor: complete functional package cutover` | Task 6 | 乾淨 |
| 7 | `60a38f3` - `build: package functional toolkit layout` | Task 7 | 找到並修正了會阻擋釋出的 sdist 缺陷 |
| 8 | `d98ce6a` - `docs: describe functional toolkit packages` | Task 8 | 找到並修正了錯誤的相依與所有權文件內容 |

## 逐 commit 審閱

### 1. `b6056a3` - scheduling 與 events

結果：乾淨。

- `scheduler.py` 和 `application.py` 只是純搬移，行為沒有改變。
- `accessibility_toolkit.scheduling.__all__` 精確匯出 `CancellationToken`、`EventCallbacks`、`ScheduledFuture` 與 `Scheduler`。
- `accessibility_toolkit.events.__all__` 匯出 `AppEvent` 以及六個生命週期事件 dataclass。
- 使用者已經改用新路徑，舊路徑沒有保留轉送匯入。
- `scheduling` 與 `events` 都沒有依賴其他功能套件。

### 2. `916dadb` - input 套件

經過兩輪修正與重審後的結果：乾淨。

這次領域搬移、政策/事件合併、lazy runtime 選擇，以及移除相容性載入的方向都正確。主代理發現 `input.windows` 和 `input.macos` 的 `__all__` 只有宣告模組名稱，卻沒有在套件根層綁定它們支援的平台實作。這不符合設計要求中「兩個巢狀套件都要提供清楚的公開 API」的期待。文件裡的標準匯入 `from accessibility_toolkit.input.windows import WindowsKeyboardHook` 也失敗，因為現有實作類別名稱是 `WindowsKeyboardCapture`。

修正內容：

- 從套件根層匯出既有的 Windows/macOS capture、mapping、event-tap、native-context 與 permissions API。
- 保留 `WindowsKeyboardCapture`，並新增 `WindowsKeyboardHook` 作為同一物件的別名，以符合文件中定義的 API。
- 為兩個巢狀套件補上 package-root 與 `__all__` 合約測試。

TDD 與重審證據：

- 第一次 RED：2 個新的公開套件合約測試失敗；GREEN：22 個測試通過。
- 第二次 RED：`WindowsKeyboardHook` 不存在；GREEN 加上平台/執行階段測試：172 個通過。
- 主代理重新執行功能 API、Windows 與 macOS 測試：當時共 149 個通過。
- 冷程序匯入不會載入 `accessibility_toolkit.runtime`。

### 3. `96124e5` - output 與 speech

結果：乾淨。

- 一般 output、speech、settings、drivers、clipboard，以及內建的 NVDA DLL 都搬移到指定的功能所有權範圍內。
- `QueuedService` 與 speech 行為維持不變；只有匯入層級的變更，沒有改動 enum 值、已保存的 engine ID、settings schema 或 wire model。
- `VENDORED_X64_DLL` 是相對於 `nvda_controller.py` 解析；該 driver 不會匯入 runtime。
- `output` 依賴 `scheduling`，而沒有任何 output 模組依賴 `remote` 或 `runtime`。
- `output` 與 `output.speech` 都有明確的公開 API。

非阻擋性的 commit 範圍觀察：

- 這個 commit 也一併新增了設計/規劃文件，並修改了較早的 refactor 文件。
- macOS 的 PyInstaller hidden-import 轉移是在這個 commit 完成，而不是較後面的 packaging commit。這個變更本身是正確的。

### 4. `710bc01` - interaction modes

結果：乾淨。

- `ModeManager` 與 `ActivationMode` 已搬到 `interaction`，並且具備指定的明確公開 API。
- mode 的進入、離開、capture rollback、exit-key 處理與 `ModeChanged` 通知行為都保留下來。
- 相依方向完全符合 `interaction -> input, events`；各 app 的 mode 仍然保留在 `apps/*` 底下。

### 5. `d850a72` - remote 套件

目前基線中的結果：乾淨。

- 協定訊息、serializer、events、routing、session 與 transport 的搬移都沒有改變 wire format 或生命週期行為。
- `remote.routing`、`remote.session` 與 `remote.transport` 都有明確的公開 API。
- 唯一跨功能的相依是允許的 `remote -> output.speech` wire-model 邊。

commit 層級發現：

- 文件中定義的標準匯入 `from accessibility_toolkit.remote import RemoteSession` 不是由這個 commit 提供的。修正用的 sub-agent 已確認，較晚的目前基線已經在 remote root 匯入並匯出 `RemoteSession`，因此沒有重複實作。當前的匯入、屬性、`__all__` 以及不載入 runtime 的合約都通過。

### 6. `cbaed7e` - hard cutover

結果：乾淨。

- `application`、`application_support`、`interop` 與 `adapters` 套件樹已完全刪除。
- 沒有留下相容模組或轉送匯入。
- runtime 暴露了指定的六個組合符號。
- runtime 的測試檔案已重新命名，並補上公開 API 與刪除合約。
- 最終樹狀結構中，核心套件底下只剩 `input`、`output`、`scheduling`、`interaction`、`events`、`remote` 與 `runtime`。

### 7. `60a38f3` - packaging

修正與重審後的結果：乾淨。

套件發現、DLL 的 package-data key 與 PyInstaller 路徑都正確，但實際驗證揭露了一個原本靜態檢查沒有抓到、而且會阻擋發佈的缺陷：

```text
python -m build packages/accessibility-toolkit-core
...
error in 'egg_base' option: '../../src' does not exist or is not a directory
```

根因：

- 兩個 distribution 專案都用 `package-dir` 與套件發現指向 `../../src`。
- setuptools 可以直接從 repository 建 wheel，但 sdist 不會把外部 source tree 或 DLL 一起打包進去。
- 因此解壓後的 sdist 無法重新建出 wheel。wx distribution 也有相同問題。

修正內容：

- 兩個專案現在都在 distribution metadata 中改用專案內部的 `src` 版型。
- 新增一個小型內建 PEP 517 backend，在從 monorepo 建置時只會把該 distribution 擁有的套件暫時 stage 到臨時專案。
- 每個 sdist 都包含自己的 backend 與自足的 source tree，因此可以獨立重建，不需要 symlink、永久重複 source tree，也不增加新的 runtime 依賴。
- 新增 core 與 wx sdist 的 round-trip 測試、wheel 隔離測試，以及 NVDA DLL 測試。

TDD 與主代理重審證據：

- RED：兩個 packaging 測試都因 `../../src` 的 `egg_base` 錯誤而失敗。
- GREEN：兩個 packaging 測試都通過；把 TOML 變更退回去之後，兩個測試又再次失敗。
- 主代理對兩個專案做的精確 build 都成功，且各自產生一個 sdist 與一個 wheel。
- Core wheel：72 個 core 套件檔案、0 個 wx 檔案、1 個 NVDA DLL。
- wx wheel：9 個 wx 套件檔案、0 個 core 檔案。
- Core sdist 包含 functional core sources、backend 與 DLL；wx sdist 只包含 wx source package 與 backend。
- 建置暫存沒有在工作樹留下 `packages/*/src`、`build`、`dist` 或 egg-info artifact。

### 8. `d98ce6a` - 目前文件

修正與重審後的結果：乾淨。

新的套件樹與使用範例都有出現，但幾個相依敘述與設計及實作不一致：

- 文件聲稱 `input` 目前會消耗 root `events`。
- 文件把 `scheduling` 描述成目前由 input、output 與 runtime 共用，但這次重構中 `input -> scheduling` 明確只是未來可行、目前尚未發生。
- `InputActivationUseCase` 在目前的英文與繁體中文規格中被分配給 `interaction`，而不是 `input`。

修正內容：

- 記錄實際相依邊：`output -> scheduling`、`interaction -> input, events`、`remote -> output.speech`、以及 `runtime -> all functional packages`。
- 釐清 `input -> scheduling` 未來可以允許，但目前並不存在。
- 將 `InputActivationUseCase` 的所有權更正為 `input`。
- 英文與繁體中文文件同步更新。

靜態相依掃描與來源所有權檢查都與修正後的文字一致。

## 審閱／修正輪次

### 第 1 輪

主代理審閱完八個 commit 後，發現：

1. `input.windows` 與 `input.macos` 缺少公開的實作匯出。
2. 文件中定義的 `WindowsKeyboardHook` API 缺失。
3. commit 層級缺少 `remote.RemoteSession` 匯出，但這已經在目前基線中解決。
4. 目前文件中的相依與所有權描述不正確。
5. core 與 wx 的 sdist 無法獨立重建 wheel。

每一個獨立問題都交給專門的 sub-agent 處理。程式碼修正採用先寫會失敗的合約測試，再實作修正的方式。文件修正則以規格/來源對照與靜態相依驗證為基礎。

### 第 2 輪

主代理沒有只看 sub-agent 的完成報告，而是逐一檢查每個 diff。第一個平台 API 修正仍不足以滿足設計文件中明確寫出的 `WindowsKeyboardHook` 使用方式，因此再送回去做第二次 TDD 修正。包裝方案則檢查了可選工具依賴、暫存 artifact 清理、distribution 隔離，以及 round-trip 行為。之後沒有再出現新的阻擋性問題。

## 最終驗證

所有修正完成後，主代理重新做了以下驗證：

```text
.venv/bin/python -m pytest tests/unit tests/integration -q
823 passed in 10.39s
```

核心套件、全部七個功能套件、`WindowsKeyboardHook` 與 `RemoteSession` 的匯入驗證都成功。

靜態邊界檢查：

| 檢查 | 結果 |
|---|---|
| 舊的技術層級目錄 | 不存在 |
| `src` 與 `tests` 內的舊 namespace 匯入 | 0 筆符合 |
| 套件／打包 metadata 中移除的 adapter 參考 | 0 筆符合 |
| `scheduling` / `events` 匯入 feature 套件 | 0 筆符合 |
| feature 套件匯入 `runtime` | 0 筆符合 |
| 非 runtime feature 套件匯入 `remote` | 0 筆符合 |
| `remote -> output.speech` | 剛好 2 個允許的 wire-model 匯入 |
| `git diff --check` | 乾淨 |

精確建置：

```text
.venv/bin/python -m build packages/accessibility-toolkit-core --outdir <tmp>/core
Successfully built accessibility_toolkit_core-0.1.0.tar.gz and accessibility_toolkit_core-0.1.0-py3-none-any.whl

.venv/bin/python -m build packages/accessibility-toolkit-wx --outdir <tmp>/wx
Successfully built accessibility_toolkit_wx-0.1.0.tar.gz and accessibility_toolkit_wx-0.1.0-py3-none-any.whl
```

唯一的建置訊息是 setuptools 的非阻擋性警告：每個 distribution 專案都沒有自己的 README 檔。這不影響 source 收錄、wheel 重建、namespace 隔離或 DLL 收錄。

Windows 與 macOS 的可執行 bundle 在這個 Linux 審閱環境中沒有實際建置。不過已經以靜態方式檢查了它們的 spec 檔與 hidden-import / resource 路徑；平台匯入測試也都通過。

## 最終結論

**修正後通過。**

這次審閱的實作已符合功能套件結構、公開 API、相依方向、hard-cut 移除、文件、套件隔離與內建資源的要求。完整測試套件與兩個 distribution 的 round-trip 驗證都通過，且沒有任何 Critical 或 Important 等級的審閱問題殘留。
