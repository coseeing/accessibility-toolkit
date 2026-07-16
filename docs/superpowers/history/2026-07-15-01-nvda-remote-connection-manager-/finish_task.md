# NVDA Remote Connection Manager 完成說明

## 完成內容

- 新增具驗證、分組、排序、搜尋與 Quick Connect 的 saved-connection model/catalog/manager。
- 新增 versioned JSON persistence，使用 sibling temporary file 與 `os.replace` atomic save，並保護 malformed configuration。
- 將 saved connection 接入 application service、`CONNECTING` lifecycle 與獨立 runtime config path。
- 新增 accessible connection editor、group manager、searchable connection manager，以及 main frame 的 saved-only workflow。
- 支援 NVDA Remote 相容連結格式、secure seven-digit key generation、English/Traditional Chinese 文件與整合測試。
- 修正 relay reader replacement race：每個 reader generation 擁有自己的 socket/buffer，舊 reader 不會污染新連線。

## Post-completion bugfix

- 修正 wxPython 垂直 `BoxSizer` 誤用 `wx.ALIGN_CENTER_VERTICAL` 導致開啟 Manage Connections 時 assertion 的問題。
- 同步修正 connection editor 與 group manager 的相同 sizer flag 問題，並讓 fake wx 測試模擬真實 wx assertion。
- 回歸驗證：connection UI `19 passed`、app wx `26 passed`、完整測試 `942 passed, 1 skipped`。

## 驗證

- `pytest tests/unit tests/integration -v`: **942 passed, 1 skipped**
- `git diff --check a0929b1 HEAD`: passed
- forbidden-feature scan（排除 connection editor 的合法 Host/Port/Key fields）: clean
- 每個 task 均完成 implementer 與 reviewer gate；最後 whole-branch review：**Ready to merge: Yes**

## 新增 commits

- `2abaeba feat: add saved connection models and links`
- `5105304 feat: add atomic connection catalog store`
- `79e5cd0 feat: add transactional connection manager`
- `56cb3e1 feat: add saved connection app service`
- `975be47 feat: add connection editor and group manager dialogs`
- `fa8983e fix: improve connection dialog accessibility`
- `12564c0 feat: add searchable connection manager dialog`
- `81a3165 fix: harden connection manager context menu`
- `f06d87f fix: test connection manager through wx bindings`
- `6052be1 feat: add saved-only main frame workflow`
- `d7b7efd fix: address main frame review findings`
- `406557d test: document saved connection workflow`
- `77284ec fix: address saved connection review findings`
- `13f69ab fix: address final connection manager review findings`
- `cabedb1 fix: isolate relay reader socket state`

## 備註

工作樹中原有的 spec/plan 與既有 `.superpowers/sdd/task-1-report.md` 變更未被本次實作覆寫或納入上述 commits。
