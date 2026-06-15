# Access8Graph GUI MRT 移轉設計

## 1. 背景

Access8Graph 是一個 NVDA 附加元件，用來導覽可訪問的結構圖，特別是以 yEd GraphML 製作的 MRT 路網圖。它目前的實作仰賴 NVDA 執行階段 API 來處理鍵盤攔截、焦點物件、語音、提示音與檢閱文字。相較之下，解析器、MRT 模型與導覽器的獨立性較高，只要稍作調整，就能在不依賴 NVDA 的環境中重用。

原始 Access8Graph source tree 目前已放在此 repository 的 `Access8Graph/`；實作時應使用這個根目錄下的 source tree 作為移轉來源與 fixture 位置。

這個專案已經提供了這次移轉所需的共通架構：

- 透過 `KeyboardInputService`、`InputCapture` 與 `HotkeyCapture` 擷取鍵盤輸入。
- 透過 `AppKeyEventResult` 與 `KeyboardPipelineResult` 處理應用程式層級的按鍵結果。
- 透過 `OutputCapabilities.speech` 輸出語音。
- 透過 `key_echo` 使用的 wxPython 系統匣工具殼層，包含主面板、語音設定與離開動作。

第一階段的移轉目標，是做成一個和 `key_echo` 類似的 GUI MVP：主面板選取 `.graphml` 檔案，然後開始或停止圖形導覽。語音設定與系統匣行為則沿用共用實作。

## 2. 目標

- 新增 `apps.access8graph` 應用程式與 `ui.access8graph` GUI。
- 重用既有的 `ToolAppShell`、系統匣圖示與 `SpeechSettingsFrame`。
- 主面板只支援選取 `.graphml` 檔案。
- 使用本專案的鍵盤擷取與語音輸出來啟動選定檔案的 MRT 圖形導覽。
- 保留現有 Access8Graph MRT flow 行為，包含模式選擇、車站/路線列表、方向探索、線性探索、路線規劃、轉乘選單與說明選單。
- 讓移轉後的 GraphML 解析器、MRT 模型與導覽器都能在不匯入 NVDA 的情況下進行測試。

## 3. 非目標

- 不移植 `directedGraphView.py` 或較早的通用 directed graph prototype。
- 不實作 Windows 檔案總管的選檔整合，也不實作原本的 `NVDA+alt+g` 附加元件入口。
- 第一階段不實作 NVDA 檢閱文字或 NVDA 焦點物件行為。
- 不加入 GraphML 作者工具驗證或 schema 強制檢查。
- 不重新設計 Access8Graph 的 MRT 互動模型。

## 4. 使用者體驗

Access8Graph 會以工具形式從系統匣啟動，和 `key_echo` 相同。

系統匣選單：

- `Main`：開啟 Access8Graph 主面板。
- `Speech Settings`：開啟共用的語音設定面板。
- `Exit`：停止輸入擷取、語音輸出並關閉 wx 應用程式。

主面板：

- `Choose GraphML...`：開啟只過濾 `.graphml` 的檔案選擇器。
- 狀態文字：
  - 尚未選檔時顯示 `No file selected`。
  - 選檔後顯示已選檔名。
  - 導覽啟動後顯示 `Navigation running`。
  - 載入或啟動失敗時顯示簡短錯誤訊息。
- `Start Navigation` / `Stop Navigation`：
  - 在尚未選取 `.graphml` 檔案前停用。
  - 對選定的圖形啟動導覽。
  - 當鍵盤擷取啟用時，按鈕文字切換為 `Stop Navigation`。

導覽啟動後，應用程式會朗讀 MRT 模式選單。接著使用者可以沿用既有 MRT flow 按鍵來操作圖形，包括方向鍵、Enter、`q`、`h`、`m`、`v`、`d`、`u`、`p`、`s`、`l` 與 `e`。Escape 會結束導覽並讓應用程式回到閒置狀態。

## 5. 架構

### 模組

`apps.access8graph.main`

- 以和 `apps.key_echo.main` 相同的方式建立執行環境依賴。
- 建立輸入擷取、熱鍵擷取、語音排程器、語音服務、輸出服務、應用程式服務與 wx app。
- 使用共用的語音後端預設值。

`apps.access8graph.service`

- 持有已選檔案路徑與導覽執行狀態。
- 提供 UI 會用到的方法：
  - `choose_graphml(path: str)`。
  - `start_navigation()`。
  - `stop_navigation()`。
  - `is_navigation_running()`。
  - 與 `key_echo` 對應的語音設定代理方法。
- 實作 `handle_key_event(CapturedKeyEvent) -> KeyboardPipelineResult`。
- 導覽執行時啟用鍵盤擷取，停止時回復閒置狀態。

`apps.access8graph.graphml`

- 包含移轉後的 Access8Graph GraphML 解析器、MRT 模型與 MRT 導覽器。
- 不得匯入 NVDA 模組。
- 盡量維持與原始 Access8Graph 檔案接近的行為，以降低移轉風險。

`apps.access8graph.flow`

- 包含從 `mrtView.py` 移轉而來的 MRT flow 與狀態機。
- 保留 `State`、`ListState`、`HelpState`、`ListView` 與 `RunView`。
- 以明確注入的 adapter 取代 NVDA 的 `Window`、`speech`、`tones`、`textInfos`、焦點與記錄相依性。

`apps.access8graph.input`

- 將本專案的 `KeyEvent` 值轉換成 MRT flow 命令鍵。
- 只追蹤 key-down 事件來觸發命令，和原本 Access8Graph 的行為一致。
- key-up 事件僅在啟用中用於 pipeline suppression，不作為命令處理。

`ui.access8graph.app`

- 模式與 `ui.echo.app` 相同。
- 使用 `Access8GraphMainFrame` 與共用的 `SpeechSettingsFrame` 建立 `ToolAppShell`.

`ui.access8graph.main_frame`

- 提供檔案選擇器、狀態文字與開始/停止按鈕。
- 依 controller 的狀態通知更新 UI。

### 資料流

1. 使用者從系統匣開啟主面板。
2. 使用者按下 `Choose GraphML...` 並選取 `.graphml` 檔案。
3. UI 呼叫 `controller.choose_graphml(path)`。
4. 使用者按下 `Start Navigation`。
5. controller 載入：
   - `Graph(path=path)`。
   - `MrtModel(Graph)`。
   - `MrtDirectionNavigator(MrtModel)`。
   - `MrtUndirectionNavigator(MrtModel)`。
   - `MrtFlow({"direction": ..., "undirection": ...}, output=...)`。
6. controller 透過既有的啟用模式進入鍵盤擷取。
7. 擷取到的按鍵事件會轉換成 flow 命令。
8. `MrtFlow.enter(command)` 更新狀態並輸出語音或失敗提示音。
9. Escape 或 Stop 按鈕會退出導覽並回到閒置狀態。

## 6. Flow 調整

原始 Access8Graph 的 `MrtFlow` 會做三件 NVDA 專屬工作：

- 透過 `Window`、`event_gainFocus` 與 `event_loseFocus` 管理焦點生命週期。
- 透過 NVDA `speech` 與 `tones` 輸出語音與提示音。
- 透過 `GraphViewTextInfo` 提供檢閱文字。

移轉後會保留 flow 的狀態機，但移除這些責任。

新的 flow 責任：

- 持有導覽器與狀態物件。
- 接收包含 `key`、`repeat` 與 `pressing` 的命令 dict。
- 接收由 `Access8GraphKeyTranslator` 產生的命令鍵；translator 負責把 HID 事件映射成 `up`、`down`、`left`、`right`、`enter` 與 MRT 字母命令。
- 將 `enter` 視為 `onok()`。
- 透過注入的 callback 輸出：
  - `cancel_speech()`。
  - `speak(items: tuple[str, ...])`。
  - `beep_failure()`。
- 回傳該命令是否已被處理。

檢閱文字不會出現在第一階段執行期。如果日後需要，可以把目前 `state.view.label` 直接暴露成一般屬性，供未來的檢閱文字 adapter 使用。

## 7. 輸入對應

`Access8GraphKeyTranslator` 會把 HID 鍵盤事件映射成命令名稱。

第一階段支援的映射如下：

- `HID.UP` -> `up`
- `HID.DOWN` -> `down`
- `HID.LEFT` -> `left`
- `HID.RIGHT` -> `right`
- `HID.ENTER` 與 `HID.KEYPAD_ENTER` -> `enter`
- `HID.ESCAPE` -> `escape`
- MRT flow 會用到的字母鍵：
  - `D` -> `d`
  - `U` -> `u`
  - `P` -> `p`
  - `Q` -> `q`
  - `H` -> `h`
  - `M` -> `m`
  - `V` -> `v`
  - `S` -> `s`
  - `L` -> `l`
  - `E` -> `e`
- `HID.HOME` -> `home`
- `HID.END` -> `end`

對於不支援的按鍵，translator 不會產生命令。當導覽處於啟用中時，不支援的按鍵仍會被視為已處理並抑制，因為原本 Access8Graph 的 hook 會在互動視窗內吞掉大部分按鍵。

Escape 會由 service 在送往 flow 前先處理。它會停止導覽並回傳 `HANDLED_STOP`。

## 8. 輸出行為

`Access8GraphFlowOutput` 會把 flow 輸出適配到 `OutputCapabilities`。

語音：

- `cancel_speech()` 會呼叫 `outputs.speech.cancel()`。
- `speak(items)` 會把字串包成 `SpeechSequence`。
- 送出前會移除空字串。
- 非空語音項目之間會插入 `interop.speech.speech_commands` 的 `BreakCommand(time=1)`，對齊原始 NVDA flow 的語音節奏意圖。

提示音：

- 如果 `outputs.tone` 存在，失敗提示音就使用該 tone 輸出。
- 如果 `outputs.tone` 不存在，失敗提示音就視為 no-op。
- no-op 的提示音不應造成命令處理失敗。

原始 NVDA flow 會在語音項目之間插入 `BreakCommand(1)`。本專案已經有等價的命令型別，因此移轉時應在建立 `SpeechSequence` 時使用 `interop.speech.speech_commands.BreakCommand(time=1)`。

## 9. 錯誤處理

檔案選擇：

- 檔案選擇器只過濾 `.graphml`。
- controller 只有在路徑存在且副檔名為 `.graphml` 時才會儲存選定路徑。

啟動導覽：

- 如果沒有選檔，controller 會丟出清楚的驗證錯誤，並讓應用程式維持閒置。
- 如果解析器或模型建立失敗，controller 會把例外訊息回報給 UI，且不會啟用鍵盤擷取。
- 如果鍵盤擷取啟用失敗，controller 會回復到閒置狀態，並回報啟用錯誤。

導覽進行中：

- 未知命令會被視為已處理，但不會改變狀態。
- 狀態方法回傳 false 時會觸發失敗提示音。
- flow 錯誤會在 service 邊界被捕捉，透過狀態通知回報，並停止導覽，以免把所有鍵盤輸入都困在壞掉的狀態裡。

關閉時：

- 如果導覽啟用中就先停止導覽。
- 如果輸入或熱鍵擷取正在執行，就先停止它們。
- 關閉語音輸出。

## 10. 測試策略

單元測試：

- `Access8GraphKeyTranslator` 正確映射方向鍵、Enter、Escape、Home/End 與 MRT 字母鍵。
- 不支援的按鍵不會產生命令。
- flow 輸出 adapter 會依序呼叫 cancel 與 speak。
- flow 啟動時會在不依賴 NVDA 的情況下朗讀模式選單。
- 沒有選檔時 service 不能啟動。
- 解析/模型失敗時 service 會回報錯誤，但不會啟用鍵盤擷取。
- 導覽啟用時 service 會回傳 `KeyboardPipelineResult(send_to_system=False, app_result=HANDLED_STOP)`。
- Escape 會停止導覽。

整合測試：

- 載入一個小型且既有的 Access8Graph `.graphml` fixture。
- 建立 `Graph -> MrtModel -> MrtDirectionNavigator/MrtUndirectionNavigator -> MrtFlow`。
- 驗證會先輸出模式選單語音。
- 以假的輸出元件驅動一小段序列，例如 Down、Enter，或方向模式選擇。

UI 測試：

- 主面板初始時 `Start Navigation` 為停用狀態。
- 選取 `.graphml` 路徑後會更新狀態並啟用開始按鈕。
- 開始/停止按鈕的文字會隨 controller 狀態通知而改變。
- 關閉視窗時會隱藏而不是退出，行為比照 `key_echo`。

手動驗證：

- 執行 `PYTHONPATH=src python -m apps.access8graph.main`。
- 選取一個已知的 `.graphml` 檔案。
- 啟動導覽。
- 確認語音會朗讀模式選單。
- 使用方向鍵與 Enter 導覽列表。
- 使用 Escape 或 Stop Navigation 回到閒置狀態。
- 從系統匣開啟語音設定，確認後端控制仍可正常使用。

## 11. 推進順序

實作應該分小步進行：

1. 複製並去 NVDA 化 GraphML parser/model/navigator 模組。
2. 抽出並調整 MRT flow 的輸出/失敗行為。
3. 新增 key translator 與 service 測試。
4. 新增 Access8Graph 應用程式執行環境與 GUI。
5. 串接系統匣與共用語音設定。
6. 先跑針對性的單元測試，再跑完整測試套件。

這樣可以讓純 parser/model 的工作和 GUI、鍵盤擷取整合彼此分離。

## 12. 已確認決策

- 第一階段的檔案選擇器只支援 `.graphml`。
- 第一階段採 GUI 方式，不做 CLI-only。
- 第一階段只移轉 MRT flow，不包含通用 directed graph 導覽。
- 第一階段執行期不實作 NVDA 檢閱文字，也不實作檔案總管選檔整合。
