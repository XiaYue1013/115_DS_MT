"""第 17 題：登入 GitHub，擷取新版首頁與 Feed 對應區塊。"""

import os
import time
from pathlib import Path
from urllib.parse import urlparse

import pyotp
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from common import OUTPUT_DIR, new_driver, save_csv

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = Path(__file__).resolve().parent / ".browser-profile"
CONFIG_KEYS = ("GITHUB_USERNAME", "GITHUB_PASSWORD", "GITHUB_TOTP_SECRET")


def load_test_credentials():
    """讀取本機 .env；環境變數優先，設定值不寫入輸出。"""
    values = {}
    config_path = ROOT / ".env"
    if config_path.exists():
        for line in config_path.read_text(encoding="utf-8-sig").splitlines():
            key, separator, value = line.partition("=")
            key = key.strip().removeprefix("export ").strip()
            if separator and key in CONFIG_KEYS:
                values[key] = value.strip().strip("\"'")
    return tuple(os.environ.get(key, values.get(key)) for key in CONFIG_KEYS)


def make_totp(secret):
    if not secret:
        return None
    # GitHub setup key 是 Base32 密鑰，不是六位驗證碼或 recovery code。
    normalized = "".join(secret.split()).upper()
    try:
        if len(normalized.rstrip("=")) < 16:
            raise ValueError
        generator = pyotp.TOTP(normalized)
        generator.at(0)  # 提前檢查格式，避免錯誤訊息帶出原始密鑰。
    except (ValueError, TypeError):
        raise RuntimeError("GITHUB_TOTP_SECRET 格式不正確，請填 GitHub 的 setup key，而非六位驗證碼。") from None
    return generator


def clean_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def signed_in(driver, username):
    account = driver.execute_script("return document.querySelector('meta[name=\"user-login\"]')?.content || ''")
    return bool(account) and (not username or account.casefold() == username.casefold())


def dashboard_loaded(driver, username):
    location = urlparse(driver.current_url)
    return location.netloc == "github.com" and location.path in ("", "/", "/dashboard") and signed_in(driver, username) and bool(driver.find_elements(By.CSS_SELECTOR, "main"))


class TotpLogin:
    """每個時間區間只送一次，最多三次；不把 TOTP 填到 Email/SMS 驗證。"""

    def __init__(self, generator):
        self.generator = generator
        self.submitted_steps = set()

    def submit_if_needed(self, driver):
        location = urlparse(driver.current_url)
        if location.netloc != "github.com" or not location.path.startswith("/sessions/two-factor"):
            return
        if any(mode in location.path for mode in ("sms", "recovery", "security-key")):
            return
        fields = driver.find_elements(By.CSS_SELECTOR, "input#app_totp, input[name='app_otp'], input[name='app_totp']")
        if location.path.rstrip("/").endswith("/app"):
            fields += driver.find_elements(By.CSS_SELECTOR, "input[name='otp'], input[autocomplete='one-time-code']")
        field = next((element for element in fields if element.is_displayed() and element.is_enabled()), None)
        if field is None:
            return
        if self.generator is None:
            raise RuntimeError("GitHub 已要求 TOTP；請在專案 .env 加入 GITHUB_TOTP_SECRET（setup key）後重跑。")
        now = time.time()
        step = int(now // self.generator.interval)
        if step in self.submitted_steps:
            return
        if len(self.submitted_steps) >= 3:
            raise RuntimeError("GitHub 三次 TOTP 驗證仍未成功，請確認 setup key 屬於此帳號，並同步電腦時間。")
        # 剩不到五秒就等下一碼；WebDriverWait 會繼續輪詢。
        if self.generator.interval - now % self.generator.interval < 5:
            return
        code = self.generator.at(now)
        form = field.find_element(By.XPATH, "ancestor::form[1]")
        self.submitted_steps.add(step)
        field.clear()
        field.send_keys(code)
        # GitHub 部分版本填滿六碼即送出；只有仍在原表單時才按按鈕。
        try:
            for button in form.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"):
                if button.is_displayed() and button.is_enabled():
                    button.click()
                    break
        except StaleElementReferenceException:
            pass
        print("已自動送出 GitHub TOTP 驗證。")


def ensure_login(driver, username, password, generator):
    driver.get("https://github.com/")
    if signed_in(driver, username):
        print("沿用已驗證的 GitHub 登入狀態。")
        return
    if signed_in(driver, None):
        raise RuntimeError("保存的瀏覽器登入了其他帳號，請在此瀏覽器切換到專案測試帳號後重跑。")
    if not username or not password:
        raise RuntimeError("尚無保存的登入狀態，請在專案 .env 設定 GITHUB_USERNAME 和 GITHUB_PASSWORD。")
    driver.get("https://github.com/login")
    WebDriverWait(driver, 30).until(lambda d: d.find_element(By.ID, "login_field")).send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.NAME, "commit").click()
    wait_seconds = int(os.getenv("GITHUB_LOGIN_TIMEOUT", "180"))
    verification = TotpLogin(generator)
    print(f"等待 GitHub 登入，TOTP 將自動處理；其他驗證請在瀏覽器完成，最多等待 {wait_seconds} 秒。")

    def login_ready(current_driver):
        if dashboard_loaded(current_driver, username):
            return True
        verification.submit_if_needed(current_driver)
        if urlparse(current_driver.current_url).path == "/login":
            if any(error.text.strip() for error in current_driver.find_elements(By.CSS_SELECTOR, ".flash-error")):
                raise RuntimeError("GitHub 登入未被接受，請確認測試帳號的帳號和密碼。")
        return False

    try:
        WebDriverWait(driver, wait_seconds, ignored_exceptions=(StaleElementReferenceException,)).until(login_ready)
        print("GitHub 登入成功，已確認為設定的測試帳號。")
    except TimeoutException:
        location = urlparse(driver.current_url).path
        if "/verified-device" in location:
            raise RuntimeError("GitHub 仍要求 Email 裝置驗證，請確認此帳號已完成啟用驗證器 2FA；額外驗證需在瀏覽器完成。") from None
        if "/two-factor" in location:
            raise RuntimeError("GitHub 兩步驟驗證尚未完成；請確認使用驗證器 TOTP、setup key 正確，且電腦時間已同步。") from None
        raise RuntimeError(f"GitHub 登入或驗證尚未完成，目前頁面路徑：{location}") from None


def read_project_section(driver, title):
    """擷取新版導覽列的專案區標題與可見 repository 連結。"""
    return driver.execute_script(r"""
        const title = arguments[0];
        const visible = e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
        const norm = s => (s || '').replace(/\s+/g, ' ').trim();
        const heading = [...document.querySelectorAll('h1,h2,h3,h4,[role=heading]')]
            .find(e => visible(e) && norm(e.innerText) === title);
        if (!heading) return null;
        let root = heading;
        while (root.parentElement && root.querySelectorAll('a[href]').length < 1 && root.tagName !== 'NAV') root = root.parentElement;
        const repos = [...root.querySelectorAll('a[href]')].filter(a => visible(a) && /^https:\/\/github\.com\/[^/]+\/[^/?#]+\/?$/.test(a.href));
        return {title, repos: repos.map(a => ({name:norm(a.innerText), url:a.href}))};
    """, title)


def read_trending_section(driver):
    """擷取 Feed「Trending repositories」區塊中的 repository 與卡片文字。"""
    return driver.execute_script(r"""
        const visible = e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
        const norm = s => (s || '').replace(/\s+/g, ' ').trim();
        const main = document.querySelector('main');
        if (!main || !norm(main.innerText).includes('Trending repositories')) return null;
        const links = [...main.querySelectorAll('a[href]')].filter(a => visible(a) && /^https:\/\/github\.com\/[^/]+\/[^/?#]+\/?$/.test(a.href));
        const unique = new Map();
        for (const a of links) {
            if (unique.has(a.href)) continue;
            let card = a;
            while (card.parentElement && card.parentElement !== main && norm(card.innerText).length < 100) card = card.parentElement;
            unique.set(a.href, {name:norm(a.innerText), url:a.href, detail:norm(card.innerText)});
        }
        return {title:'Trending repositories', repos:[...unique.values()]};
    """)


def main():
    username, password, secret = load_test_credentials()
    generator = make_totp(secret)
    driver = new_driver(profile_dir=PROFILE_DIR)
    try:
        ensure_login(driver, username, password, generator)
        WebDriverWait(driver, 40).until(lambda d: dashboard_loaded(d, username))
        home_url = "https://github.com/"
        driver.save_screenshot(str(OUTPUT_DIR / "q17_login.png"))
        WebDriverWait(driver, 30).until(lambda d: read_project_section(d, "Top repositories") is not None)
        project = read_project_section(driver, "Top repositories")
        if not project["repos"]:
            raise RuntimeError("GitHub 首頁 Top repositories 區塊目前沒有可見 repository。")
        home_rows = [{"區塊": project["title"], "序號": 1, "內容": project["title"], "網址": "", "來源頁": home_url}]
        home_rows.extend({"區塊": project["title"], "序號": i, "內容": repo["name"], "網址": repo["url"], "來源頁": home_url}
                         for i, repo in enumerate(project["repos"], 2))
        driver.execute_script("window.scrollTo(0, 0)")
        driver.save_screenshot(str(OUTPUT_DIR / "q17_area1.png"))

        feed_url = "https://github.com/feed"
        driver.get(feed_url)
        WebDriverWait(driver, 40).until(lambda d: read_trending_section(d) is not None)
        trending = read_trending_section(driver)
        if not trending["repos"]:
            raise RuntimeError("GitHub Feed 顯示 Trending repositories，但目前沒有可見專案資料。")
        feed_rows = [{"區塊": trending["title"], "序號": 1, "內容": trending["title"], "網址": "", "來源頁": feed_url}]
        for i, repo in enumerate(trending["repos"], 2):
            feed_rows.append({"區塊": trending["title"], "序號": i, "內容": repo["name"], "網址": repo["url"], "來源頁": feed_url})
            if repo["detail"] and repo["detail"] != repo["name"]:
                feed_rows.append({"區塊": trending["title"], "序號": i, "內容": repo["detail"], "網址": repo["url"], "來源頁": feed_url})
        save_csv("github_area1.csv", home_rows)
        save_csv("github_area2.csv", feed_rows)
        driver.execute_script("window.scrollTo(0, 0)")
        driver.save_screenshot(str(OUTPUT_DIR / "q17_area2.png"))
        driver.save_screenshot(str(OUTPUT_DIR / "q17.png"))
        for stale in ("q17_verification.png", "q17_failure.png", "github_dashboard.html"):
            (OUTPUT_DIR / stale).unlink(missing_ok=True)
        print(f"Q17 完成：Top repositories {len(home_rows) - 1} 個，Trending repositories {len(trending['repos'])} 個")
    except Exception:
        # 不保存登入頁 HTML，避免帳密、TOTP 或驗證欄位落入檔案。
        try:
            driver.execute_script("""
                document.querySelectorAll('input[type=password], input[autocomplete=one-time-code], input#app_totp, input[name=app_otp], input[name=app_totp], input[name=otp]')
                    .forEach(element => element.style.visibility = 'hidden');
            """)
            driver.save_screenshot(str(OUTPUT_DIR / "q17_failure.png"))
        except Exception:
            pass  # 保留原始失敗原因，即使瀏覽器已關閉。
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
