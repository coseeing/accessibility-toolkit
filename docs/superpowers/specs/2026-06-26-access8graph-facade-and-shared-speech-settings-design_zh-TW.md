# Access8Graph Facade、Shared Speech Settings 與 Output Manager 退場設計

## 目標

透過四個依序進行的 milestone，完成 `refactor4.md` 已定案的下一階段重構：

1. 將 `Access8GraphAppService` 從 workflow owner 收斂為薄 facade
2. 拆出 Access8Graph 的 command translation 邊界
3. 將 speech settings 從 app service 內部 controller 提升為獨立 shared facade
4. 移除 `application.output.Manager`，將剩餘用途併回更清楚的 runtime 路徑

這是一份單一 spec，包含整體架構終局與四個可分批實作、分批驗證的 milestone。
每個 milestone 都應能單獨 review、單獨驗證，並在確認穩定後再進到下一步。

## 已定決策

這份 spec 以前面的討論結果為前提，不再重新開放以下決策：

- `application.output.Manager` 的方向是退場，不走 compatibility-oriented rename
- Access8Graph 的最終目標是完整收斂成薄 facade，但實作上採 milestone 分批推進
- `SpeechSettingsController` 不維持在各 app service 內部，而是抽成獨立 shared facade
- milestone-first 是主要執行方式；不採一次性大改

## 現況

根據 `docs/refactor/refactor4.md`，目前的 codebase 已經完成：

- bootstrap/runtime extraction
- shared speech runtime settings coordinator
- NVDA Remote typed protocol event 與主要 orchestration 拆分

因此，下一階段的重心已不再是 NVDA Remote，而是下面三個仍未完成的邊界問題：

- `Access8GraphAppService` 仍然同時持有 facade、workflow、lifecycle 與 mode-private 細節
- speech settings 仍以 app-service pass-through surface 的形式散落在各 app 中
- `application.output.Manager` 仍留在 codebase 中，但不再符合 active architecture 的中心角色

## 非目標

這份設計不包含以下工作：

- 重新設計 bootstrap/runtime provider 架構
- 導入通用型 input command framework
- 重做 UI 版面、互動流程或視覺設計
- 修改 speech settings 的持久化 schema 或既有設定 key
- 設計新的 multimodal output bus
- 重寫 NVDA Remote 已完成的 typed event 與 orchestration 拆分

## 目標終局

當四個 milestone 全部完成後，系統應呈現以下形狀：

- `Access8GraphAppService` 僅保留 UI-facing facade 與少量組裝責任
- Access8Graph 的 graph selection、flow lifecycle、navigation session、command translation、
  hotkey startup policy 都有清楚的邊界
- speech settings 成為獨立 shared feature，UI 或 app service 透過清楚命名的 facade 使用
- `application.output.Manager` 從 active design 中消失
- 每個 milestone 都有對應的行為驗證，確保逐步重構不改變外部行為

## 總體策略

這次重構不是先做抽象，再找地方套用；而是先把現有責任密度最高、耦合最直接的區塊
按風險順序拆開。

整體順序如下：

1. 先把 Access8Graph 的 flow lifecycle 與 facade 邊界整理好
2. 再把 Access8Graph 的 translator / command dispatch 邊界獨立出來
3. 等 app service 變薄之後，再把 speech settings 抽成真正共享的 facade
4. 最後移除不再屬於核心路徑的 `application.output.Manager`

這個順序的目的，是避免在 app service 仍然肥大的時候就先改 shared surface，造成兩邊
同時大幅變動。

---

## Milestone 1：Access8Graph Flow Lifecycle 與 Facade 收斂

### 意圖

先處理 Access8Graph 中最重的 workflow / lifecycle 責任，讓
`Access8GraphAppService` 不再直接擁有 flow 建立、銷毀與 navigation session 狀態切換。

### 問題描述

目前 `Access8GraphAppService` 直接持有：

- graphml path 選擇與驗證
- flow 建立與銷毀
- navigation running state
- hotkey 啟動流程中的錯誤回報政策
- mode 進出時的私有方法耦合

同時，`Access8GraphNavigationMode` 仍然直接呼叫 service 的 private methods。
這代表 mode 與 service 的關係不是介面合作，而是內部結構耦合。

### 設計

第一步先不追求把 Access8Graph 一次切完，而是先把 lifecycle 責任抽離：

- `Access8GraphAppService` 保留對 UI 暴露的啟動 / 停止 / 查詢介面
- 實際的 flow 建立、銷毀、navigation lifecycle 交給專責 use case 或 lifecycle object
- graph selection 與檔案驗證也應一併抽到更清楚的邊界，避免 service 既管 UI surface 又管 domain 驗證
- `Access8GraphNavigationMode` 只能依賴穩定公開介面，不可再碰 private service methods

這個 milestone 不要求先抽出 translator；那是下一個 milestone 的工作。

### 建議檔案結構

- Modify: `src/apps/access8graph/service.py`
- Modify: `src/apps/access8graph/flow.py`
- Modify: `src/apps/access8graph/output.py`
- 可能新增：
  - `src/apps/access8graph/use_cases/navigation.py`
  - `src/apps/access8graph/use_cases/graph_selection.py`
  - `src/apps/access8graph/use_cases/__init__.py`

### 邊界規則

`Access8GraphAppService` 應負責：

- 對 UI 提供穩定 facade
- 組裝 navigation lifecycle collaboration
- 轉發 status event 給 UI listener

Navigation lifecycle/use case 應負責：

- 建立 flow
- 銷毀 flow
- 維護目前 navigation 是否 active
- 管理開始與停止時的 side effects

Mode 應負責：

- mode enter / exit 語意
- 把 key event 交給穩定介面

Mode 不應：

- 知道 flow 具體建立方式
- 直接存取 service 私有狀態
- 直接呼叫 service 私有方法

### 風險

- start / stop 時序調整可能改變 speech cancellation 行為
- hotkey 啟動錯誤在搬移時，可能漏掉目前的錯誤語音回報
- graphml 選檔與檔案存在檢查如果拆分不當，可能改變例外型別或拋出時機

### 完成定義

當以下條件都成立時，`M1` 才算完成：

- `Access8GraphNavigationMode` 不再呼叫 private service methods
- flow 建立 / 銷毀不再直接實作在 `Access8GraphAppService`
- graph selection 與 lifecycle 責任已從 service 中明確分離
- UI 端對 `Access8GraphAppService` 的主要呼叫方式維持穩定
- 既有 navigation 啟停、錯誤語音、hotkey 啟動行為保持不變

### 驗證方式

- 單元測試驗證：
  - 選圖、啟動、停止、檔案遺失、錯誤語音
  - mode enter / exit 不再依賴 private methods
- 既有 Access8Graph flow / service / UI 測試持續通過
- 若需要新增測試，應優先加在 service 與 use case 的邊界，而不是只補 integration test

---

## Milestone 2：Access8Graph Command Translation 邊界獨立

### 意圖

把 command translation 與 command dispatch 從 inline mode logic 中抽離，讓
Access8Graph 的按鍵處理邊界與前一個 milestone 的 lifecycle 邊界一致清楚。

### 問題描述

目前 `Access8GraphNavigationMode.handle_key_event()` 內部仍然直接：

- 建立 `Access8GraphKeyTranslator()`
- 把 key event 轉成 command
- 直接將 command 丟給 flow

這讓 mode 同時兼管：

- mode semantics
- translator 組裝
- command dispatch

這種結構讓 translation 規則與 lifecycle 規則難以分開測試，也讓未來若要調整 key handling
policy 時，容易和 mode 狀態改動糾纏在一起。

### 設計

在 `M1` 已整理好的 lifecycle 邊界上，再抽出 command translation 邊界：

- 定義小型 translator / dispatcher collaboration
- mode 僅處理「目前 mode 是否接收這個事件」與「事件該交給哪個合作物件」
- translator 負責把 key event 轉成 app command
- dispatcher 或 navigation collaboration 負責執行 command

這裡不應建立大型 generic framework。只應針對目前 Access8Graph 已經存在的重複結構，
做最小但清楚的界線。

### 建議檔案結構

- Modify: `src/apps/access8graph/input.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: `src/apps/access8graph/flow.py`
- 可能新增：
  - `src/apps/access8graph/use_cases/command_dispatch.py`
  - `src/apps/access8graph/use_cases/navigation_commands.py`

### 邊界規則

Translator 應負責：

- 接收 key event
- 回傳 command 或 `None`

Dispatcher / navigation collaboration 應負責：

- 驗證目前是否有 active flow
- 對 flow 執行 command
- 決定執行失敗時的錯誤上報方式

Mode 應負責：

- 套用 mode-specific 的 handled / unhandled 語意
- 把結果轉換成 app pipeline 可用的結果

### 風險

- unknown key 的處理可能不小心變成 pass-through 或 consume 行為不同
- command execution 出錯時的 error-reporting path 可能改變
- active flow 不存在時的回傳值如果變動，會影響整個 keyboard pipeline

### 完成定義

當以下條件都成立時，`M2` 才算完成：

- translator instantiation 不再寫在 `handle_key_event()` 裡
- mode、translator、dispatcher 的責任分開
- 測試可以分別描述 translation 規則與 mode lifecycle 行為
- handled / unhandled / pass-through 行為與目前一致

### 驗證方式

- 單元測試驗證 translation 規則本身
- 單元測試驗證 mode 對 command / no command / no active flow 的回應
- 回歸現有 Access8Graph keyboard pipeline 相關測試

---

## Milestone 3：Shared Speech Settings 抽成獨立 Facade

### 意圖

將 speech settings 從「每個 app service 內部持有一組 pass-through methods」改成
獨立 shared facade，讓 speech settings 成為真正的共用功能模組，而不是每個 app service
表面的一部分。

### 問題描述

目前各 app service 都暴露一組幾乎相同的方法：

- `get_speech_engine_options()`
- `get_selected_speech_engine()`
- `set_speech_engine()`
- `get_available_voices()`
- `set_selected_voice()`
- `get_rate()` / `set_rate()`
- `get_pitch()` / `set_pitch()`
- `get_volume()` / `set_volume()`

這些方法的真正行為大多只是代理給 `SpeechSettingsController`，導致：

- app service 公開 surface 擴大
- speech settings 被誤視為 app-specific service 職責
- UI controller 對 app service 形成不必要的耦合

### 設計

直接把 speech settings 提升為獨立 shared facade，而不是只做較小的收斂：

- 建立清楚命名的 shared speech settings facade
- facade 包含目前 `SpeechSettingsController` 的行為責任
- UI 或 app 組裝層直接依賴這個 facade
- app service 不再需要暴露整組 speech settings pass-through methods，除非有極少數 app-specific
  協調需求必須保留

這個 facade 仍應能接住：

- speech service adapter
- engine-change callback
- voice-change callback
- numeric-setting-change callback

但不應再以「某個 app service 的一部分」存在。

### 建議檔案結構

- Modify or Rename: `src/apps/shared/speech_settings_controller.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `src/apps/key_echo/service.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: 對應 UI controller / app wiring 呼叫點
- 可能新增：
  - `src/apps/shared/speech_settings_facade.py`

### 邊界規則

Shared speech settings facade 應負責：

- speech engine / voice / numeric settings 的讀寫
- callback 觸發與 shared policy 封裝

App service 應負責：

- 只在必要時協調 speech settings 與 app-domain 行為的互動
- 不再暴露整組 speech settings API 作為自己的主要表面

UI 組裝層應負責：

- 明確注入 speech settings facade 給需要的 UI controller

### 風險

- 現有 UI code 可能直接假設 app service 具有 speech settings methods
- 如果 facade 命名或注入方式不清楚，可能只是把耦合從 service 移到 app wiring
- engine change 時的 status event 行為如果透過 app service 觸發，可能需要明確重新指定責任

### 完成定義

當以下條件都成立時，`M3` 才算完成：

- speech settings 有獨立且清楚命名的 shared facade
- 至少主要 UI controller 已不再直接依賴 app service 的 speech settings pass-through methods
- app services 的公開 surface 明顯縮小
- speech settings 的持久化與行為維持現狀

### 驗證方式

- 單元測試驗證 shared speech settings facade 的 API 與 callback 行為
- UI / app wiring 測試驗證 controller 仍能讀寫 speech settings
- 回歸 `test_speech_settings_controller.py`、`test_app_wx.py`、相關 app service 測試

---

## Milestone 4：移除 `application.output.Manager`

### 意圖

移除一個已不再屬於 active architecture 中心的過渡性抽象，讓 output 路徑回到更直接、
可理解的 runtime collaboration。

### 問題描述

目前 `application.output.Manager` 提供：

- speech route
- cancel
- pause
- tone route
- clipboard push

但目前 active runtime path 主要依賴的是：

- `Capabilities`
- `QueuedService`
- speech runtime services
- direct router callbacks

也就是說，`Manager` 的 generic naming 已經不符合實際地位，繼續保留只會讓維護者誤判
它是否仍是核心設計的一部分。

### 設計

這個 milestone 不做 rename，不做 compatibility repackaging，而是直接退場：

- 找出仍然依賴 `Manager` 的呼叫點
- 把仍有意義的 routing 行為併回更清楚的 runtime path
- 調整測試，使它們驗證真正保留的 collaboration，而不是驗證 `Manager` 這個 wrapper 類別

若某些測試只是在保護歷史遺留 wrapper 的轉發行為，應一併刪除或改寫成驗證新的明確路徑。

### 建議檔案結構

- Delete: `src/application/output/manager.py`
- Modify: `src/application/output/__init__.py`
- Modify: 任何仍 import `Manager` 的檔案
- Modify or Delete: `tests/unit/test_output_manager.py`

### 邊界規則

移除後應遵守：

- protocol/router 直接依賴清楚的 callback collaboration
- clipboard push 應留在真正擁有 transport / clipboard context 的地方
- 不再使用一個 generic manager 類別當作轉接容器

### 風險

- 如果有隱藏 consumer 尚未被測試覆蓋，移除時可能出現遺漏
- `test_output_manager.py` 可能保護了某些仍重要的轉發語意，需要先辨別哪些是 wrapper 噪音、哪些是行為契約

### 完成定義

當以下條件都成立時，`M4` 才算完成：

- `application.output.Manager` 已從 production code 移除
- 沒有 active runtime path 再依賴它
- 剩餘 output collaboration 可由命名更清楚的 runtime path 理解
- 測試已更新成驗證新路徑，而不是驗證舊 wrapper 類別

### 驗證方式

- 搜尋確認 production imports 不再引用 `Manager`
- 回歸 output / message router / app service 相關測試
- 刪除或改寫原本只針對 wrapper forwarding 的測試

---

## 跨 Milestone 驗證策略

每個 milestone 都必須獨立驗證，不能等到全部完成才一起回歸。

原則如下：

1. 每次只動一個主要責任面
   例如 `M1` 不同時改 translator，`M3` 不同時改 output path。

2. 優先補邊界測試，不優先擴大量 integration tests
   這次重構的目的是把責任拆清楚，因此測試也應優先落在新邊界上。

3. 維持 UI-facing 行為穩定
   對使用者可見的 keyboard handling、speech feedback、navigation start / stop、speech settings
   操作，不應在重構中改變。

4. 每完成一個 milestone 就做回歸
   若有既有測試可以覆蓋，就跑最小必要子集；若有新邊界，就為新邊界補最直接的測試。

## 退出條件

當以下條件全部成立時，這份 spec 對應的重構計畫才算結束：

- Access8Graph 已不再由單一 app service 同時掌管 facade、lifecycle、translation 與 mode-private 細節
- speech settings 已成為獨立 shared facade，而不是 app service 的附屬表面
- `application.output.Manager` 已退場
- 四個 milestones 都有對應的測試與驗證結果
- `docs/refactor/refactor4.md` 中對下一階段的主要決策已全數落地

## Summary

這份 spec 將 `refactor4.md` 中較高層的方向，收斂成四個可以逐步落地的 milestone。
它的核心不是建立更多抽象，而是把現有責任邊界整理到能夠穩定演進的狀態：

- 先把 Access8Graph service 變薄
- 再把 command translation 與 lifecycle 分離
- 接著把 speech settings 從 app service 中抽成真正共享的 facade
- 最後移除已失去核心地位的 `application.output.Manager`

如此一來，後續的 app 演進會建立在更清楚的 collaboration 上，而不是建立在歷史殘留的
wrapper 與肥大 facade 之上。
