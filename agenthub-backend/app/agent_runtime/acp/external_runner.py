from __future__ import annotations

from dataclasses import dataclass

from app.agent_runtime.acp.acp_stdio import ACPStdioAgentClient
from app.agent_runtime.acp.tool_call_protocol import ToolCallSpec, build_tool_result_message, extract_tool_calls


@dataclass
class ACPRunnerConfig:
    provider_type: str
    command: list[str]
    cwd: str


async def run_acp_tool_loop(
    *,
    cfg: ACPRunnerConfig,
    system_prompt: str,
    user_prompt: str,
    tool_executor,
    max_rounds: int = 12,
) -> tuple[str, list[dict]]:
    client = ACPStdioAgentClient(command=cfg.command, cwd=cfg.cwd)
    try:
        await client.start()
        history: list[dict] = []
        prompt = (
            f"{system_prompt}\n\n"
            "你可以请求调用工具，但你不能自己读写文件/执行命令。\n"
            "当你需要工具时，只输出一个JSON对象：\n"
            '{\"tool_calls\":[{\"tool_code\":\"...\",\"args\":{}}]}\n'
            "当你已经完成任务，输出一个JSON对象：\n"
            '{\"tool_calls\":[],\"final\":\"...\"}\n\n'
            f"用户任务：\n{user_prompt}\n"
        )
        final_text: str = ""
        for _ in range(max_rounds):
            await client.prompt_text(prompt)
            model_text = client.collect_text_output()
            calls: list[ToolCallSpec] = extract_tool_calls(model_text)
            if not calls:
                final_text = model_text.strip()
                break
            tool_results: list[str] = []
            for c in calls[:8]:
                try:
                    result = tool_executor(c.tool_code, c.args)
                    tool_results.append(build_tool_result_message(tool_code=c.tool_code, ok=True, result=result))
                    history.append({"tool_code": c.tool_code, "ok": True, "args": c.args, "result": result})
                except Exception as e:
                    tool_results.append(
                        build_tool_result_message(tool_code=c.tool_code, ok=False, result={"error": str(e)[:200]})
                    )
                    history.append({"tool_code": c.tool_code, "ok": False, "args": c.args, "error": str(e)[:200]})
            prompt = (
                "工具执行结果如下（JSON数组）：\n"
                f"{tool_results}\n\n"
                "基于工具结果继续：如果需要更多工具，再输出 tool_calls JSON；否则输出 final。\n"
            )
        updates = [{"kind": u.kind, "text": u.text, "raw_type": u.raw_type} for u in client.updates]
        return final_text or "", updates + [{"kind": "tool.history", "raw_type": "tool.history", "text": "", "history": history}]
    finally:
        await client.close()
