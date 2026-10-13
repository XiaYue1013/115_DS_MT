"""第 2 題：抓取台灣銀行最新掛牌匯率並存成 bank.csv。

台銀目前可能顯示 JavaScript challenge，因此改用 Selenium 取得通過驗證後的
頁面，再以 BeautifulSoup 解析。這仍是台銀官方掛牌頁的即時資料。
"""

import time
import re
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait

from common import OUTPUT_DIR, new_driver, save_csv

URL = "https://rate.bot.com.tw/xrt?Lang=zh-TW"


def normalize_currency(text):
    """移除台銀同時輸出的桌機／手機重複幣別文字。"""
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    half = len(words) // 2
    if len(words) % 2 == 0 and words[:half] == words[half:]:
        return " ".join(words[:half])
    return text


def main():
    driver = new_driver()
    try:
        driver.get(URL)
        WebDriverWait(driver, 90).until(
            lambda d: len(d.find_elements("css selector", "table tbody tr")) >= 5
        )
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "lxml")
        rows = []
        for tr in soup.select("table tbody tr"):
            name = tr.select_one(".hidden-phone.print_show, .visible-phone")
            cells = tr.select("td[data-table]")
            if len(cells) < 4:
                continue
            values = [c.get_text(" ", strip=True) for c in cells]
            raw_name = name.get_text(" ", strip=True) if name else ""
            # 新版頁面把幣別也標成 data-table；匯率固定是列末四格。
            if not raw_name and len(values) >= 5:
                raw_name = values[0]
            rates = values[-4:]
            rows.append(
                {
                    "幣別": normalize_currency(raw_name),
                    "現金買入": rates[0],
                    "現金賣出": rates[1],
                    "即期買入": rates[2],
                    "即期賣出": rates[3],
                }
            )
        save_csv("bank.csv", rows)
        driver.save_screenshot(str(OUTPUT_DIR / "q02.png"))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
