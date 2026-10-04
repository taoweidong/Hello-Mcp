"""天气 MCP 服务器测试"""

import pytest
import requests

from hello_mcp.servers import weather_agent

_get_current_weather = weather_agent.get_current_weather.fn
_get_weather_forecast = weather_agent.get_weather_forecast.fn
_compare_cities_weather = weather_agent.compare_cities_weather.fn


def _weather_payload(city: str) -> dict:
    return {
        "name": city,
        "sys": {"country": "CN"},
        "main": {"temp": 25.5, "feels_like": 26.0, "humidity": 60, "pressure": 1013},
        "weather": [{"description": "晴朗"}],
        "wind": {"speed": 3.5},
    }


def _forecast_payload(dates: list[str]) -> dict:
    return {
        "list": [
            {
                "dt_txt": f"{date} 12:00:00",
                "main": {"temp": 20.0, "feels_like": 19.5, "humidity": 55},
                "weather": [{"description": "多云"}],
                "wind": {"speed": 2.0},
            }
            # 同一天放两个时段，验证按日去重
            for date in dates
            for _ in range(2)
        ]
    }


@pytest.fixture
def stub_weather(monkeypatch, make_response):
    """按城市返回预置 payload；未列出的城市模拟连接失败"""

    def _stub(payloads: dict[str, dict], status: int = 200) -> list[dict]:
        calls: list[dict] = []

        def fake_get(url, params=None, **kwargs):
            calls.append({"url": url, "params": params})
            city = params["q"]
            if city not in payloads:
                raise requests.ConnectionError(f"cannot resolve city: {city}")
            return make_response(payloads[city], status)

        monkeypatch.setattr(weather_agent.http_session, "get", fake_get)
        return calls

    return _stub


def test_get_current_weather_returns_info(stub_weather):
    stub_weather({"Beijing": _weather_payload("Beijing")})

    result = _get_current_weather("Beijing")

    assert result["city"] == "Beijing"
    assert result["temperature"] == 25.5
    assert result["description"] == "晴朗"


def test_get_current_weather_uses_https(stub_weather):
    """回归 P1-3：API key 不得走明文 http"""
    calls = stub_weather({"Beijing": _weather_payload("Beijing")})

    _get_current_weather("Beijing")

    assert calls[0]["url"].startswith("https://api.openweathermap.org/")


def test_get_current_weather_raises_on_http_status_error(stub_weather):
    stub_weather({"Beijing": {"cod": 401, "message": "Invalid API key"}}, status=401)

    with pytest.raises(RuntimeError, match="获取天气信息失败") as excinfo:
        _get_current_weather("Beijing")

    assert isinstance(excinfo.value.__cause__, requests.HTTPError)


def test_get_current_weather_raises_when_key_missing(stub_weather, monkeypatch):
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENWEATHER_API_KEY 环境变量未设置"):
        _get_current_weather("Beijing")


def test_get_weather_forecast_dedupes_by_day(stub_weather):
    stub_weather({"Beijing": _forecast_payload(["2024-01-01", "2024-01-02", "2024-01-03"])})

    result = _get_weather_forecast("Beijing", days=2)

    assert [item["datetime"][:10] for item in result] == ["2024-01-01", "2024-01-02"]


def test_get_weather_forecast_clamps_days(stub_weather):
    stub_weather({"Beijing": _forecast_payload([f"2024-01-0{i}" for i in range(1, 10)])})

    assert len(_get_weather_forecast("Beijing", days=99)) == 7
    assert len(_get_weather_forecast("Beijing", days=0)) == 1


def test_get_weather_forecast_raises_on_http_status_error(stub_weather):
    stub_weather({"Beijing": {"cod": 401, "message": "Invalid API key"}}, status=401)

    with pytest.raises(RuntimeError, match="获取天气预报失败") as excinfo:
        _get_weather_forecast("Beijing")

    assert isinstance(excinfo.value.__cause__, requests.HTTPError)


def test_compare_cities_weather_degrades_per_city(stub_weather):
    """回归 P2-5：单城市失败只记录 error，不影响整体，也不再触发死代码"""
    stub_weather({"Beijing": _weather_payload("Beijing"), "Shanghai": _weather_payload("Shanghai")})

    result = _compare_cities_weather(["Beijing", "Nowhere", "Shanghai"])

    assert result["Beijing"]["temperature"] == 25.5
    assert result["Shanghai"]["city"] == "Shanghai"
    assert "error" in result["Nowhere"]


def test_tools_log_through_context(stub_weather, recording_ctx):
    """三个工具都要把进度与失败写进 MCP Context"""
    beijing = {**_weather_payload("Beijing"), **_forecast_payload(["2024-01-01"])}
    stub_weather({"Beijing": beijing, "Shanghai": _weather_payload("Shanghai")})
    ctx = recording_ctx

    _get_current_weather("Beijing", ctx)
    _get_weather_forecast("Beijing", ctx=ctx)
    _compare_cities_weather(["Beijing", "Nowhere"], ctx)

    assert "成功获取到 Beijing 的天气信息" in ctx.infos
    assert any("正在查询 Beijing 的 5 天天气预报" in msg for msg in ctx.infos)
    assert any("获取 Nowhere 天气失败" in msg for msg in ctx.errors)
    assert "城市天气对比完成" in ctx.infos
