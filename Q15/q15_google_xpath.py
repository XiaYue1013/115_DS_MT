"""第 15 題：用 WebDriver 搜尋 xpath、滾動並取得更多 Google 結果。"""

import os
import time
from urllib.parse import urlparse

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from common import OUTPUT_DIR, new_driver, save_csv

HOME_URL = "https://www.google.com/?hl=zh-TW&gbv=1&filter=0"
QUERY = "xpath"


def collect(driver, seen, rows):
    for h3 in driver.find_elements(By.CSS_SELECTOR, "a h3"):
        anchor = h3.find_element(By.XPATH, "./ancestor::a[1]")
        title = h3.text.strip()
        url = anchor.get_attribute("href") or ""
        if title and url.startswith("http") and url not in seen:
            seen.add(url)
            rows.append({"標題": title, "網址": url})


def more_results(driver):
    selectors = [
        "#pnnext",
        "a[aria-label='下一頁']",
        "a[aria-label='Next page']",
    ]
    for selector in selectors:
        nodes = driver.find_elements(By.CSS_SELECTOR, selector)
        if nodes:
            nodes[0].click()
            return True
    nodes = driver.find_elements(
        By.XPATH,
        "//*[self::a or self::button][contains(., '更多結果') or contains(., 'More results')]",
    )
    if nodes:
        nodes[0].click()
        return True
    return False


def resolve_links(driver, rows):
    """用 WebDriver 跟隨 Google 結果連結並保存真正的目標網址。"""
    search_url = driver.current_url
    driver.set_page_load_timeout(20)
    for row in rows:
        original = row["網址"]
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
            row["網址"] = final_url
    driver.set_page_load_timeout(60)
    driver.get(search_url)
    WebDriverWait(driver, 60).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "a h3")) > 0
    )


def main():
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
            driver.save_screenshot(str(OUTPUT_DIR / "q15.png"))
            raise RuntimeError(f"Google 未顯示搜尋結果，目前頁面：{driver.current_url}")

        rows, seen = [], set()
        for _ in range(10):
            collect(driver, seen, rows)
            driver.execute_script("window.scrollBy(0, 900)")
            time.sleep(0.5)
        if more_results(driver):
            WebDriverWait(driver, 40).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "a h3")) > 0
            )
            for _ in range(8):
                collect(driver, seen, rows)
                driver.execute_script("window.scrollBy(0, 900)")
                time.sleep(0.5)
        if not rows:
            driver.save_screenshot(str(OUTPUT_DIR / "q15.png"))
            raise RuntimeError("Google 結果頁沒有可解析資料")
        resolve_links(driver, rows)
        for row in rows:
            print(row)
        save_csv("xpath.csv", rows)
        driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(1)
        # 直接截取目前 Google 結果頁，不建立本地 HTML。
        driver.save_screenshot(str(OUTPUT_DIR / "q15.png"))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
