"""配置层测试：密钥解耦与必填校验"""

import pytest

from hello_mcp.config import load_config, require


def test_load_config_never_raises_when_keys_missing(monkeypatch):
    """回归 P1-1：缺失任一密钥都不应在加载阶段抛错"""
    for name in ("DASHSCOPE_API_KEY", "TMDB_API_KEY", "OPENWEATHER_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    config = load_config()

    assert config.dashscope_api_key is None
    assert config.tmdb_api_key is None
    assert config.openweather_api_key is None


def test_load_config_reads_env(monkeypatch):
    """三个密钥各自独立读取"""
    monkeypatch.setenv("TMDB_API_KEY", "only-tmdb")

    config = load_config()

    assert config.tmdb_api_key == "only-tmdb"
    assert config.dashscope_api_key == "test-dashscope-key"


def test_require_returns_configured_value():
    assert require(load_config().tmdb_api_key, "TMDB_API_KEY") == "test-tmdb-key"


@pytest.mark.parametrize("value", [None, ""])
def test_require_raises_with_env_name(value):
    with pytest.raises(ValueError, match="TMDB_API_KEY 环境变量未设置"):
        require(value, "TMDB_API_KEY")
