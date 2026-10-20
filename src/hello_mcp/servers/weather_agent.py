"""天气查询 MCP 服务器"""

from typing import Annotated

from fastmcp import Context, FastMCP
from pydantic import Field
from typing_extensions import TypedDict

from hello_mcp.config import load_config, require
from hello_mcp.utils.http_client import create_session

mcp = FastMCP("Weather Agent")
PORT = 8001

http_session = create_session()

_BASE_URL = "https://api.openweathermap.org/data/2.5"
_MAX_FORECAST_DAYS = 5

_TOOL_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "openWorldHint": True,
}


class WeatherInfo(TypedDict):
    city: str
    country: str
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    description: str
    wind_speed: float


class ForecastItem(TypedDict):
    datetime: str
    temperature: float
    feels_like: float
    humidity: int
    description: str
    wind_speed: float


class WeatherError(TypedDict):
    error: str


CityWeather = WeatherInfo | WeatherError


def _fetch_current_weather(city: str, api_key: str) -> WeatherInfo:
    """拉取单个城市的当前天气（供工具与城市对比复用）"""
    response = http_session.get(
        f"{_BASE_URL}/weather",
        params={"q": city, "appid": api_key, "units": "metric", "lang": "zh_cn"},
    )
    response.raise_for_status()
    data = response.json()

    return {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "description": data["weather"][0]["description"],
        "wind_speed": data["wind"]["speed"],
    }


def _fetch_forecast(city: str, api_key: str, days: int) -> list[ForecastItem]:
    """拉取并按天去重，每个日期取首个 3 小时时段作为代表"""
    days = max(1, min(days, _MAX_FORECAST_DAYS))

    response = http_session.get(
        f"{_BASE_URL}/forecast",
        params={"q": city, "appid": api_key, "units": "metric", "lang": "zh_cn"},
    )
    response.raise_for_status()
    data = response.json()

    forecasts: list[ForecastItem] = []
    processed_dates = set()
    for item in data["list"]:
        date = item["dt_txt"].split(" ")[0]
        if date not in processed_dates and len(processed_dates) < days:
            forecasts.append(
                {
                    "datetime": item["dt_txt"],
                    "temperature": item["main"]["temp"],
                    "feels_like": item["main"]["feels_like"],
                    "humidity": item["main"]["humidity"],
                    "description": item["weather"][0]["description"],
                    "wind_speed": item["wind"]["speed"],
                }
            )
            processed_dates.add(date)

    return forecasts


@mcp.tool(title="当前天气", annotations=_TOOL_ANNOTATIONS)
def get_current_weather(
    city: Annotated[str, Field(min_length=1, description="城市名称，例如 Beijing 或 北京")],
    ctx: Context | None = None,
) -> WeatherInfo:
    """获取指定城市的当前天气信息

    Args:
        city: 城市名称，例如 "Beijing" 或 "北京"

    Returns:
        包含天气信息的字典
    """
    api_key = require(load_config().openweather_api_key, "OPENWEATHER_API_KEY")

    if ctx:
        ctx.info(f"正在查询 {city} 的天气信息...")

    try:
        weather_info = _fetch_current_weather(city, api_key)
    except Exception as e:
        error_msg = f"获取天气信息失败: {e}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

    if ctx:
        ctx.info(f"成功获取到 {city} 的天气信息")

    return weather_info


@mcp.tool(title="天气预报", annotations=_TOOL_ANNOTATIONS)
def get_weather_forecast(
    city: Annotated[str, Field(min_length=1, description="城市名称")],
    days: Annotated[
        int,
        Field(ge=1, le=_MAX_FORECAST_DAYS, description="预报天数（1-5）"),
    ] = 5,
    ctx: Context | None = None,
) -> list[ForecastItem]:
    """获取指定城市的天气预报

    OpenWeatherMap 免费 5 天预报接口最多覆盖 5 天；
    每个日期取上游返回的首个 3 小时时段作为代表。

    Args:
        city: 城市名称
        days: 预报天数（默认 5 天，最大 5 天）

    Returns:
        包含未来几天天气预报的列表
    """
    api_key = require(load_config().openweather_api_key, "OPENWEATHER_API_KEY")

    if ctx:
        ctx.info(f"正在查询 {city} 的 {days} 天天气预报...")

    try:
        forecasts = _fetch_forecast(city, api_key, days)
    except Exception as e:
        error_msg = f"获取天气预报失败: {e}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg) from e

    if ctx:
        ctx.info(f"成功获取到 {city} 的 {len(forecasts)} 天天气预报")

    return forecasts


@mcp.tool(title="城市天气对比", annotations=_TOOL_ANNOTATIONS)
def compare_cities_weather(
    cities: Annotated[
        list[Annotated[str, Field(min_length=1)]],
        Field(min_length=1, description="要比较的城市名称列表（至少一个）"),
    ],
    ctx: Context | None = None,
) -> dict[str, CityWeather]:
    """比较多个城市的当前天气

    Args:
        cities: 城市名称列表

    Returns:
        以城市名为键的天气信息字典；单个城市失败不影响整体，失败城市记录 error
    """
    api_key = require(load_config().openweather_api_key, "OPENWEATHER_API_KEY")

    if ctx:
        ctx.info(f"正在比较 {len(cities)} 个城市的天气...")

    weather_comparison: dict[str, CityWeather] = {}
    for city in cities:
        try:
            weather_comparison[city] = _fetch_current_weather(city, api_key)
        except Exception as e:
            if ctx:
                ctx.error(f"获取 {city} 天气失败: {e}")
            weather_comparison[city] = {"error": str(e)}

    if ctx:
        ctx.info("城市天气对比完成")

    return weather_comparison


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=PORT, path="/mcp")
