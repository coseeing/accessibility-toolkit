# 語音引擎設定設計

## 概述

本文件定義如何將語音設定面板，從直接輸入原始整數值的文字欄位，演進為類似 NVDA 的語音引擎設定模型，並以正規化的 `0-100` 滑桿控制語速、語調與音量。

此實作會維持既有 speech command 與 speech sequence 與 NVDA 對齊的方向。每個語音引擎驅動程式自行擁有它支援的設定、目前值，以及從百分比到引擎實際值的對應邏輯。UI 與 application 層只處理正規化百分比與引擎能力，不直接處理引擎專屬的原始數值。

## 目標

- 將語速、語調、音量的文字輸入欄位改為滑桿。
- 在 UI 與 application 對外 API 中，將語音設定值正規化為 `0-100`。
- 讓語音引擎驅動程式負責將正規化百分比轉換為引擎專屬的原始值。
- 將用詞從 `backend` 統一改為 `speech engine`。
- 根據目前啟用的引擎能力，在 UI 中停用不支援的控制項。
- 將選取的語音引擎、語音與正規化數值設定保存，並在下次啟動時還原。
- 讓整體設計盡量貼近 NVDA 的 synth driver 架構。

## 非目標

- 不修改遠端語音協定或 speech command payload 格式。
- 不加入自動偵測引擎或自動 fallback 邏輯。
- 不保留舊 `speech_backend` config key 的相容性。
- 這一輪不新增 macOS 或 Linux 專屬的語音引擎。
- 不重新設計與此無關的連線、relay、鍵盤、剪貼簿或 tone 功能。

## 建議架構

目前啟用的語音引擎仍然是一個實作通用 speech output protocol 的具體驅動程式 class。application 層仍負責把請求路由到目前啟用的引擎，但不再把數值視為引擎專屬的原始整數。

### 分層

#### `adapters`

具體的語音引擎驅動程式仍然是語音行為與設定的唯一真實來源。

職責：

- 播放、取消與暫停語音。
- 在支援時列舉與選取語音。
- 宣告自己支援的語速、語調與音量數值設定。
- 保存自己支援設定的目前正規化百分比值。
- 將正規化百分比值轉換為引擎專屬的原始值。

初期仍維持以下驅動程式：

- `NvdaControllerSpeechOutput`
- `Pyttsx3SpeechOutput`

#### `application`

application 層仍負責管理目前啟用的語音引擎選擇與路由。

職責：

- 保存目前選取的語音引擎 id。
- 建立與替換目前啟用的語音引擎。
- 將 `speak()`、`cancel()`、`pause()`、語音選取與數值設定更新轉發給目前啟用的引擎。
- 保存選取的引擎與各引擎自己的設定。
- 保持不依賴引擎專屬的轉換公式。

#### `ui`

語音設定面板直接反映目前引擎的能力。

職責：

- 顯示語音引擎選擇控制項。
- 顯示語音下拉選單。
- 以正規化百分比顯示語速、語調與音量滑桿。
- 停用不支援的控制項。
- 將目前引擎的數值同步到各控制項。

## 語音引擎模型

### 名詞統一

所有使用者可見與 application 層級的命名，都應改用 `speech engine`，而非 `backend`。

建議改名如下：

- `SpeechBackendOption` -> `SpeechEngineOption`
- `SpeechBackendManager` -> `SpeechEngineManager`
- `get_speech_backend_options()` -> `get_speech_engine_options()`
- `get_selected_speech_backend()` -> `get_selected_speech_engine()`
- `set_speech_backend()` -> `set_speech_engine()`

驅動程式 class 名稱可以維持具體實作導向，但在此設計中，會將它們視為 NVDA synth driver 意義下的語音引擎驅動程式。

### 語音引擎 ID 與標籤

語音引擎的 id 與 UI 顯示標籤固定如下：

- `NvdaControllerSpeechOutput` -> id: `NvdaController`，label: `Nvda Controller`
- `Pyttsx3SpeechOutput` -> id: `Pyttsx3`，label: `Pyttsx3`

`id` 是 application 邏輯與設定保存使用的內部值。

`label` 是顯示在 UI 語音引擎下拉選單中的使用者可見字串。

### 驅動程式自有設定

每個語音引擎驅動程式都必須自行擁有它支援的設定與對應邏輯。

新增一個小型設定模型，概念上類似 NVDA 的 `NumericDriverSetting`，例如：

```python
@dataclass(frozen=True)
class SpeechNumericSetting:
    id: str
    label: str
    default_percent: int = 50
    min_percent: int = 0
    max_percent: int = 100
    step: int = 1
    large_step: int = 10
```

每個驅動程式暴露自己支援的數值設定。最簡單的形式可以是：

```python
def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
    ...
```

本功能的 setting id 為：

- `rate`
- `pitch`
- `volume`

如果某個引擎不支援某項設定，應直接從 supported settings 清單中省略該設定。

### 正規化數值契約

公開的語音數值設定 getter 與 setter，回傳與接受的都應是正規化百分比：

- `get_rate() -> int | None`
- `set_rate(value: int) -> None`
- `get_pitch() -> int | None`
- `set_pitch(value: int) -> None`
- `get_volume() -> int | None`
- `set_volume(value: int) -> None`

這些值一律解讀為 `0-100` 百分比。引擎原始值只存在於具體驅動程式內部，不向外暴露。

### 共用輔助函式

可以加入共用輔助函式，處理一些通用的低階操作，例如：

- `clamp_percent(value: int) -> int`
- `percent_to_range(percent: int, min_value: float, max_value: float) -> float`
- `range_to_percent(raw: float, min_value: float, max_value: float) -> int`

這些 helper 應維持在低階層次。實際採用什麼對應策略，仍由各驅動程式自己決定。

## 執行流程

### 啟動

1. application 載入已設定的語音引擎 id。
2. 語音引擎管理器建立目前啟用的語音引擎驅動程式。
3. application 載入該引擎已保存的語音與數值設定。
4. 已保存的數值一律視為正規化百分比，並傳給目前啟用的引擎。
5. 語音設定視窗同步語音可用性、支援的滑桿、啟用狀態與目前正規化數值。

### 切換語音引擎

1. 使用者在設定視窗中選擇不同的語音引擎。
2. controller 更新 application 層中的目前引擎 id。
3. 目前引擎先執行取消語音。
4. 語音引擎管理器建立新的引擎驅動程式。
5. application 載入該引擎已保存的數值並套用。
6. 設定視窗重新同步各控制項的值與啟用狀態。

### 更新數值設定

1. 使用者移動滑桿。
2. UI 將正規化百分比值送給 controller。
3. controller 轉發給 speech service。
4. speech service 再轉發給目前啟用的引擎。
5. 目前引擎視需要先做 clamp，保存正規化值，轉換為引擎專屬原始值，再套用到執行中的引擎。
6. application 保存目前所選引擎的正規化值。

## UI 設計

### 面板控制項

語音設定視窗維持穩定的控制項排列：

- 語音引擎選擇
- 語音下拉選單
- 語速滑桿
- 語調滑桿
- 音量滑桿

三個數值滑桿一律使用 `0-100` 範圍。若某個支援的設定沒有已保存的值，預設顯示位置為 `50`。

### 不支援的數值設定

不支援的設定要直接反映在 UI 上。

規則：

- 若目前引擎沒有宣告某項數值設定，對應的滑桿就必須停用。
- 被停用的滑桿應顯示中性/預設位置 `50`。
- 被停用的滑桿不得呼叫 `set_rate()`、`set_pitch()` 或 `set_volume()`。
- 在切換引擎後，三個滑桿的啟用與停用狀態都必須重新計算。

### 語音選擇

語音選擇遵循同一套以能力為基礎的模型。

規則：

- 若 `list_voices()` 回傳一個以上的語音，語音下拉選單啟用，並與 `get_voice()` 同步。
- 若 `list_voices()` 回傳空 tuple，語音下拉選單停用。
- 當語音下拉選單停用時，`_on_voice_change()` 不得呼叫 `set_voice()`。

這對 `NvdaControllerSpeechOutput` 特別重要，因為它目前無法提供語音選擇，即使它可能仍透過 SSML prosody 行為支援語速、語調與音量。

## 驅動程式對應策略

### 一般原則

每個驅動程式都自行負責把正規化百分比值轉成引擎原始值。

application 層不應知道這個對應是線性、分段、有限幅、需四捨五入，或是某個引擎專屬公式。

### `Pyttsx3SpeechOutput`

`Pyttsx3SpeechOutput` 內部應將 `rate`、`pitch` 與 `volume` 都視為正規化百分比。

預期行為：

- `rate` 保存正規化百分比，並將其對應為底層引擎的原始語速值。
- `pitch` 保存正規化百分比，並在引擎支援時對應到引擎的 `pitch` property。
- `volume` 保存正規化百分比，並對應到引擎的 `0.0-1.0` 音量範圍。

實際採用的原始值對應公式可以保守、以實作為主，但它應屬於驅動程式本身。

### `NvdaControllerSpeechOutput`

`NvdaControllerSpeechOutput` 雖然底層是透過 SSML 輸出，仍應暴露正規化百分比設定。

預期行為：

- 它會將正規化的 `rate`、`pitch` 與 `volume` 保存為目前本地 baseline。
- 這些正規化值在將 offset-based speech commands 轉為 SSML prosody 百分比時作為基準使用。
- 轉換邏輯保留在驅動程式內。

這樣可以讓它與其他驅動程式共用同一套正規化契約，同時保留它以 SSML 為核心的實作方式。

## 設定保存

設定應保存正規化數值，並使用新的 `speech engine` 命名，不加入任何舊 `speech_backend` key 的相容層。

建議的 config 結構：

- `speech_engine`
- `speech_engines.NvdaController.voice`
- `speech_engines.NvdaController.rate`
- `speech_engines.NvdaController.pitch`
- `speech_engines.NvdaController.volume`
- `speech_engines.Pyttsx3.voice`
- `speech_engines.Pyttsx3.rate`
- `speech_engines.Pyttsx3.pitch`
- `speech_engines.Pyttsx3.volume`

保存規則：

- 語音與數值設定都以 engine id 為單位分開保存。
- 數值只保存正規化百分比。
- 不保存引擎原始值。
- 啟動或切換引擎時，若某個已保存值對應的是不支援的設定，直接忽略。
- 還原數值時先 clamp 到 `0-100`。
- 若已保存的語音已不存在於 `list_voices()` 中，直接忽略並維持引擎預設值。

## 錯誤處理

- 若切換到新的語音引擎失敗，保留目前引擎為啟用狀態，並將 UI 選取復原。
- 若列舉語音失敗且引擎回傳無語音，應讓語音控制項維持停用，而不是呈現損壞的選擇狀態。
- 若引擎不支援某個數值設定，該設定應維持停用，而不是做最佳努力套用。
- 若還原的 config 值超出範圍，套用前先進行 clamp。

## 測試策略

### 單元測試

- 針對 speech engine option 與 manager 命名改動的測試。
- controller 對 speech engine 選擇方法的測試。
- UI 測試，確認語速、語調與音量使用滑桿而非文字欄位。
- UI 測試，確認不支援的滑桿會被停用，且不會呼叫 setter。
- UI 測試，確認當語音清單為空時會停用語音下拉選單。
- 針對所選引擎、各引擎語音與各引擎正規化數值設定的保存測試。
- 針對各引擎自己百分比到原始值對應行為的驅動程式測試。

### 整合測試

- 先以某個引擎啟動並保存設定，重新啟動後確認同一個引擎與正規化數值被正確還原。
- 在不同引擎間切換，確認保存值是以各引擎分開套用，而不是全域共用。
- 確認既有的 incoming speech sequences 仍不需修改，即可路由到目前選取的引擎。

### 手動檢查

- 開啟語音設定視窗，確認三個數值控制項已改為 `0-100` 範圍的滑桿。
- 確認 `NvdaControllerSpeechOutput` 會停用語音選擇。
- 確認某個不支援語調的驅動程式只會停用語調，其他支援的控制項仍保持可用。
- 修改語音與數值後重新啟動應用程式，確認同一個引擎的值會被還原。

## 實作備註

- 語音引擎管理器應保留在 `application`，不要放進 `ui`。
- 引擎專屬的對應邏輯應保留在各驅動程式中。
- 優先採用小型的 `SpeechNumericSetting` 模型，而不是建立過重的抽象階層。
- speech command 與 speech sequence 模型保持不變。
- 不要加入舊 `speech_backend` config key 的相容程式碼。
