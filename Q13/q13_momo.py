"""第 13 題：在 momo 自動輸入 nba，並把搜尋結果 HTML 存為 NBA_test.html。"""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from common import OUTPUT_DIR, new_driver

URL = "https://www.momoshop.com.tw/main/Main.jsp"


def find_first(driver, selectors):
    for selector in selectors:
        found = driver.find_elements(By.CSS_SELECTOR, selector)
        if found:
            return found[0]
    return None


def main():
    driver = new_driver()
    try:
        driver.get(URL)
        search = WebDriverWait(driver, 40).until(
            lambda d: find_first(
                d,
                ["#keyword", "input[name='keyword']", "input[name='search-input']", "input[type='search']"],
            )
        )
        search.clear()
        search.send_keys("nba", Keys.ENTER)
        WebDriverWait(driver, 40).until(lambda d: "nba" in d.current_url.lower() or "nba" in d.title.lower())
        path = OUTPUT_DIR / "NBA_test.html"
        path.write_text(driver.page_source, encoding="utf-8")
        driver.save_screenshot(str(OUTPUT_DIR / "q13.png"))
        print("已儲存：", path)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
