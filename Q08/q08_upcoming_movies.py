"""第 8 題：抓開眼電影網所有近期上映推薦的名稱、上映日期與網址。"""

import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from common import get, save_csv

URL = "https://www.atmovies.com.tw/movie/next/"


def main():
    response = get(URL)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "lxml")
    rows = []
    for item in soup.select("ul.filmListAllX > li"):
        link = item.select_one(".filmtitle a[href]")
        runtime = item.select_one(".runtime")
        if not link:
            continue
        text = runtime.get_text(" ", strip=True) if runtime else ""
        match = re.search(r"\d{4}/\d{2}/\d{2}", text)
        rows.append(
            {
                "名稱": link.get_text(" ", strip=True),
                "上映日期": match.group(0) if match else "",
                "連結網址": urljoin(URL, link["href"]),
            }
        )
    for row in rows:
        print(row)
    save_csv("movies.csv", rows)


if __name__ == "__main__":
    main()
