"""异步调用 DashScope API 示例"""

import asyncio
import platform

from dashscope.aigc.generation import AioGeneration

from hello_mcp.config import load_config, require


async def task(api_key: str, question: str):
    """单个异步任务"""
    print(f"发送问题：{question}")

    response = await AioGeneration.call(
        api_key=api_key,
        model="qwen-plus",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
        result_format="message",
    )

    print(f"模型回复：{response.output.choices[0].message.content}")


async def main():
    """主异步函数"""
    api_key = require(load_config().dashscope_api_key, "DASHSCOPE_API_KEY")

    questions = ["你是谁？", "你会什么？", "天气怎么样？"]
    tasks = [task(api_key, q) for q in questions]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main(), debug=False)
