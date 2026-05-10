"""天气 MCP 服务器测试"""

from unittest.mock import MagicMock, patch

import pytest

from hello_mcp.servers.weather_agent import (
    compare_cities_weather,
    get_current_weather,
    get_weather_forecast,
)

_get_current_weather = get_current_weather.fn
_get_weather_forecast = get_weather_forecast.fn
_compare_cities_weather = compare_cities_weather.fn


@pytest.fixture
def mock_config():
    """模拟配置"""
    with patch("hello_mcp.servers.weather_agent.load_config") as mock:
        mock.return_value = MagicMock(OPENWEATHER_API_KEY="test-weather-key")
        yield mock


@pytest.fixture
def mock_weather_response():
    """模拟当前天气 API 响应"""
    return {
        "name": "Beijing",
        "sys": {"country": "CN"},
        "main": {
            "temp": 25.5,
            "feels_like": 26.0,
            "humidity": 60,
            "pressure": 1013,
        },
        "weather": [{"description": "晴朗"}],
        "wind": {"speed": 3.5},
    }


@pytest.fixture
def mock_forecast_response():
    """模拟天气预报 API 响应"""
    return {
        "list": [
            {
                "dt_txt": "2024-01-01 12:00:00",
                "main": {"temp": 20.0, "feels_like": 19.5, "humidity": 55},
                "weather": [{"description": "多云"}],
                "wind": {"speed": 2.0},
            }
        ]
    }


def test_get_current_weather_returns_info(mock_config, mock_weather_response):
    """测试获取当前天气返回天气信息"""
    with patch("hello_mcp.servers.weather_agent.http_session.get") as mock_get:
        mock_get.return_value = MagicMock(json=MagicMock(return_value=mock_weather_response))

        result = _get_current_weather("Beijing")

        assert result["city"] == "Beijing"
        assert result["temperature"] == 25.5
        assert result["description"] == "晴朗"


def test_get_weather_forecast_returns_list(mock_config, mock_forecast_response):
    """测试获取天气预报返回列表"""
    with patch("hello_mcp.servers.weather_agent.http_session.get") as mock_get:
        mock_get.return_value = MagicMock(json=MagicMock(return_value=mock_forecast_response))

        result = _get_weather_forecast("Beijing", days=1)

        assert isinstance(result, list)
        assert len(result) >= 1


def test_compare_cities_weather_returns_dict(mock_config, mock_weather_response):
    """测试比较城市天气返回字典"""
    with patch("hello_mcp.servers.weather_agent.http_session.get") as mock_get:
        mock_get.return_value = MagicMock(json=MagicMock(return_value=mock_weather_response))

        result = _compare_cities_weather(["Beijing", "Shanghai"])

        assert "Beijing" in result
        assert "Shanghai" in result


def test_get_current_weather_raises_on_error(mock_config):
    """测试网络错误时抛出异常"""
    with patch("hello_mcp.servers.weather_agent.http_session.get") as mock_get:
        mock_get.side_effect = Exception("Network Error")

        with pytest.raises(RuntimeError, match="获取天气信息失败"):
            _get_current_weather("Beijing")
