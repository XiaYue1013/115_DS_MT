"""第 10 題：以 Selenium 通過 PTT 八卦板年齡確認並抓網址、標題、作者。"""

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from common import OUTPUT_DIR, new_driver, save_csv

URL = "https://www.ptt.cc/bbs/Gossiping/index.html"


def main():
    driver = new_driver()
    try:
        driver.get(URL)
        if "/ask/over18" in driver.current_url:
            yes = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='yes'], .btn-big"))
            )
            yes.click()
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".r-ent"))
        )
        print("網站 title：", driver.title)
        soup = BeautifulSoup(driver.page_source, "lxml")
        rows = []
        for entry in soup.select(".r-ent"):
            link = entry.select_one(".title a[href]")
            author = entry.select_one(".author")
            title = link.get_text(" ", strip=True) if link else entry.select_one(".title").get_text(" ", strip=True)
            rows.append(
                {
                    "網址": urljoin(URL, link["href"]) if link else "",
                    "標題": title,
                    "作者": author.get_text(strip=True) if author else "",
                }
            )
        for row in rows:
            print(row["網址"], row["標題"], row["作者"], sep="\n")
        save_csv("ptt_gossiping.csv", rows)
        driver.save_screenshot(str(OUTPUT_DIR / "q10.png"))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
