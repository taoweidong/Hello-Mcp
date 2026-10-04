"""集中配置管理

约定：`load_config()` 只做加载、不做校验，所有密钥可为 None；
每个 server 用 `require()` 声明自己真正必需的密钥，避免无关服务被阻塞。
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """应用配置（未设置的密钥为 None）"""

    dashscope_api_key: str | None = None
    tmdb_api_key: str | None = None
    openweather_api_key: str | None = None


def load_config() -> Config:
    """加载 .env 与环境变量，不校验任何字段

    环境变量优先级高于 .env，因此测试与 CI 可直接设置环境变量覆盖。
    """
    load_dotenv()
    return Config(
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
        tmdb_api_key=os.getenv("TMDB_API_KEY"),
        openweather_api_key=os.getenv("OPENWEATHER_API_KEY"),
    )


def require(value: str | None, env_name: str) -> str:
    """取出某个服务必需的密钥，缺失时给出明确错误"""
    if not value:
        raise ValueError(f"{env_name} 环境变量未设置")
    return value
