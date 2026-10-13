"""第 17 題：自動登入 GitHub、完成 TOTP，抓題目指定的兩張卡片。"""

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


def read_required_areas(driver):
    """只擷取原題卡片；缺少卡片時回報，不退回整個 aside/main。"""
    return driver.execute_script(r"""
        const normalize = text => (text || '').replace(/\s+/g, ' ').trim();
        const visible = element => element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden';
        const heading = title => Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,[role=heading],strong,p,span,div'))
            .find(element => visible(element) && normalize(element.textContent) === title &&
                !Array.from(element.children).some(child => normalize(child.textContent) === title));
        const first = heading('Create your first project');
        let intro = null;
        for (let parent = first?.parentElement; parent && !['MAIN','ASIDE','BODY','HTML'].includes(parent.tagName); parent = parent.parentElement) {
            intro = Array.from(parent.querySelectorAll('p,div,span')).find(element =>
                visible(element) && normalize(element.textContent).startsWith('Ready to start building?') &&
                !Array.from(element.children).some(child => normalize(child.textContent).startsWith('Ready to start building?')));
            if (intro) break;
        }
        const second = heading('Updates to your homepage feed');
        let feedIntro = null;
        let learnMore = null;
        for (let parent = second?.parentElement; parent && !['MAIN','ASIDE','BODY','HTML'].includes(parent.tagName); parent = parent.parentElement) {
            feedIntro = Array.from(parent.querySelectorAll('p,div,span')).find(element =>
                visible(element) && /^We['’]ve combined/.test(normalize(element.textContent)) &&
                !Array.from(element.children).some(child => /^We['’]ve combined/.test(normalize(child.textContent))));
            learnMore = Array.from(parent.querySelectorAll('a')).find(element =>
                visible(element) && normalize(element.textContent) === 'Learn more');
            if (feedIntro && learnMore) break;
        }
        return {
            area1: first && intro ? first.innerText + '\n' + intro.innerText : null,
            area2: second && feedIntro && learnMore ? second.innerText + '\n' + feedIntro.innerText + '\n' + learnMore.innerText : null,
        };
    """)


def main():
    username, password, secret = load_test_credentials()
    generator = make_totp(secret)
    driver = new_driver(profile_dir=PROFILE_DIR)
    try:
        ensure_login(driver, username, password, generator)
        WebDriverWait(driver, 40).until(lambda d: dashboard_loaded(d, username))
        driver.save_screenshot(str(OUTPUT_DIR / "q17_login.png"))

        def areas_ready(current_driver):
            result = read_required_areas(current_driver)
            return result if all(result.values()) else False

        def wait_for_areas():
            try:
                return WebDriverWait(driver, 30).until(areas_ready)
            except TimeoutException:
                return read_required_areas(driver)

        areas = wait_for_areas()
        if not all(areas.values()):
            # 新版首頁與 Feed 分開；只使用網站提供的同站 Feed 連結。
            feed_url = driver.execute_script("return Array.from(document.querySelectorAll('a')).find(e => e.innerText.trim() === 'Feed' && e.getClientRects().length)?.href || null")
            if feed_url and urlparse(feed_url).netloc == "github.com" and urlparse(feed_url).path == "/feed":
                print("首頁未找到原題卡片，檢查網站的 Feed 頁。")
                driver.get(feed_url)
                areas = wait_for_areas()
        if not all(areas.values()):
            missing = [str(index) for index, value in enumerate(areas.values(), 1) if not value]
            raise RuntimeError(f"GitHub Dashboard 缺少原題第 {'、'.join(missing)} 個紅框卡片，可能已改版或該帳號已關閉卡片；需核對畫面，不能用整個頁面代替。") from None
        rows = []
        for index in (1, 2):
            lines = clean_lines(areas[f"area{index}"])
            rows.append([{"序號": i, "內容": line, "來源頁": driver.current_url} for i, line in enumerate(lines, 1)])
        save_csv("github_area1.csv", rows[0])
        save_csv("github_area2.csv", rows[1])
        driver.execute_script("window.scrollTo(0, 0)")
        driver.save_screenshot(str(OUTPUT_DIR / "q17.png"))
        for stale in ("q17_verification.png", "q17_failure.png", "github_dashboard.html"):
            (OUTPUT_DIR / stale).unlink(missing_ok=True)
        print(f"Q17 完成：區域 1 共 {len(rows[0])} 行，區域 2 共 {len(rows[1])} 行")
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
