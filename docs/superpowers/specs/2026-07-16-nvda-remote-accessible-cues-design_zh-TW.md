# NVDA Remote 無障礙連線提示設計

## 目的

改善 NVDA Remote 用戶端的以下三個相關部分：

- 為連線編輯器的每個欄位提供可視的快速鍵標籤，並與編輯控制項建立關聯。
- 參考 NVDA Remote Access，為連線生命週期變更提供聲音回饋。
- 告知使用者按下 F11 後，鍵盤控制已切換至遠端電腦或本機電腦。

本次實作也會完成 `accessibility-toolkit-core` 中可重複使用的檔案型波形輸出能力，讓應用程式碼不必直接使用平台音效 API。

## 範圍

### 連線編輯器標籤

`ConnectionEditorDialog` 會為 Name、Host、Port 與 Key 建立可視的 `wx.StaticText` 標籤。標籤使用快速鍵文字（`&Name:`、`&Host:`、`&Port:` 與 `&Key:`），並與對應控制項並排配置，符合 remotePlusPlus 的 `addLabeledControl` 慣例。

現有的 `SetName` 值會保留，作為穩定的無障礙名稱。測試會驗證可視標籤與控制項的配對，以及目前的鍵盤預設、驗證和焦點行為。

### 核心波形輸出能力

現有的公開 protocol 維持如下：

```python
class WaveOutput(Protocol):
    def play(self, path: str) -> None: ...
```

`accessibility-toolkit-core` 會新增具體的預設實作，並透過一般 runtime 組合路徑公開：

```text
PlatformProvider.create_wave_output()
    -> AppRuntimeParts.wave_output
    -> OutputServices.capabilities.wave
    -> application use case
```

`Capabilities.wave` 與 `Capabilities.tone` 一樣是可選能力。如此可維持不需要波形播放之應用程式和測試的相容性。

`DefaultWaveOutput.play(path)` 必須是非阻塞的。在 Windows 上使用標準 Windows WAV 播放功能；在 macOS 上於背景啟動 `afplay`。在不支援的平台上，或指定檔案無法播放時，記錄警告並返回，不得拋出例外。提示音效只負責回饋，不得改變連線或控制狀態。

現有的音調產生器仍只負責產生 beep。若有助益，可以共用底層播放實作，但不得改變其公開行為與測試。

### NVDA Remote 提示行為

NVDA Remote 應用程式會封裝以下 NVDA 原始音效檔：

```text
src/apps/nvda_remote/waves/connected.wav
src/apps/nvda_remote/waves/disconnected.wav
```

音效來源為 `ref/nvda/source/waves/`。應用程式的套件設定必須將它們納入建置發行物。音效檔旁必須附上來源與授權聲明，標明 NVDA 為來源，並保留適用於這些複製檔案的 GPL v2（或更新版本）授權資訊。另須將 `ref/nvda/copying.txt` 原文複製為 `NVDA-COPYING.txt` 並封裝在音效檔旁，確保離線發行物也包含具權威性的完整授權條款。由此產生的發行物必須維持 GPL 相容性。

提示對應會固定採用此設計；本次不加入 TeleNVDA 式的偏好設定，亦不提供以產生式 tones 取代 WAV 檔的選項。

| 狀態轉換 | 波形提示 | 語音 |
| --- | --- | --- |
| 工作階段變為已連線 | `connected.wav` | 無 |
| 實際中斷連線後工作階段變為閒置 | `disconnected.wav` | `Disconnected` |
| F11／Start Control 進入遠端控制 | 無 | `Controlling remote computer` |
| F11／Stop Control 返回本機控制 | 無 | `Controlling local computer` |

生命週期和控制 use case 負責決定通知時機。如此無論轉換是由可視按鈕、F11、替換連線或傳輸中斷所啟動，每次實際狀態轉換都只會產生一次提示。UI 只消費狀態，不得重複發出音效或語音回饋。

只有先前狀態與目標狀態不同時才發出生命週期通知：已連線時重複收到 connected 事件、已閒置時重複收到中斷連線事件、控制遠端時重複啟動控制，以及控制本機時重複停止控制，對狀態和提示而言都必須是無操作。

只有先前的連線狀態為 `CONNECTED` 時，才播放中斷連線音效並提供語音提示。連線嘗試失敗而從 `CONNECTING` 返回 `IDLE` 時，仍須執行清理並發布閒置狀態，但因工作階段並未建立，不提供中斷連線提示。

語音使用已設定的本機語音能力。提示 WAV 檔只在本機用戶端播放，不會透過遠端 protocol 傳送給其他端點。

## 元件與責任

| 元件 | 責任 |
| --- | --- |
| `accessibility_toolkit.output.wave` | 定義安全、非同步的本機 WAV 播放器具體實作。 |
| `accessibility_toolkit.output.Capabilities` | 將可選的 `WaveOutput` 與語音、音調能力一併傳遞。 |
| `accessibility_toolkit.runtime.platform` | 延遲建立適合平台的波形播放器。 |
| `accessibility_toolkit.runtime.output` 與 `runtime_parts` | 在 runtime 組合過程中原樣傳遞波形播放器。 |
| `apps.nvda_remote` 提示輔助程式／use case | 解析套件內的提示路徑，並將生命週期／控制轉換對應到波形與語音輸出。 |
| `ui.nvda_remote.connection_editor` | 在編輯控制項旁顯示快速鍵欄位標籤。 |

## 錯誤處理

- 缺少可選的 `wave` 能力時，只略過 WAV 提示；狀態轉換及必要的語音回饋仍須繼續。
- 波形後端發生例外時，由 core 具體實作攔截並以 warning 層級記錄。
- `Capabilities` 已將語音能力列為必要能力；語音輸出回報失敗時，不回滾狀態轉換。
- 重複呼叫 `stop_control()` 或收到重複的中斷連線通知時，維持現有的冪等性，不得增加重複播報。
- 重複的 connected 與啟動控制通知同樣必須維持冪等，不得增加重複的波形或語音輸出。

## 測試與驗收條件

1. 編輯器可視顯示四個快速鍵標籤，且每個標籤都與預期的文字或數值旋鈕控制項配對；驗證及標準對話框鍵盤行為仍通過。
2. 使用預設 provider 建立的 runtime，會透過 runtime parts 和 `Capabilities` 公開同一個波形輸出物件；呼叫端也可以安全地省略它。
3. 預設波形播放會非同步委派給平台後端，播放失敗時轉為警告而非例外。
4. 套件發行物包含兩個 NVDA 提示 WAV 檔、來源聲明，以及位元組完全相同的 `NVDA-COPYING.txt` 授權檔案。
5. 工作階段成功連線時，恰好產生一次 connected WAV 請求。
6. 實際中斷連線時，恰好產生一次 disconnected WAV 請求及一次 `Disconnected` 語音序列。
   `CONNECTING` 失敗後轉為 `IDLE` 時，兩種提示皆不得產生。
7. 進入與離開遠端控制時，分別產生遠端／本機語音提示，無論由可視控制按鈕或 F11 驅動皆相同。
8. 相關的單元測試與完整的 `pytest tests/unit tests/integration -v` 測試套件皆通過。

## 非目標

- 不加入音效與 tones 之間的切換偏好或持久化音效設定。
- 不修改遠端 protocol，也不將本機提示音效轉送給其他端點。
- 不替換現有的遠端語音、音調、剪貼簿或輸入路由行為。
- 不進行與本需求無關的連線管理或 UI 版面重構。
