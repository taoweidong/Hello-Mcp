"""同步调用 DashScope API 示例"""

from pprint import pprint

from dashscope import Generation

from hello_mcp.config import load_config


def main():
    config = load_config()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "system",
            "content": "你是一名资深的 Python 工程师，请使用 Python 演示代码坏味道的各类场景。",
        },
    ]

    response = Generation.call(
        api_key=config.DASHSCOPE_API_KEY,
        model="qwen-plus",
        messages=messages,
        result_format="message",
    )

    print("*" * 20)
    pprint(response)


if __name__ == "__main__":
    main()
