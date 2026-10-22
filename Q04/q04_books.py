"""第 4 題：只從博客來「演算法」搜尋頁及原站商品頁取得資料。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup
import requests
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from common import OUTPUT_DIR, new_driver, save_csv

BASE = "https://search.books.com.tw"
URL = f"{BASE}/search/query/key/{quote_plus('演算法')}/cat/all"
FIELDS = ["書名", "網址", "作者", "書價"]
PROFILE = Path(__file__).resolve().parent / ".browser-profile"


def product_url(href):
    url = urljoin(BASE, href)
    parts = urlparse(url)
    if parts.hostname in {"www.books.com.tw", "books.com.tw"} and parts.path.startswith("/products/"):
        return url
    if parts.hostname == "search.books.com.tw" and parts.path.startswith("/redirect/move/"):
        item = re.search(r"/item/([A-Za-z0-9]+)(?:/|$)", parts.path)
        if item:
            return "https://www.books.com.tw/products/" + item.group(1)
    return ""


def authors(node):
    links = node.select("a[href*='adv_author'], a[href*='/avtor/']")
    values = [link.get_text(' ', strip=True) for link in links]
    if any(values):
        return "、".join(dict.fromkeys(value for value in values if value))
    author = node.select_one(".author")
    if author:
        return re.sub(r"^作者[：:]\s*", "", author.get_text(" ", strip=True))
    text = node.get_text("\n", strip=True)
    match = re.search(r"作者[：:]\s*([^\n]+)", text)
    if match:
        return re.split(r"出版社[：:]|出版日期[：:]|優惠價[：:]", match.group(1))[0].strip()
    return ""


def price(node):
    area = node.select_one(".price, .set2, .price_box, .pricebox")
    text = (area or node).get_text(" ", strip=True)
    match = re.search(r"(?:優惠價|售價|網路價)[：:]?\s*(?:\d+(?:\.\d+)?\s*折\s*)?(?:NT\$|\$)?\s*([\d,]+)\s*元", text)
    if not match:
        matches = list(re.finditer(r"(?:NT\$|\$)\s*([\d,]+)|([\d,]+)\s*元", text))
        match = matches[-1] if matches else None
    if match:
        value = next(group for group in match.groups() if group is not None)
        return value.replace(",", "") + "元"
    if area:
        amounts = [element.get_text(strip=True) for element in area.select("strong, b")]
        amounts = [value for value in amounts if re.fullmatch(r"[\d,]+", value)]
        if amounts:
            return amounts[-1].replace(",", "") + "元"
    return ""


def parse_books_page(html):
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(".type02_bd-a, .table-td, li.item, .searchbook")
    if not cards:
        for heading in soup.select("h3, h4"):
            card = heading.parent
            for _ in range(3):
                if "優惠價" in card.get_text(" ", strip=True):
                    cards.append(card)
                    break
                if card.parent is None:
                    break
                card = card.parent
    rows, seen = [], set()
    for card in cards:
        candidates = card.select("h3 a[href], h4 a[href], a[title][href], a[href]")
        link = next((anchor for anchor in candidates if product_url(anchor.get("href", ""))), None)
        if link is None:
            continue
        url = product_url(link["href"])
        identity = urlparse(url).path
        title = link.get("title") or link.get_text(" ", strip=True)
        if not title or identity in seen:
            continue
        seen.add(identity)
        rows.append({"書名": title, "網址": url, "作者": authors(card), "書價": price(card)})
    return rows


def detail_fields(html):
    soup = BeautifulSoup(html, "lxml")
    metadata = soup.select_one('.type02_p002, .bookinfo') or soup
    result = {"作者": authors(metadata), "書價": price(soup.select_one('.type02_p003, .price_box') or metadata)}
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except ValueError:
            continue
        if not isinstance(data, (dict, list)):
            continue
        nodes = data if isinstance(data, list) else data.get("@graph", [data])
        for node in nodes:
            if not isinstance(node, dict):
                continue
            author = node.get("author")
            if not result["作者"] and author:
                people = author if isinstance(author, list) else [author]
                result["作者"] = "、".join(person.get("name", "") if isinstance(person, dict) else str(person) for person in people)
            offers = node.get("offers")
            if not result["書價"] and isinstance(offers, dict) and offers.get("price") is not None:
                result["書價"] = str(offers["price"]) + "元"
    return result


def main():
    rows, driver = [], None
    try:
        try:
            response = requests.get(URL, timeout=25)
            if response.ok:
                rows = parse_books_page(response.text)
        except requests.RequestException:
            pass
        if not rows:
            profile = None if os.getenv("HEADLESS") == "1" else PROFILE
            driver = new_driver(profile_dir=profile)
            driver.get(URL)
            wait = int(os.getenv("BOOKS_WAIT_TIMEOUT", "120"))
            print(f"等待博客來原站商品資料；若有驗證請在瀏覽器完成，最多 {wait} 秒。")
            for attempt in range(2):
                try:
                    rows = WebDriverWait(driver, wait).until(lambda d: parse_books_page(d.page_source))
                    break
                except TimeoutException:
                    if attempt == 0:
                        print("原站資料尚未載入，使用已保存的網站狀態重新載入同一搜尋頁。")
                        driver.refresh()
            if not rows:
                driver.save_screenshot(str(OUTPUT_DIR / "q04_failure.png"))
                (OUTPUT_DIR / "q04_failure.html").write_text(driver.page_source, encoding="utf-8")
                raise RuntimeError("博客來原站尚未提供搜尋商品，可能需要網站驗證或更換正常可用的網路；未以其他站資料替代。") from None
            driver.save_screenshot(str(OUTPUT_DIR / "q04.png"))
        for row in rows:
            if row["作者"] and row["書價"]:
                continue
            if driver is None:
                profile = None if os.getenv("HEADLESS") == "1" else PROFILE
                driver = new_driver(profile_dir=profile)
            driver.get(row["網址"])
            try:
                data = WebDriverWait(driver, 30).until(
                    lambda d: (values if (values := detail_fields(d.page_source))["作者"] and values["書價"] else False)
                )
            except TimeoutException:
                raise RuntimeError("博客來商品頁未提供完整作者及書價，未儲存不完整 booklist.csv。") from None
            row["作者"] = row["作者"] or data["作者"]
            row["書價"] = row["書價"] or data["書價"]
        save_csv("booklist.csv", rows, FIELDS)
        for name in ("q04_failure.png", "q04_failure.html"):
            (OUTPUT_DIR / name).unlink(missing_ok=True)
        for row in rows:
            print(row)
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    main()
