class MessageEventCategory:
    INPUT_OUTPUT = "input_output"
    DAG = "dag"
    EXECUTION = "execution"
    TASK = "task"
    SYSTEM = "system"


class MessageEventStatus:
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class MessageEventType:
    class InputOutput:
        MESSAGE_CREATED = "message.created"
        MESSAGE_UPDATED = "message.updated"
        MESSAGE_ACCEPTED = "message.accepted"
        REPLY_PLACEHOLDER_CREATED = "reply.placeholder.created"
        REPLY_STARTED = "reply.started"
        REPLY_FINISHED = "reply.finished"
        REPLY_FAILED = "reply.failed"

    class Dag:
        DAG_CREATED = "dag.created"
        DAG_UPDATED = "dag.updated"
        DAG_PATCHED = "dag.patched"
        NODE_CREATED = "dag.node.created"
        NODE_UPDATED = "dag.node.updated"
        NODE_DELETED = "dag.node.deleted"
        EDGE_CREATED = "dag.edge.created"
        EDGE_DELETED = "dag.edge.deleted"
        NODE_STATUS_CHANGED = "dag.node.status_changed"
        PLANNING_STARTED = "dag.planning.started"
        PLANNING_FINISHED = "dag.planning.finished"

    class Execution:
        RUN_STARTED = "run.started"
        RUN_FINISHED = "run.finished"
        LLM_REQUEST = "llm.request"
        LLM_RESPONSE = "llm.response"
        THINKING = "thinking"
        TOOL_CALL = "tool.call"
        TOOL_RESULT = "tool.result"
        STREAM_CHUNK = "stream.chunk"
        RETRY = "retry"
        ERROR = "error"

    class Task:
        TASK_CREATED = "task.created"
        TASK_ASSIGNED = "task.assigned"
        TASK_CLAIMED = "task.claimed"
        TASK_COMPLETED = "task.completed"
        TASK_FAILED = "task.failed"
        TASK_REVIEWED = "task.reviewed"
        TASK_REQUEUED = "task.requeued"
        NODE_EXEC_STARTED = "node.exec.started"
        NODE_EXEC_FINISHED = "node.exec.finished"

    class System:
        BOOTSTRAP_STARTED = "bootstrap.started"
        BOOTSTRAP_FINISHED = "bootstrap.finished"
        BOOTSTRAP_FAILED = "bootstrap.failed"
        MEMORY_COMPRESSION_STARTED = "memory.compression.started"
        MEMORY_COMPRESSION_FINISHED = "memory.compression.finished"


ACTIVE_DISPATCH_EVENT_TYPES: set[str] = {
    MessageEventType.InputOutput.MESSAGE_CREATED,
    MessageEventType.InputOutput.REPLY_FINISHED,
    MessageEventType.Dag.DAG_CREATED,
    MessageEventType.Dag.DAG_UPDATED,
    MessageEventType.Dag.DAG_PATCHED,
    MessageEventType.Dag.NODE_STATUS_CHANGED,
    MessageEventType.Task.TASK_ASSIGNED,
    MessageEventType.Task.TASK_CLAIMED,
    MessageEventType.Task.TASK_COMPLETED,
    MessageEventType.Task.TASK_FAILED,
    MessageEventType.Task.TASK_REVIEWED,
    MessageEventType.Task.NODE_EXEC_STARTED,
    MessageEventType.Task.NODE_EXEC_FINISHED,
}


def is_dispatchable_message_event_type(event_type: str) -> bool:
    return str(event_type or "") in ACTIVE_DISPATCH_EVENT_TYPES


def default_message_event_status(event_type: str) -> str:
    return MessageEventStatus.PENDING if is_dispatchable_message_event_type(event_type) else MessageEventStatus.DONE


MESSAGE_EVENT_OPERATION_HINTS: dict[str, str] = {
    MessageEventType.InputOutput.MESSAGE_CREATED: "落库消息并触发 dispatcher 进行路由",
    MessageEventType.InputOutput.MESSAGE_UPDATED: "更新消息展示内容",
    MessageEventType.InputOutput.MESSAGE_ACCEPTED: "通知前端消息已接收",
    MessageEventType.InputOutput.REPLY_PLACEHOLDER_CREATED: "创建等待中的 AI 回复占位消息",
    MessageEventType.InputOutput.REPLY_STARTED: "标记 AI 回复开始",
    MessageEventType.InputOutput.REPLY_FINISHED: "写回最终 AI 回复",
    MessageEventType.InputOutput.REPLY_FAILED: "写回 AI 回复失败状态",
    MessageEventType.Dag.DAG_CREATED: "创建任务图",
    MessageEventType.Dag.DAG_UPDATED: "更新任务图",
    MessageEventType.Dag.DAG_PATCHED: "局部修补任务图",
    MessageEventType.Dag.NODE_CREATED: "新增 DAG 节点",
    MessageEventType.Dag.NODE_UPDATED: "编辑 DAG 节点",
    MessageEventType.Dag.NODE_DELETED: "删除 DAG 节点",
    MessageEventType.Dag.EDGE_CREATED: "新增 DAG 边",
    MessageEventType.Dag.EDGE_DELETED: "删除 DAG 边",
    MessageEventType.Dag.NODE_STATUS_CHANGED: "修改节点状态",
    MessageEventType.Dag.PLANNING_STARTED: "开始生成规划图",
    MessageEventType.Dag.PLANNING_FINISHED: "完成规划图生成",
    MessageEventType.Execution.RUN_STARTED: "开始一次 AI 执行",
    MessageEventType.Execution.RUN_FINISHED: "结束一次 AI 执行",
    MessageEventType.Execution.LLM_REQUEST: "记录一次模型请求",
    MessageEventType.Execution.LLM_RESPONSE: "记录一次模型响应",
    MessageEventType.Execution.THINKING: "记录推理/思考过程",
    MessageEventType.Execution.TOOL_CALL: "记录一次工具调用",
    MessageEventType.Execution.TOOL_RESULT: "记录一次工具返回",
    MessageEventType.Execution.STREAM_CHUNK: "记录流式输出片段",
    MessageEventType.Execution.RETRY: "记录一次重试",
    MessageEventType.Execution.ERROR: "记录异常",
    MessageEventType.Task.TASK_CREATED: "创建任务",
    MessageEventType.Task.TASK_ASSIGNED: "分配任务给 agent",
    MessageEventType.Task.TASK_CLAIMED: "agent 认领任务",
    MessageEventType.Task.TASK_COMPLETED: "子 agent 写入完成事件并触发管家复核",
    MessageEventType.Task.TASK_FAILED: "子 agent 写入失败事件并触发管家复核",
    MessageEventType.Task.TASK_REVIEWED: "管家复核完成并收口节点状态",
    MessageEventType.Task.TASK_REQUEUED: "任务重新入队",
    MessageEventType.Task.NODE_EXEC_STARTED: "请求执行节点并触发解析器调度",
    MessageEventType.Task.NODE_EXEC_FINISHED: "节点执行结束（兼容事件）",
    MessageEventType.System.BOOTSTRAP_STARTED: "开始 bootstrap 初始化",
    MessageEventType.System.BOOTSTRAP_FINISHED: "完成 bootstrap 初始化",
    MessageEventType.System.BOOTSTRAP_FAILED: "bootstrap 初始化失败",
    MessageEventType.System.MEMORY_COMPRESSION_STARTED: "开始记忆压缩",
    MessageEventType.System.MEMORY_COMPRESSION_FINISHED: "完成记忆压缩",
}


def describe_message_event_operation(event_type: str) -> str:
    return MESSAGE_EVENT_OPERATION_HINTS.get(str(event_type), "")
