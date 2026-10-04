# -*- coding: utf-8 -*-
"""
豆瓣电影Top250爬虫
使用Playwright和BeautifulSoup提取豆瓣电影详细信息
支持分页采集和详情页面数据抓取
"""

import asyncio
import json
import logging
import random
import re
import traceback

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模拟真实浏览器的 User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)

# 目标网址
DOUBAN_MOVIE_TOP250_URL = "https://movie.douban.com/top250"


async def scrape_douban_movie_top250():
    """
    爬取豆瓣电影Top250信息并保存到Excel文件

    Returns:
        bool: 是否成功执行
    """
    browser = None
    try:
        logger.info("启动浏览器...")
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 设置用户代理，模拟真实浏览器
            await page.set_extra_http_headers({"User-Agent": USER_AGENT})

            all_movies = []

            # 分页采集，共10页，每页25条数据
            for i in range(10):
                start = i * 25
                url = f"{DOUBAN_MOVIE_TOP250_URL}?start={start}"
                logger.info(f"正在访问页面: {url}")

                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("networkidle")

                # 获取页面内容
                html_content = await page.content()

                # 解析HTML内容，提取基础电影信息
                movies_data = parse_movie_list_data(html_content)
                logger.info(f"第{i + 1}页提取到 {len(movies_data)} 部电影基础信息")

                # 访问每个电影的详情页面，获取更详细的信息
                for movie in movies_data:
                    try:
                        detail_url = movie.get("link", "")
                        if detail_url:
                            logger.info(f"正在访问电影详情页面: {detail_url}")
                            await page.goto(detail_url, timeout=30000)
                            await page.wait_for_load_state("networkidle")

                            # 随机延时，避免请求过于频繁
                            await asyncio.sleep(random.uniform(1, 3))

                            detail_html = await page.content()
                            detail_info = parse_movie_detail_data(detail_html)

                            # 合并基础信息和详情信息
                            movie.update(detail_info)

                        # 添加一个小延时
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                    except Exception as e:
                        logger.warning(f"获取电影详情信息时出错: {str(e)}")
                        continue

                all_movies.extend(movies_data)

                # 页面间添加随机延时
                await asyncio.sleep(random.uniform(2, 4))

            # 保存到Excel文件
            save_to_excel(all_movies)

            logger.info(f"成功提取 {len(all_movies)} 部电影信息")
            return True

    except asyncio.TimeoutError:
        logger.error("页面加载超时")
        return False
    except Exception as e:
        logger.error(f"爬取过程中发生错误: {str(e)}")
        logger.debug(traceback.format_exc())
        return False
    finally:
        # 确保浏览器被正确关闭
        if browser:
            await browser.close()
            logger.info("浏览器已关闭")


def parse_movie_list_data(html_content):
    """
    使用BeautifulSoup解析列表页面HTML内容，提取基础电影信息

    Args:
        html_content (str): 页面HTML内容

    Returns:
        list: 电影基础信息列表
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        movies = []

        # 查找电影项
        movie_items = soup.find_all("div", class_="item")
        logger.info(f"找到 {len(movie_items)} 个电影项")

        for item in movie_items:
            try:
                movie_info = {}

                # 提取排名
                rank_element = item.find("div", class_="pic")
                if rank_element:
                    em_element = rank_element.find("em")
                    if em_element:
                        movie_info["rank"] = int(em_element.get_text().strip())

                # 提取电影链接和海报
                pic_link = item.find("div", class_="pic")
                if pic_link:
                    a_element = pic_link.find("a")
                    if a_element:
                        movie_info["link"] = a_element.get("href", "")
                        img = a_element.find("img")
                        if img:
                            movie_info["poster"] = img.get("src", "")

                # 提取电影信息区域
                info_element = item.find("div", class_="info")
                if info_element:
                    # 提取电影名称
                    title_element = info_element.find("span", class_="title")
                    if title_element:
                        movie_info["title"] = title_element.get_text().strip()

                    # 提取其他标题（英文名等）
                    other_title_elements = info_element.find_all("span", class_="other")
                    other_titles = []
                    for other_title in other_title_elements:
                        other_titles.append(other_title.get_text().strip())
                    if other_titles:
                        movie_info["other_titles"] = "".join(other_titles).replace("/", "").strip()

                    # 提取导演、演员等信息
                    bd_element = info_element.find("div", class_="bd")
                    if bd_element:
                        # 提取导演和演员信息
                        director_info = bd_element.find("p", class_="")
                        if director_info:
                            movie_info["director_info"] = (
                                director_info.get_text()
                                .strip()
                                .replace("\\n", " ")
                                .replace("  ", " ")
                            )

                        # 提取评分
                        rating_element = bd_element.find("span", class_="rating_num")
                        if rating_element:
                            movie_info["rating"] = float(rating_element.get_text().strip())

                        # 提取评价人数
                        star_element = bd_element.find("div", class_="star")
                        if star_element:
                            people_elements = star_element.find_all("span")
                            if people_elements and len(people_elements) > 1:
                                people_text = people_elements[-1].get_text().strip()
                                # 提取括号内的数字
                                people_match = re.search(r"(\\d+)", people_text)
                                if people_match:
                                    movie_info["review_count"] = int(people_match.group(1))
                                else:
                                    movie_info["review_count"] = 0

                        # 提取简介
                        quote_element = bd_element.find("span", class_="inq")
                        if quote_element:
                            movie_info["quote"] = quote_element.get_text().strip()

                # 只有当提取到标题时才添加到结果中
                if "title" in movie_info and movie_info["title"]:
                    movies.append(movie_info)

            except Exception as e:
                logger.warning(f"解析单个电影项时出错: {str(e)}")
                continue

        return movies

    except Exception as e:
        logger.error(f"解析HTML内容时发生错误: {str(e)}")
        return []


def parse_movie_detail_data(html_content):
    """
    使用BeautifulSoup解析详情页面HTML内容，提取详细电影信息

    Args:
        html_content (str): 详情页面HTML内容

    Returns:
        dict: 电影详细信息
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        detail_info = {}

        # 提取海报图片
        poster_img = (
            soup.find("div", id="mainpic").find("img") if soup.find("div", id="mainpic") else None
        )
        if poster_img:
            detail_info["detail_poster"] = poster_img.get("src", "")

        # 提取基本信息区域
        info_wrapper = soup.find("div", class_="info_wrapper")
        if not info_wrapper:
            info_wrapper = soup.find("div", id="info")

        if info_wrapper:
            # 提取导演
            director_element = info_wrapper.find("span", class_="attrs")
            if director_element and director_element.parent.get_text().startswith("导演"):
                directors = [a.get_text().strip() for a in director_element.find_all("a")]
                detail_info["directors"] = ", ".join(directors)

            # 提取编剧
            scenario_elements = info_wrapper.find_all("span", class_="attrs")
            for elem in scenario_elements:
                if elem.parent.get_text().startswith("编剧"):
                    scenarists = [a.get_text().strip() for a in elem.find_all("a")]
                    detail_info["scenarists"] = ", ".join(scenarists)
                    break

            # 提取主演
            actor_elements = info_wrapper.find_all("span", class_="attrs")
            for elem in actor_elements:
                if elem.parent.get_text().startswith("主演"):
                    actors = [a.get_text().strip() for a in elem.find_all("a")]
                    detail_info["actors"] = ", ".join(actors)
                    break

            # 提取类型
            genre_element = info_wrapper.find("span", property="v:genre")
            if genre_element:
                genres = [
                    elem.get_text().strip()
                    for elem in info_wrapper.find_all("span", property="v:genre")
                ]
                detail_info["genres"] = ", ".join(genres)

            # 提取制片国家/地区
            country_match = re.search(r"制片国家/地区:</span>(.*?)<br", str(info_wrapper))
            if country_match:
                detail_info["countries"] = country_match.group(1).strip()

            # 提取语言
            language_match = re.search(r"语言:</span>(.*?)<br", str(info_wrapper))
            if language_match:
                detail_info["languages"] = language_match.group(1).strip()

            # 提取上映日期
            release_date_elements = info_wrapper.find_all("span", property="v:initialReleaseDate")
            if release_date_elements:
                release_dates = [elem.get_text().strip() for elem in release_date_elements]
                detail_info["release_dates"] = ", ".join(release_dates)

            # 提取片长
            runtime_element = info_wrapper.find("span", property="v:runtime")
            if runtime_element:
                detail_info["runtime"] = runtime_element.get_text().strip()

            # 提取又名
            aka_match = re.search(r"又名:</span>(.*?)<br", str(info_wrapper))
            if aka_match:
                detail_info["aka"] = aka_match.group(1).strip()

            # 提取IMDb链接
            imdb_match = re.search(r"IMDb:</span>(.*?)<br", str(info_wrapper))
            if imdb_match:
                detail_info["imdb"] = imdb_match.group(1).strip()

        # 提取评分信息
        rating_element = soup.find("strong", class_="rating_num")
        if rating_element:
            detail_info["detail_rating"] = float(rating_element.get_text().strip())

        # 提取评分人数
        rating_people_element = soup.find("span", property="v:votes")
        if rating_people_element:
            detail_info["detail_rating_votes"] = int(rating_people_element.get_text().strip())

        # 提取评分分布
        ratings_on_weight = soup.find("div", class_="ratings-on-weight")
        if ratings_on_weight:
            rating_stars = ratings_on_weight.find_all("span", class_="rating_per")
            star_ratings = {}
            for i, star_elem in enumerate(rating_stars):
                star_ratings[f"{5 - i}星占比"] = star_elem.get_text().strip()
            detail_info["star_ratings"] = star_ratings

        # 提取简介
        summary_element = soup.find("span", property="v:summary")
        if summary_element:
            detail_info["summary"] = (
                summary_element.get_text().strip().replace(" ", "").replace("\\n", "")
            )
        elif soup.find("div", id="link-report"):
            summary_element = soup.find("div", id="link-report").find("span", class_="short")
            if summary_element:
                detail_info["summary"] = (
                    summary_element.get_text().strip().replace(" ", "").replace("\\n", "")
                )

        return detail_info

    except Exception as e:
        logger.warning(f"解析详情页面时出错: {str(e)}")
        return {}


def save_to_excel(data, filename="douban_movie_top250_detailed.xlsx"):
    """
    将数据保存为Excel文件

    Args:
        data (list): 要保存的数据
        filename (str): 文件名
    """
    try:
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine="openpyxl")
        logger.info(f"数据已保存至 {filename}")
    except Exception as e:
        logger.error(f"保存Excel文件时发生错误: {str(e)}")


def save_to_json(data, filename="douban_movie_top250_detailed.json"):
    """
    将数据保存为JSON文件

    Args:
        data (list): 要保存的数据
        filename (str): 文件名
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"数据已保存至 {filename}")
    except Exception as e:
        logger.error(f"保存文件时发生错误: {str(e)}")


async def main():
    """
    主函数
    """
    try:
        success = await scrape_douban_movie_top250()
        if success:
            print("豆瓣电影Top250详细数据已成功提取并保存到 douban_movie_top250_detailed.xlsx")
        else:
            print("提取豆瓣电影Top250详细数据时发生错误，请查看日志")
    except Exception as e:
        logger.error(f"程序执行过程中发生未预期的错误: {str(e)}")
        print("程序执行失败，请查看日志")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
