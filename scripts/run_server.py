"""统一 MCP 服务器启动脚本"""

import sys


def print_usage():
    """打印使用说明"""
    print("用法：python scripts/run_server.py <服务器名称>")
    print()
    print("可用服务器：")
    print("  qwen     - Qwen AI 聊天 + 代码审查 (端口 8000)")
    print("  tmdb     - TMDB 电影信息服务 (端口 8080)")
    print("  weather  - 天气查询服务 (端口 8001)")
    print()
    print("示例：")
    print("  python scripts/run_server.py qwen")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    server_name = sys.argv[1].lower()

    servers = {
        "qwen": "hello_mcp.servers.qwen_agent",
        "tmdb": "hello_mcp.servers.tmdb_server",
        "weather": "hello_mcp.servers.weather_agent",
    }

    if server_name not in servers:
        print(f"错误：未知的服务器名称 '{server_name}'")
        print()
        print_usage()
        sys.exit(1)

    import importlib

    module = importlib.import_module(servers[server_name])

    if hasattr(module, "mcp"):
        port = {"qwen": 8000, "tmdb": 8080, "weather": 8001}[server_name]
        print(f"启动 {server_name} 服务器 (端口 {port})...")
        module.mcp.run(transport="http", host="127.0.0.1", port=port, path="/mcp")


if __name__ == "__main__":
    main()
