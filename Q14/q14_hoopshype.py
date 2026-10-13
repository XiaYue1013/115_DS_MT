"""第 14 題：抓完 HoopsHype 薪資分頁，並從前三名球員頁取得背號。"""

import json
import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from common import OUTPUT_DIR, new_driver, save_csv

URL = "https://www.hoopshype.com/salaries/players/"


def parse_salary(value):
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else 0


def salary_table(html):
    soup = BeautifulSoup(html, "lxml")
    for table in soup.select("table"):
        headers = [th.get_text(" ", strip=True) for th in table.select("thead th")]
        if "Player" in headers and "$" in table.get_text():
            return table, headers
    return None, []


def page_rows(html):
    table, headers = salary_table(html)
    if table is None:
        return []
    names = ["排名" if not text else "球員" if text == "Player" else f"{text} 薪資" for text in headers]
    rows = []
    for tr in table.select("tbody tr"):
        cells = tr.select("th, td")
        link = tr.select_one("a[href*='/salaries/players/']")
        if len(cells) != len(names):
            continue
        row = dict(zip(names, (cell.get_text("", strip=True) for cell in cells)))
        # 退役球員等薪資紀錄可能沒有個人頁連結，仍是全表的一部分。
        row["球員頁"] = urljoin(URL, link["href"]) if link else ""
        rows.append(row)
    return rows


def pagination(driver):
    for span in driver.find_elements(By.XPATH, "//span[contains(normalize-space(.), ' of ')]"):
        match = re.fullmatch(r"(\d+)\s+of\s+(\d+)", span.text.strip())
        if match and span.is_displayed():
            return int(match[1]), int(match[2]), span.find_element(By.XPATH, "..")
    raise RuntimeError("薪資頁沒有可辨識的分頁計數，不能確認已抓完全部球員")


def expected_players(html):
    soup = BeautifulSoup(html, "lxml")
    script = soup.select_one("script#__NEXT_DATA__")
    if not script or not script.string:
        return None

    def walk(value):
        if isinstance(value, dict):
            contracts = value.get("contracts")
            if isinstance(contracts, dict) and isinstance(contracts.get("numResults"), int):
                return contracts["numResults"]
            for child in value.values():
                result = walk(child)
                if result is not None:
                    return result
        elif isinstance(value, list):
            for child in value:
                result = walk(child)
                if result is not None:
                    return result
        return None

    return walk(json.loads(script.string))


def collect_all(driver):
    WebDriverWait(driver, 60).until(lambda d: len(page_rows(d.page_source)) > 0)
    expected = expected_players(driver.page_source)
    driver.save_screenshot(str(OUTPUT_DIR / "q14.png"))
    collected = {}
    last_page = 0
    while True:
        current, total, controls = pagination(driver)
        if current != last_page + 1:
            raise RuntimeError(f"薪資分頁未連續：前頁 {last_page}、目前 {current}")
        rows = page_rows(driver.page_source)
        if not rows:
            raise RuntimeError(f"薪資第 {current} 頁沒有資料")
        for row in rows:
            # 同一球員可能同時有舊隊買斷薪資與新隊合約，不能只按球員網址去重。
            contract = tuple(row.items())
            if contract in collected:
                raise RuntimeError(f"薪資第 {current} 頁重複球員，停止避免匯出不完整資料")
            collected[contract] = row
        print(f"完成薪資第 {current}/{total} 頁，累計 {len(collected)} 筆薪資")
        if current == total:
            break
        first_row = rows[0]
        buttons = controls.find_elements(By.TAG_NAME, "button")
        if not buttons or not buttons[-1].is_enabled():
            raise RuntimeError(f"薪資第 {current} 頁的下一頁按鈕不可用")
        driver.execute_script("arguments[0].click()", buttons[-1])

        def loaded(d):
            try:
                page = pagination(d)[0]
            except RuntimeError:
                return False
            next_rows = page_rows(d.page_source)
            return page == current + 1 and next_rows and next_rows[0] != first_row

        WebDriverWait(driver, 45).until(loaded)
        last_page = current
        time.sleep(0.3)
    if expected is not None and len(collected) != expected:
        raise RuntimeError(f"網站宣告 {expected} 位球員，實際抓到 {len(collected)} 位，未保存不完整全表")
    return list(collected.values())


def player_details(driver, row):
    driver.get(row["球員頁"])
    WebDriverWait(driver, 40).until(lambda d: d.find_elements(By.TAG_NAME, "h1"))
    body = driver.find_element(By.TAG_NAME, "body").text
    # 背號位於球員標題前一行，避免把廣告或統計數字當作背號。
    match = re.search(r"(?m)^\s*#(\d{1,2})\s*$", body)
    heading = driver.find_element(By.TAG_NAME, "h1").text.strip()
    name = re.sub(r"\s+Salary$", "", heading, flags=re.I).strip() or row["球員"]
    return name, match.group(1) if match else "網站未提供"


def main():
    driver = new_driver()
    try:
        driver.get(URL)
        rows = collect_all(driver)
        salary_field = next(key for key in rows[0] if "薪資" in key)
        rows.sort(key=lambda row: parse_salary(row[salary_field]), reverse=True)
        highest = []
        for row in rows[:3]:
            name, jersey = player_details(driver, row)
            highest.append({"名字": name, "背號": jersey, "薪資": row[salary_field], "資料來源": row["球員頁"]})
        save_csv("all_play.csv", rows)
        save_csv("highest.csv", highest)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
