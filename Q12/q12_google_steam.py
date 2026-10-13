"""第 12 題：用 WebDriver 在 Google 輸入「Steam 遊戲推薦」並抓結果。"""

import os
import time
from urllib.parse import urlparse

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from common import OUTPUT_DIR, new_driver, save_csv

HOME_URL = "https://www.google.com/?hl=zh-TW&gbv=1"
QUERY = "Steam 遊戲推薦"


def collect(driver):
    rows, seen = [], set()
    for h3 in driver.find_elements(By.CSS_SELECTOR, "a h3"):
        anchor = h3.find_element(By.XPATH, "./ancestor::a[1]")
        title = h3.text.strip()
        url = anchor.get_attribute("href") or ""
        if title and url.startswith("http") and url not in seen:
            seen.add(url)
            rows.append({"搜尋結果": title, "超連結": url})
    return rows


def resolve_links(driver, rows):
    """實際開啟 Google 的結果轉址，換成最後的目標網址。"""
    search_url = driver.current_url
    driver.set_page_load_timeout(20)
    for row in rows:
        original = row["超連結"]
        if urlparse(original).netloc not in {"www.google.com", "google.com"}:
            continue
        resolved = False
        try:
            driver.get(original)
            resolved = True
        except TimeoutException:
            resolved = True
            try:
                driver.execute_script("window.stop()")
            except WebDriverException:
                pass
        except WebDriverException:
            pass
        final_url = driver.current_url
        if resolved and "/goto?" not in final_url:
            row["超連結"] = final_url
    driver.set_page_load_timeout(60)
    driver.get(search_url)
    WebDriverWait(driver, 60).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "a h3")) > 0
    )


def main():
    # Google 在共享環境執行前端偵測時可能轉到驗證頁；關閉頁面 JavaScript
    # 後仍由 WebDriver 操作 Google 的標準 HTML 搜尋表單與真實結果頁。
    os.environ.setdefault("DISABLE_JAVASCRIPT", "1")
    driver = new_driver()
    try:
        driver.get(HOME_URL)
        search = WebDriverWait(driver, 30).until(
            lambda d: d.find_element(By.CSS_SELECTOR, "textarea[name='q'], input[name='q']")
        )
        search.send_keys(QUERY, Keys.ENTER)
        try:
            WebDriverWait(driver, 60).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "a h3")) > 0
            )
        except TimeoutException:
            driver.save_screenshot(str(OUTPUT_DIR / "q12.png"))
            raise RuntimeError(f"Google 未顯示搜尋結果，目前頁面：{driver.current_url}")
        rows = collect(driver)
        if not rows:
            driver.save_screenshot(str(OUTPUT_DIR / "q12.png"))
            raise RuntimeError("Google 結果頁沒有可解析的標題與超連結")
        resolve_links(driver, rows)
        for row in rows:
            print(row["搜尋結果"], row["超連結"], sep="\n")
        save_csv("steam_games.csv", rows)
        driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(1)
        # 直接截取 Google 真實結果頁，不建立本地 HTML。
        driver.save_screenshot(str(OUTPUT_DIR / "q12.png"))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
