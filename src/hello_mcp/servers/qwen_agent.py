"""Qwen AI 聊天 + 代码审查 MCP 服务器"""

from dashscope import Generation
from fastmcp import Context, FastMCP

from hello_mcp.config import load_config, require

mcp = FastMCP("Aliyun Qwen Agent")
PORT = 8000


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

    return response.output.choices[0].message.content


@mcp.tool
def ask_qwen(question: str, ctx: Context | None = None) -> str:
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


@mcp.tool
def code_review(code: str, ctx: Context | None = None) -> str:
    """对代码进行审查并提供改进建议

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
        review_result = _ask_model(api_key, "You are a professional Python code reviewer.", prompt)
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
