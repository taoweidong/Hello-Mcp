"""Qwen AI 聊天 + 代码审查 MCP 服务器"""

import asyncio
from typing import Annotated, Any

from dashscope import Generation
from fastmcp import Context, FastMCP
from pydantic import Field

from hello_mcp.config import load_config, require

mcp = FastMCP("Aliyun Qwen Agent")
PORT = 8000

_TOOL_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "openWorldHint": True,
}


def _extract_content(response: Any) -> str:
    """校验 DashScope 响应并取出首个回复内容"""
    status_code = getattr(response, "status_code", 200)
    if status_code != 200:
        code = getattr(response, "code", "") or ""
        message = getattr(response, "message", "") or ""
        raise RuntimeError(f"DashScope 返回错误 {status_code}: {code} {message}".strip())

    output = getattr(response, "output", None)
    choices = getattr(output, "choices", None) if output is not None else None
    if not choices:
        raise RuntimeError("DashScope 未返回有效结果")

    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if not content:
        raise RuntimeError("DashScope 返回空内容")
    return content


def _ask_model(api_key: str, system_prompt: str, user_prompt: str) -> str:
    """调用 Qwen 模型，返回首个回复内容"""
    response = Generation.call(
        api_key=api_key,
        model="qwen-plus",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        result_format="message",
    )

    return _extract_content(response)


@mcp.tool(title="提问 Qwen", annotations=_TOOL_ANNOTATIONS)
def ask_qwen(
    question: Annotated[str, Field(min_length=1, description="用户提出的问题")],
    ctx: Context | None = None,
) -> str:
    """使用阿里云 Qwen 模型回答问题

    Args:
        question: 用户提出的问题

    Returns:
        模型的回答
    """
    api_key = require(load_config().dashscope_api_key, "DASHSCOPE_API_KEY")

    if ctx:
        ctx.info(f"正在向 Qwen 提问: {question}")

    try:
        answer = _ask_model(api_key, "You are a helpful assistant.", question)
    except Exception as e:
        error_msg = f"调用 Qwen 模型失败: {e}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

    if ctx:
        ctx.info(f"Qwen 回答: {answer}")

    return answer


@mcp.tool(title="代码审查", annotations=_TOOL_ANNOTATIONS)
async def code_review(
    code: Annotated[str, Field(min_length=1, description="待审查的代码")],
    ctx: Context | None = None,
) -> str:
    """对代码进行审查并提供改进建议

    该工具使用 async 写法：DashScope 同步 SDK 通过 asyncio.to_thread 桥接，
    避免阻塞 MCP 事件循环，可作为异步工具模板。

    Args:
        code: 待审查的代码

    Returns:
        代码审查结果和建议
    """
    api_key = require(load_config().dashscope_api_key, "DASHSCOPE_API_KEY")

    if ctx:
        ctx.info("正在进行代码审查...")

    prompt = f"""你是一名资深的 Python 工程师，精通软件设计，请对以下代码进行审查：
    1. 指出代码中的坏味道（Code Smells）
    2. 提供具体的优化建议
    3. 给出优化后的代码示例

    代码内容：
    {code}
    """

    try:
        review_result = await asyncio.to_thread(
            _ask_model,
            api_key,
            "You are a professional Python code reviewer.",
            prompt,
        )
    except Exception as e:
        error_msg = f"代码审查失败: {e}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

    if ctx:
        ctx.info("代码审查完成")

    return review_result


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=PORT, path="/mcp")
