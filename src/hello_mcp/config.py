"""集中配置管理"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """应用配置"""

    DASHSCOPE_API_KEY: str
    TMDB_API_KEY: str | None = None
    OPENWEATHER_API_KEY: str | None = None


def load_config() -> Config:
    """加载并校验配置"""
    dashscope_key = os.getenv("DASHSCOPE_API_KEY")
    if not dashscope_key:
        raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")

    return Config(
        DASHSCOPE_API_KEY=dashscope_key,
        TMDB_API_KEY=os.getenv("TMDB_API_KEY"),
        OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY"),
    )
