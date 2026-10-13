"""第 1 題：抓開眼電影網本週新片的標題、內容、片長與網址。"""

import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from common import get, save_csv

URL = "https://www.atmovies.com.tw/movie/new/"


def main():
    response = get(URL)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "lxml")
    rows = []
    for article in soup.select("article.filmList"):
        link = article.select_one(".filmTitle a[href]")
        if not link:
            continue
        runtime = article.select_one(".runtime")
        runtime_text = runtime.get_text(" ", strip=True) if runtime else ""
        duration = re.search(r"片長[：:]?\s*\d+分", runtime_text)
        rows.append(
            {
                "標題": link.get_text(" ", strip=True),
                "內容": (article.select_one("p") or article).get_text(" ", strip=True),
                "片長": duration.group(0) if duration else "",
                "網址": urljoin(URL, link["href"]),
            }
        )
    for row in rows:
        print(row)
    save_csv("q01_movies.csv", rows)


if __name__ == "__main__":
    main()
