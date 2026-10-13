"""第 16 題：Agoda 自動搜尋台中，輸出飯店名與目前顯示價格。"""

import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException

from common import OUTPUT_DIR, new_driver, save_csv

URL = "https://www.agoda.com/zh-tw/"
PROFILE = Path(__file__).resolve().parent / ".browser-profile"


def source_url(url):
    """保留重現搜尋所需參數，省略匿名追蹤與暫時工作階段參數。"""
    parts = urlsplit(url)
    keep = {"city", "checkIn", "checkOut", "rooms", "adults", "children", "currencyCode", "textToSearch"}
    params = [(name, value) for name, value in parse_qsl(parts.query) if name in keep]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), ""))


def select_dates(driver, check_in, check_out):
    """只點選可見日期，並確認網站狀態已實際更新。"""
    for index, target in enumerate((check_in, check_out)):
        print(f"選擇{'入住' if index == 0 else '退房'}日：{target:%Y-%m-%d}")
        selector = f"[data-selenium-date='{target:%Y-%m-%d}']"
        if first(driver, [selector]) is None:
            # 選城市後網站可能自動開啟日曆；先等動畫，避免手動點擊又把它關閉。
            for attempt in range(3):
                if first(driver, ["[data-selenium-date]"]):
                    break
                date_box = WebDriverWait(driver, 20).until(
                    lambda d: first(d, ["#check-in-box" if index == 0 else "#check-out-box"])
                )
                date_box.click()
                try:
                    WebDriverWait(driver, 5).until(lambda d: first(d, ["[data-selenium-date]"]))
                    break
                except TimeoutException:
                    if attempt == 2:
                        raise
                    time.sleep(0.5)
        for _ in range(12):
            day = first(driver, [selector])
            if day is not None:
                break
            next_month = first(driver, ["[data-selenium='calendar-next-month-button']"])
            if not next_month or not next_month.is_enabled():
                raise RuntimeError(f"Agoda 行事曆找不到 {target:%Y-%m-%d}")
            next_month.click()
            time.sleep(0.5)
        else:
            raise RuntimeError("Agoda 行事曆無法定位指定月份")
        button = day.find_element(By.XPATH, "./ancestor::*[@role='button'][1]")
        button.click()
        field = "checkInBox" if index == 0 else "checkOutBox"
        WebDriverWait(driver, 15).until(
            lambda d: d.find_element(By.CSS_SELECTOR, f"[data-selenium='{field}']").get_attribute("data-date") == f"{target:%Y-%m-%d}"
        )
        print(f"日期已更新：{target:%Y-%m-%d}")
    # 選完日期可能自動打開人數面板，先關閉再搜尋。
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)


def first(driver, selectors):
    for selector in selectors:
        items = driver.find_elements(By.CSS_SELECTOR, selector)
        for item in items:
            if item.is_displayed():
                return item
    return None


def result_rows(driver, check_in, check_out):
    """僅解析搜尋結果中的住宿卡；沒有價格的卡片不當作完整結果。"""
    names = driver.find_elements(By.CSS_SELECTOR,
        "[data-selenium='hotel-name'], [data-testid='property-name'], .PropertyCard__HotelName")
    rows = []
    for node in names:
        try:
            hotel_name = node.text.strip()
            if not hotel_name:
                continue
            card = node
            for _ in range(8):
                card = card.find_element(By.XPATH, "..")
                if len(card.find_elements(By.CSS_SELECTOR,
                    "[data-selenium='hotel-name'], [data-testid='property-name'], .PropertyCard__HotelName")) > 1:
                    break
                prices = card.find_elements(By.CSS_SELECTOR,
                    "[data-selenium='display-price'], [data-selenium='price-display'], "
                    "[data-element-name='final-price'], [data-testid='price'], .Price__Value")
                values = [price.text.strip() for price in prices if price.is_displayed()]
                values = [value for value in values if re.search(r"\d", value)]
                if values:
                    rows.append({"飯店名": hotel_name, "價格": values[-1],
                                 "入住日": f"{check_in:%Y-%m-%d}", "退房日": f"{check_out:%Y-%m-%d}",
                                 "資料來源": source_url(driver.current_url)})
                    break
        except (NoSuchElementException, StaleElementReferenceException):
            continue
    return rows


def search_hotels(driver, check_in, check_out):
    driver.get(URL)
    hotel_tab = WebDriverWait(driver, 30).until(
        lambda d: first(d, ["button[data-element-name='all-rooms-tab']", "[data-element-name='hotel-home-tab']"])
    )
    hotel_tab.click()
    box = WebDriverWait(driver, 30).until(
        lambda d: first(d, ["input[data-selenium='textInput']", "input[placeholder*='目的地']"])
    )
    box.click()
    box.clear()
    box.send_keys("台中")
    suggestion = WebDriverWait(driver, 25).until(
        lambda d: first(d, ["[data-testid='autosuggest-item']", "[data-selenium='autosuggest-item']", "li[role='option']"])
    )
    suggestion.click()
    time.sleep(1)
    print("已選擇台中，開始操作行事曆。")
    select_dates(driver, check_in, check_out)
    search_button = WebDriverWait(driver, 20).until(
        lambda d: first(d, ["button[data-element-name='search-button']", "[data-selenium='searchButton']"])
    )
    old_windows = set(driver.window_handles)
    search_button.click()
    WebDriverWait(driver, 30).until(
        lambda d: set(d.window_handles) != old_windows or "/search" in d.current_url
    )
    new_windows = set(driver.window_handles) - old_windows
    if new_windows:
        driver.switch_to.window(new_windows.pop())
    if "/search" not in driver.current_url:
        WebDriverWait(driver, 30).until(lambda d: "/search" in d.current_url)
    # 只重試同一個真實搜尋結果頁，不切換到單間住宿或其他資料來源。
    for attempt in range(3):
        try:
            state = WebDriverWait(driver, 45).until(
                lambda d: result_rows(d, check_in, check_out)
                or ("搜尋的時候發生了點小問題" in d.find_element(By.TAG_NAME, "body").text and "error")
            )
            if state != "error":
                break
        except TimeoutException:
            pass
        if attempt == 2:
            raise RuntimeError("Agoda 台中搜尋結果頁未提供有價格的住宿卡；未以個別住宿頁起價替代。") from None
        print("搜尋結果尚未載入，重試同一個台中搜尋。")
        retry = first(driver, ["button[data-element-name='search-button']", "[data-selenium='searchButton']"])
        if retry is not None:
            retry.click()
            time.sleep(3)
        else:
            driver.refresh()
    collected, stable_bottom = {}, 0
    for _ in range(30):
        before = len(collected)
        for row in result_rows(driver, check_in, check_out):
            collected[row["飯店名"]] = row
        bottom = driver.execute_script("return window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 5")
        stable_bottom = stable_bottom + 1 if bottom and len(collected) == before else 0
        if stable_bottom >= 3:
            break
        driver.execute_script("window.scrollBy(0, 750)")
        time.sleep(0.6)
    return list(collected.values())


def main():
    driver = new_driver(profile_dir=PROFILE)
    check_in = datetime.now(ZoneInfo("Asia/Taipei")).date() + timedelta(days=14)
    check_out = check_in + timedelta(days=1)
    try:
        rows = search_hotels(driver, check_in, check_out)
        if not rows:
            raise RuntimeError("Agoda 台中搜尋結果沒有可辨識的飯店與價格。")
        save_csv("agoda_result.csv", rows)
        driver.save_screenshot(str(OUTPUT_DIR / "q16.png"))
        for name in ("q16_search_failure.png", "q16_search_failure.html"):
            (OUTPUT_DIR / name).unlink(missing_ok=True)
    except Exception:
        driver.save_screenshot(str(OUTPUT_DIR / "q16_search_failure.png"))
        (OUTPUT_DIR / "q16_search_failure.html").write_text(driver.page_source, encoding="utf-8")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
