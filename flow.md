# Keyboard Decision Flow

## 現況模型對照

目前 capture / app 邊界的 `KeyEventDecision` 只有兩種：

- `SUPPRESS`
- `PASS_THROUGH`

若把現況硬對映到準備重構的 app-level result，實際上大多接近下面這張表：

| 現況 `KeyEventDecision` | 對系統 | app 內部語意的近似對映 |
|---|---|---|
| `PASS_THROUGH` | 傳給系統 | `UNHANDLED` |
| `SUPPRESS` | 不傳給系統 | `HANDLED_STOP` |

重點：

- 現況幾乎沒有被正式表達的 `HANDLED_CONTINUE`
- 這代表目前模型缺少「app 已處理，但事件仍要往系統送」這種能力

## 新模型語意

規劃中的 app-level result：

- `UNHANDLED`
  - app 沒有處理這個事件
- `HANDLED_CONTINUE`
  - app 已處理這個事件
  - app 內部流程仍可繼續
- `HANDLED_STOP`
  - app 已處理這個事件
  - app 內部流程應在這裡停止

規劃中的最終 capture decision：

- `SUPPRESS`
  - 不送系統
- `PASS_THROUGH_AND_STOP`
  - 送系統
  - app 原路到此為止
- `PASS_THROUGH_AND_CONTINUE`
  - 送系統
  - app 原路功能仍執行

## 關鍵路徑對照

### key_echo

| 情境 | 現況近似 app-level 語意 | 備註 |
|---|---|---|
| echo mode 未啟動，收到一般鍵 | `UNHANDLED` | 直接 pass 給系統 |
| echo mode 啟動，收到一般鍵 | `HANDLED_STOP` | 會朗讀，且不送系統 |
| echo mode 啟動，收到 `Esc` 退出 mode | `HANDLED_STOP` | 已完成退出，不再往下 |
| echo mode 啟動，收到 `Num Lock` | 目標是 `HANDLED_CONTINUE` | 要朗讀，同時也要讓系統切換 Num Lock |

### nvda_remote

| 情境 | 現況近似 app-level 語意 | 備註 |
|---|---|---|
| 未 controlling，收到一般鍵 | `UNHANDLED` | 直接 pass 給系統 |
| controlling，收到一般鍵並成功轉送 | `HANDLED_STOP` | 目前會送遠端，且不送本機系統 |
| controlling，按 `F11` 本機停止控制 | `HANDLED_STOP` | 已完成 stop control，不再往下 |

## 為何要重構

目前系統只有兩種有效組合：

- pass 到系統 + app 不做功能
- 不 pass 到系統 + app 做功能

缺少的第三種是：

- pass 到系統 + app 也做功能

`key_echo` 中的 Windows `Num Lock` 就是第一個明確案例：

- 要 pass 到系統，維持系統 Num Lock 狀態同步
- 也要讓 app 照常執行 echo / speak

因此需要把：

- 「要不要送系統」
- 「app 是否已處理、是否停止」

拆成兩個層次來表達。
