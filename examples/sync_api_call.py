"""同步调用 DashScope API 示例"""

from pprint import pprint

from dashscope import Generation

from hello_mcp.config import load_config, require


def main():
    api_key = require(load_config().dashscope_api_key, "DASHSCOPE_API_KEY")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "system",
            "content": "你是一名资深的 Python 工程师，请使用 Python 演示代码坏味道的各类场景。",
        },
    ]

    response = Generation.call(
        api_key=api_key,
        model="qwen-plus",
        messages=messages,
        result_format="message",
    )

    print("*" * 20)
    pprint(response)


if __name__ == "__main__":
    main()
