# WsRuntime WebSocket 推送包

本包负责把后端消息通过 WebSocket 推送给前端。

## 包内内容
- `manager.py`：WebSocket 连接管理与广播
- `types.py`：前端推送事件类型
- `__init__.py`：统一导出 `ws_manager` 和 `WsEventType`

## 典型用途
- 消息创建时通知前端刷新
- 消息更新时同步前端展示
- 消息被接收时给前端一个确认
- AI 回复失败时向前端推送失败状态
