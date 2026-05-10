"""天气查询 MCP 服务器"""

from fastmcp import Context, FastMCP

from hello_mcp.config import load_config
from hello_mcp.utils.http_client import create_session

mcp = FastMCP("Weather Agent")

http_session = create_session()


@mcp.tool
def get_current_weather(city: str, ctx: Context = None) -> dict:
    """获取指定城市的当前天气信息

    Args:
        city: 城市名称，例如 "Beijing" 或 "北京"

    Returns:
        包含天气信息的字典
    """
    config = load_config()

    if ctx:
        ctx.info(f"正在查询 {city} 的天气信息...")

    try:
        url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": config.OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "zh_cn",
        }

        response = http_session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        weather_info = {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
        }

        if ctx:
            ctx.info(f"成功获取到 {city} 的天气信息")

        return weather_info

    except Exception as e:
        error_msg = f"获取天气信息失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool
def get_weather_forecast(city: str, days: int = 5, ctx: Context = None) -> list:
    """获取指定城市的天气预报

    Args:
        city: 城市名称
        days: 预报天数（默认 5 天，最大 7 天）

    Returns:
        包含未来几天天气预报的列表
    """
    config = load_config()

    if ctx:
        ctx.info(f"正在查询 {city} 的 {days} 天天气预报...")

    try:
        days = max(1, min(days, 7))

        url = "http://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": city,
            "appid": config.OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "zh_cn",
        }

        response = http_session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        forecasts = []
        processed_dates = set()

        for item in data["list"]:
            date = item["dt_txt"].split(" ")[0]

            if date not in processed_dates and len(processed_dates) < days:
                forecast = {
                    "datetime": item["dt_txt"],
                    "temperature": item["main"]["temp"],
                    "feels_like": item["main"]["feels_like"],
                    "humidity": item["main"]["humidity"],
                    "description": item["weather"][0]["description"],
                    "wind_speed": item["wind"]["speed"],
                }
                forecasts.append(forecast)
                processed_dates.add(date)

        if ctx:
            ctx.info(f"成功获取到 {city} 的 {len(forecasts)} 天天气预报")

        return forecasts

    except Exception as e:
        error_msg = f"获取天气预报失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool
def compare_cities_weather(cities: list[str], ctx: Context = None) -> dict:
    """比较多个城市的当前天气

    Args:
        cities: 城市名称列表

    Returns:
        包含各城市天气信息的字典
    """
    if ctx:
        ctx.info(f"正在比较 {len(cities)} 个城市的天气...")

    try:
        weather_comparison = {}

        for city in cities:
            try:
                weather_info = get_current_weather.fn(city, ctx)
                weather_comparison[city] = weather_info
            except Exception as e:
                weather_comparison[city] = {"error": str(e)}

        if ctx:
            ctx.info("城市天气对比完成")

        return weather_comparison

    except Exception as e:
        error_msg = f"城市天气对比失败: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise RuntimeError(error_msg)


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8001, path="/mcp")
