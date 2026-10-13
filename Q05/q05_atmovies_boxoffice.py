"""第 5 題：由開眼電影網進入票房排行、顯示台北榜並按 more 抓 20 筆。"""

import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from common import OUTPUT_DIR, new_driver, save_csv

URL = "https://www.atmovies.com.tw/movie/new/"


def parse_rows(html):
    soup = BeautifulSoup(html, "lxml")
    tables = soup.select("table")
    candidates = []
    for table in tables:
        rows = []
        pending = None
        for tr in table.select("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.select("th, td")]
            if len(cells) >= 2 and cells[0].strip().isdigit():
                if len(cells) == 2:
                    pending = (cells[0].strip(), cells[1])
                    continue
                rows.append(
                    {
                        "排名": cells[0].strip(),
                        "片名": cells[1],
                        "本週票房": cells[2],
                        "累計票房": cells[3] if len(cells) >= 4 else "",
                    }
                )
                pending = None
            elif pending and len(cells) >= 4:
                rows.append(
                    {
                        "排名": pending[0],
                        "片名": pending[1],
                        "本週票房": cells[2],
                        "累計票房": cells[3],
                    }
                )
                pending = None
        if rows:
            candidates.append(rows)
    return max(candidates, key=len) if candidates else []


def main():
    driver = new_driver()
    try:
        driver.get(URL)
        box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='boxoffice']"))
        )
        driver.get(box.get_attribute("href").replace("http://", "https://", 1))
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.viewMore[href*='twweekend']"))
        )
        preview = parse_rows(driver.page_source)
        print("台北排行榜預覽：")
        for row in preview:
            print(row["排名"], row["片名"], row["本週票房"])

        more = driver.find_element(By.CSS_SELECTOR, "a.viewMore[href*='twweekend']")
        driver.execute_script("arguments[0].click()", more)
        WebDriverWait(driver, 30).until(lambda d: len(parse_rows(d.page_source)) >= 10)
        time.sleep(1)
        rows = parse_rows(driver.page_source)[:20]
        save_csv("Taipei_movies.csv", rows)
        driver.save_screenshot(str(OUTPUT_DIR / "q05.png"))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
