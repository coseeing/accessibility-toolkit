# Mode 鍵盤事件路由設計

## 目標

將鍵盤事件路由建立為 `accessibility_toolkit.input` 的共用能力。`ModeManager`
負責選擇目前 active mode；每個 mode 則擁有自己的鍵位表與處理函式。

## 核心介面

- `KeyChord` 以一般鍵 `usages` 集合及修飾鍵 `modifiers` 集合表示單鍵或組合鍵。`usages` 可有
  一個或多個 HID usage，例如 `A+B`；`modifiers` 僅包含 Ctrl、Shift、Alt、Meta。
- router 僅在 matching 時將左右側 Ctrl、Shift、Alt、Meta 正規化為相同修飾鍵類別；原始 HID usage
  與 `CapturedKeyEvent.native_context` 不變，會完整交給 fallback，例如 NVDA Remote forwarding。
- `KeyBinding` 將 chord、觸發時機與回傳 `AppKeyEventResult` 的 handler 綁定。
- `KeyTrigger` 支援 `KEY_DOWN`、`KEY_UP` 與 `LONG_PRESS`。
- `KeyEventRouter` 在 mode 建構時接收固定 bindings、可選 fallback，以及可注入的延遲排程器。
  未命中且沒有 fallback 時回傳 `UNHANDLED`；同一 chord 與 trigger 不可重複註冊。

組合鍵不受一般鍵按下順序影響，且必須完全一致：`Ctrl+S` 不會命中 `Ctrl+Shift+S`，`A+B` 也不會
命中 `A+B+C`。修飾鍵可在各平台使用左右側實體鍵，但 binding 無須區分左右側；修飾鍵單獨不作為
binding 的主動作鍵。`usages` 必須至少包含一個一般鍵。

任何可能擴展成已註冊 chord 的部分按鍵集合都採統一 prefix buffering，不論成員是一般鍵或
modifier。router 保存原始 `KeyEvent`／`CapturedKeyEvent` 並立即回傳 `HANDLED_STOP`，不將半套 chord
送給作業系統或 fallback。

例如有 `A+B` binding 時，A down 先保存；後續 B down 形成 chord 就只執行 `A+B` handler。若 A 先
放開而未形成 chord，router 依原始順序將保存的 A down 與 A up 交給 fallback。`Ctrl+A` 亦使用相同
規則：Ctrl down 先保存；形成 `Ctrl+A` 後不送 fallback，未形成則將原始左右 Ctrl down/up replay
給 fallback，因此 NVDA Remote 不會收到孤立的 modifier down。

若 prefix 同時對應較短 key-down binding，例如同時有 `A`、`A+B`、`A+B+C`，A down 與 B down 都
先延後；C down 觸發 `A+B+C`。若在 `A+B` 狀態先放開任一鍵，router 執行延後的 `A+B` handler，
不 replay 給 fallback。因原始 down 已被攔截，prefix resolution 與 fallback replay 都固定回傳
`HANDLED_STOP`；延後同步 handler 的回傳值不再影響 pipeline。沒有較短 binding 且沒有 fallback 時，
保存事件直接丟棄並維持 `HANDLED_STOP`，避免孤立的 key-up 外洩。

## 觸發與長按規則

- key-down 和 key-up binding 分別在對應事件觸發。
- key-down handler 接收使完整 chord 成立的最後一個 key-down `KeyEvent`；key-up handler 接收第一個
  放開成員的 `KeyEvent`；long-press handler 接收當初使 chord 成立的 key-down `KeyEvent`。
- key-down handler 回傳 `HANDLED_STOP` 或 `HANDLED_CONTINUE` 時，router 取得該 chord 的事件所有權，
  後續成員 key-up 不會送 fallback。若有 key-up binding，於第一個成員放開時執行一次，其餘成員
  key-up 仍回傳 `HANDLED_STOP`；若 key-down handler 回傳 `UNHANDLED`，router 不取得所有權。
- chord 若只有 key-up binding，router 從第一個 prefix key-down 起即回傳 `HANDLED_STOP` 並保留事件
  所有權，避免系統或 fallback 收到 down、但本機攔截 up。只有 key-up handler 的回傳值在第一個
  成員放開時作為該次 pipeline 結果，其餘成員放開仍固定回傳 `HANDLED_STOP`。
- 多鍵 key-up binding 在 chord 已完整成立後，任一一般鍵成員首次放開時觸發一次。
- 同一 chord 同時有 key-down 與 long-press binding 時，先延後 key-down。
  到達 long-press 的 `duration_seconds` 且所有一般鍵成員仍按住時只執行 long-press；若提前放開成員，
  則執行延後的 key-down handler。
- long-press 每次按鍵只觸發一次；相關修飾鍵先放開、mode 退出、mode 再次啟用，或 router
  reset 時，會取消尚未到期的 long-press。
- 多鍵 long-press 於最後一個一般鍵按下、完整 chord 成立時開始計時；任一成員放開，或加入額外
  一般鍵造成精確比對失敗時取消。按住造成的重複 key-down 不會重新計時或再次觸發。
- long-press handler 的 `AppKeyEventResult` 回傳值會忽略，因為原始 key-down 已回傳 pipeline 結果；
  router 建立 long-press 排程時固定回傳 `HANDLED_STOP`。
- router 不捕捉 handler 例外。同步 key-down/key-up handler 的例外向 application service 層傳遞；
  非同步 long-press handler 的例外則留在 injected scheduler 的執行環境。預設 scheduler 遵循
  `threading.Timer` 的標準未捕捉例外行為。
- long-press 的 delayed scheduler 可選填。未提供時，core 使用預設 `threading.Timer` scheduler，
  讓非 GUI application 可直接使用長按。
- router 使用同一把 `threading.RLock` 保護按鍵狀態、prefix buffer、binding ownership 與 pending
  long-press，使 timer callback、capture callback、mode reset／退出不會同時修改狀態。handler 允許在
  同一執行緒重入 router lifecycle，因此使用 reentrant lock。
- GUI application 應注入主執行緒 scheduler（例如包裝 `wx.CallLater`），使到期 callback 在可安全
  操作 UI 的執行緒執行。

## ModeManager 與退出行為

`ActivationMode` 提供 `key_router`，不再提供 `handle_key_event` 或 `exit_usage`。active mode
的所有鍵盤事件都直接交由其 router 處理。

退出鍵也是普通 binding：mode 建構時接收 `ModeManager.exit_active_mode` callback，並將 Escape、F11
或任何其他 chord 註冊為 handler。這保留由 `ModeManager` 統一處理 activation、mode lifecycle 與
`ModeChanged` 通知，同時移除退出鍵的特殊鍵盤路由規則。

Router 可接收 `CapturedKeyEvent`，使 fallback 保留 native context。這讓 NVDA Remote 在轉送按鍵時，
仍可使用 Windows 原生 payload；一般 binding handler 則只接收標準 `KeyEvent`。

## App 套用

- Access8Graph 將既有 navigation command 映射改為固定 key-down bindings，Escape binding 呼叫
  `exit_active_mode`；未知鍵仍攔截。
- Key Echo 將 Escape 註冊為退出 binding，其餘按鍵由 fallback echo。
- NVDA Remote 將 F11 註冊為退出 binding，其餘按鍵由 fallback 轉送至遠端；服務層仍抑制 F11
  對應的 key-up，避免退出後的放開事件外洩至系統。

## 驗證

新增單元測試覆蓋單鍵、修飾鍵組合、fallback、key-down/long-press 延後規則與修飾鍵取消長按；
既有 mode lifecycle 與三個 app service 測試則驗證 router 整合後的鍵盤行為與 pipeline 結果維持一致。
