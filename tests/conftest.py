"""pytest 共享 fixtures"""

import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_env_vars():
    """为所有测试模拟环境变量"""
    with patch.dict(
        os.environ,
        {
            "DASHSCOPE_API_KEY": "test-dashscope-key",
            "TMDB_API_KEY": "test-tmdb-key",
            "OPENWEATHER_API_KEY": "test-weather-key",
        },
    ):
        yield
