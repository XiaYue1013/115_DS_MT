"""第 11 題：取得所有 NBA 商品，依網站每頁 10 筆分頁輸出 CSV。"""

import math
from common import OUTPUT_DIR, new_driver, save_csv

URL = "https://fchart.github.io/ML/nba_items.html"


def main():
    driver = new_driver()
    try:
        driver.get(URL)
        data = driver.execute_script("return window.tableData")
        per_page = int(driver.execute_script("return window.state.rows"))
        if not data:
            raise RuntimeError("網站沒有 tableData")
        for page in range(1, math.ceil(len(data) / per_page) + 1):
            chunk = data[(page - 1) * per_page : page * per_page]
            rows = [
                {"商品編號": x["id"], "商品名稱": x["title"], "價格": x["price"]}
                for x in chunk
            ]
            save_csv(f"NBA_Products{page}.csv", rows)
            print(f"儲存頁面: {page}")
        driver.save_screenshot(str(OUTPUT_DIR / "q11.png"))
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
