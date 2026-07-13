# Mode Key Router 最終審閱紀錄

日期：2026-07-12  
分支：`feat/mode-key-router`  
審閱依據：

- `docs/superpowers/finish_task.md`
- `docs/superpowers/specs/2026-07-12-mode-key-router-design_zh-TW.md`
- `docs/superpowers/plans/2026-07-12-mode-key-router.md`

## 審閱範圍與方式

依 `finish_task.md` 列出的 commit，由舊至新檢查設計、實作與測試；再以最終累積狀態執行行為重現、測試與靜態差異檢查。`ba38109 docs: clarify completion commit list` 未列在完成文件的審閱清單中，因此依要求不納入逐 commit 審閱。

審閱的 commit 順序如下：

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

## 發現與修正循環

### 第一輪主審

發現下列重要生命週期與規格符合性問題：

- 非延後的單鍵 OS repeat 被吞掉，未依 plan 重複分派 `KEY_DOWN`。
- 延後 chord 在 key-up 才解析時，ownership 仍包含已放開成員，可能留下陳舊 ownership。
- long-press 提前取消時，剩餘 key-up 未被完整擁有，可能洩漏到 fallback；有無 short action 都會發生。
- handler 同步呼叫 `reset()` 後，外層流程可能重新建立已失效的 ownership。
- 較短 chord 的 long-press timer 在較長精確 chord 僅有 `KEY_UP` route 時未正確取消或清除。

修正 commit：

- `e5e671f` — `fix: correct key router lifecycle edge cases`

### 第二輪主審

重新審閱第一輪修正後，另發現 deferred chord 的 `KEY_UP` 時機問題：

- 同時具有 deferred `KEY_DOWN` 與 `KEY_UP` 的 chord，`KEY_UP` 延遲至最後一顆鍵放開才觸發，而規格要求第一次成員放開即觸發。
- 作為較長 chord prefix 的 `KEY_UP`-only chord 可能完全不觸發。
- 被提前取消的 long-press chord 若有 `KEY_UP` route，也需在第一次成員放開時觸發。

修正 commit：

- `7a77c4d` — `fix: fire deferred chord key up on first release`

### 最終主審結果

再次檢查修正差異、ownership/timer/reset 狀態轉移及新增回歸測試後，未發現仍未處理的 Critical 或 Important 問題；目前實作符合上述 spec 與 plan 的已定義行為。

## 驗證結果

- Router 與 ModeManager 聚焦測試：`53 passed in 0.08s`
- Router、ModeManager、兩個 app service 與 Access8Graph 相關目標測試：`137 passed in 0.25s`
- 完整測試：`852 passed, 1 skipped, 14 failed in 2.00s`
- `git diff --check`：通過，無 whitespace error

完整測試中的 14 項失敗均為既有基線問題：缺少被忽略的 fixture `Access8Graph/tests/test.graphml`。依本次範圍決定記錄為基線失敗，不在此功能審閱中修正；未觀察到新增的 router 或 ModeManager 測試失敗。

## 結論

Mode Key Router 可進入整合階段，但仍附帶上述 14 項既有 fixture 基線失敗。原有未追蹤的 `.superpowers/sdd/` 審閱產物保持不變，未納入本次修改。
