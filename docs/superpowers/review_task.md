# Mode Key Router 審閱紀錄

日期：2026-07-13
分支：`feat/mode-key-router`

## 範圍

依 `docs/superpowers/finish_task.md` 的清單，按提交時間由舊到新審閱下列 commit，並以設計規格與實作計畫交叉核對：

1. `255c482` — `feat: add mode key event router`
2. `73d8aec` — `feat: add default long press scheduler`
3. `e4960e9` — `fix: preserve falsey injected scheduler`
4. `0987a67` — `feat: support multi-key chord values`
5. `d6fb193` — `feat: buffer multi-key chord prefixes`
6. `7c358bc` — `fix: address mode key router review findings`
7. `5667c9e` — `feat: own multi-key chord lifecycles`
8. `9b76b86` — `fix: address long-press ownership review findings`
9. `bb5c42f` — `docs: finalize multi-key router design`
10. `d795648` — `test: address task 5 review findings`
11. `e1e3ab0` — `docs: make task 5 placeholder scan self-clean`
12. `f116dea` — `fix: cancel stale long-press timers`
13. `cb9509c` — `docs: record mode-key-router completion`

未列在完成文件的 commit 不納入逐提交審閱；為修正審閱發現而產生的未提交工作樹差異則納入最終狀態複審。

## 審閱結果與修正循環

第一輪檢查既有 lifecycle 修正後，發現含修飾鍵 chord 的 `KEY_UP` 規則未完整符合 spec：`Ctrl+A` 同時有 `KEY_UP` binding 時，Ctrl 先放開會錯誤觸發 handler。規格要求只有第一個一般鍵成員放開才觸發，但修飾鍵 key-up 仍必須被 ownership 攔截而不能外洩至 fallback。

子代理以 TDD 補齊並確認三條路徑的 RED/GREEN 回歸：

- immediate owned chord；
- deferred chord 在 release 時解析；
- pending long-press 提前取消。

第二輪複審發現 long-press 到期後建立的 ownership 未攜帶同 chord 的 `KEY_UP` binding，會使一般鍵 key-up 被攔截卻不呼叫 handler。子代理新增 timer-fire 後 Ctrl 先放開、A 再放開的回歸測試，並將 `KEY_UP` binding 納入 long-press ownership。

主審已重新檢查所有修正差異及其與 spec 的對應；未發現剩餘 Critical 或 Important 問題。

## 驗證

- `pytest tests/unit/test_key_router.py tests/unit/test_mode_manager.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py -q`：`110 passed`
- `pytest tests/unit/test_access8graph_input.py tests/unit/test_access8graph_use_cases.py -q`：`31 passed`
- `pytest tests/unit tests/integration -q`：`856 passed, 1 skipped, 14 failed`
- `git diff --check`：通過，無 whitespace error。
- 規格／計畫 placeholder scan：無匹配；計畫指定的 router types 均存在。

完整測試的 14 項失敗全部因既有且被忽略的 `Access8Graph/tests/test.graphml` 缺失而引發 `FileNotFoundError`，分布在 Access8Graph app-service、GraphML 與 MRT flow 測試；不屬於 mode-key-router 變更。

## 結論

在上述 fixture 基線限制之外，mode-key-router 符合設計規格與實作計畫，可進入整合。審閱修正與回歸測試目前保留為未提交工作樹變更。
