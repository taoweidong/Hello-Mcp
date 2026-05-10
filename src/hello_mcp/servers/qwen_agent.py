"""Qwen AI 聊天 + 代码审查 MCP 服务器"""

from dashscope import Generation
from fastmcp import Context, FastMCP

from hello_mcp.config import load_config

mcp = FastMCP("Aliyun Qwen Agent")


@mcp.tool
def ask_qwen(question: str, ctx: Context = None) -> str:
    """使用阿里云 Qwen 模型回答问题

    Args:
        question: 用户提出的问题

    Returns:
        模型的回答
    """
    if ctx:
        ctx.info(f"正在向 Qwen 提问: {question}")

    config = load_config()

    try:
        response = Generation.call(
            api_key=config.DASHSCOPE_API_KEY,
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ],
            result_format="message",
        )

        answer = response.output.choices[0].message.content

        if ctx:
            ctx.info(f"Qwen 回答: {answer}")

        return answer

    except Exception as e:
        error_msg = f"调用 Qwen 模型失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool
def code_review(code: str, ctx: Context = None) -> str:
    """对代码进行审查并提供改进建议

    Args:
        code: 待审查的代码

    Returns:
        代码审查结果和建议
    """
    if ctx:
        ctx.info("正在进行代码审查...")

    config = load_config()

    prompt = f"""你是一名资深的 Python 工程师，精通软件设计，请对以下代码进行审查：
    1. 指出代码中的坏味道（Code Smells）
    2. 提供具体的优化建议
    3. 给出优化后的代码示例

    代码内容：
    {code}
    """

    try:
        response = Generation.call(
            api_key=config.DASHSCOPE_API_KEY,
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "You are a professional Python code reviewer."},
                {"role": "user", "content": prompt},
            ],
            result_format="message",
        )

        review_result = response.output.choices[0].message.content

        if ctx:
            ctx.info("代码审查完成")

        return review_result

    except Exception as e:
        error_msg = f"代码审查失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")
