"""第 9 題：以 Selenium 列出原題指定的四個新聞區塊。"""

import json
import time
from selenium.webdriver.support.ui import WebDriverWait

from common import OUTPUT_DIR, new_driver, save_csv

URL = "https://news.google.com/home?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
SECTIONS = ["焦點新聞", "地方新聞", "您的主題", "更多新聞"]
EXTRACT = r"""
const required = arguments[0];
const headings = [...document.querySelectorAll('main h1, main h2, main h3, main [role="heading"]')];
const result = {sections: [], rows: []};
for (const heading of headings) {
  const text = heading.textContent.trim();
  if (required.includes(text) && !result.sections.includes(text)) result.sections.push(text);
}
for (const article of document.querySelectorAll("main a.gPFEn[href], main a[data-n-tid='29'][href]")) {
  const title = article.innerText.trim();
  if (!title || !article.href) continue;
  let section = null;
  for (const heading of headings) {
    if (!(heading.compareDocumentPosition(article) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
    const text = heading.textContent.trim();
    if (required.includes(text)) section = text;
    else if (heading.tagName === 'H1' || heading.tagName === 'H2' || text === '為你精選') section = null;
    // 「您的主題」內的台灣、國際等 h3 是子分類，保持原題的主區塊歸屬。
  }
  if (section) result.rows.push({分類: section, 新聞標題: title, 網址: article.href});
}
return result;
"""


def collect(driver):
    seen, rows, found = set(), [], set()
    stable_bottom = 0
    for _ in range(80):
        data = driver.execute_script(EXTRACT, SECTIONS)
        found.update(data["sections"])
        previous_count = len(rows)
        for row in data["rows"]:
            key = (row["分類"], row["新聞標題"], row["網址"])
            if key not in seen:
                seen.add(key)
                rows.append(row)
        at_bottom = driver.execute_script("return window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 5")
        stable_bottom = stable_bottom + 1 if at_bottom and len(rows) == previous_count else 0
        if stable_bottom >= 3:
            break
        driver.execute_script("window.scrollBy(0, 750)")
        time.sleep(0.6)
    else:
        raise RuntimeError("Google 新聞仍持續載入，未確認已取得本頁全部指定區塊。")
    missing = [section for section in SECTIONS if section not in found or not any(row["分類"] == section for row in rows)]
    if missing:
        raise RuntimeError("Google 新聞缺少原題區塊或可見新聞：" + "、".join(missing))
    order = {section: i for i, section in enumerate(SECTIONS)}
    return sorted(rows, key=lambda row: order[row["分類"]])


def main():
    driver = new_driver()
    try:
        driver.get(URL)
        WebDriverWait(driver, 45).until(lambda d: d.execute_script("return document.querySelectorAll('main a.gPFEn, main a[data-n-tid=\"29\"]').length") > 5)
        rows = collect(driver)
        print("焦點提要：", ["焦點新聞", "地方新聞"])
        sections = {}
        for section in SECTIONS:
            titles = [row["新聞標題"] for row in rows if row["分類"] == section]
            sections[section] = titles
            print(section + "：")
            for title in titles:
                print(title)
        save_csv("google_news.csv", rows, ["分類", "新聞標題", "網址"])
        (OUTPUT_DIR / "google_news_sections.json").write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
        driver.execute_script("window.scrollTo(0, 0)")
        driver.save_screenshot(str(OUTPUT_DIR / "q09.png"))
        (OUTPUT_DIR / "q09_failure.png").unlink(missing_ok=True)
    except Exception:
        driver.save_screenshot(str(OUTPUT_DIR / "q09_failure.png"))
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
