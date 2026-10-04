"""统一 MCP 服务器启动脚本

新增服务器只需两步：在 hello_mcp/servers/ 下建模块（定义 mcp 与 PORT），
再把名字登记到下面的 SERVER_MODULES。端口与说明一律取自模块自身。
"""

import importlib
import sys

SERVER_MODULES = {
    "qwen": "hello_mcp.servers.qwen_agent",
    "tmdb": "hello_mcp.servers.tmdb_server",
    "weather": "hello_mcp.servers.weather_agent",
}


def load_server(name: str):
    """按名字导入服务器模块"""
    module = importlib.import_module(SERVER_MODULES[name])
    if not hasattr(module, "mcp"):
        raise AttributeError(f"模块 {SERVER_MODULES[name]} 未定义 mcp 对象")
    return module


def print_usage():
    """打印使用说明"""
    print("用法：python scripts/run_server.py <服务器名称>")
    print()
    print("可用服务器：")
    for name, module_path in SERVER_MODULES.items():
        module = importlib.import_module(module_path)
        summary = (module.__doc__ or "").strip().splitlines()[0] if module.__doc__ else ""
        print(f"  {name:<8} - {summary} (端口 {module.PORT})")
    print()
    print("示例：")
    print("  python scripts/run_server.py qwen")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    server_name = sys.argv[1].lower()

    if server_name not in SERVER_MODULES:
        print(f"错误：未知的服务器名称 '{server_name}'")
        print()
        print_usage()
        sys.exit(1)

    module = load_server(server_name)
    port = module.PORT

    print(f"启动 {server_name} 服务器 (端口 {port})...")
    module.mcp.run(transport="http", host="127.0.0.1", port=port, path="/mcp")


if __name__ == "__main__":
    main()
