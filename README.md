# 資料科學期中作業

17 題網站爬蟲程式，使用 Requests、BeautifulSoup 與 Selenium 取得資料。各題可獨立執行，結果儲存在該題的 `output/`。

## 安裝

需要 Python 3.12 以上、Chrome 與網路連線。第 3 題另需系統提供的 `curl`。

先下載專案：

```bash
git clone https://github.com/XiaYue1013/115_DS_MT.git
cd 115_DS_MT
```

### Windows（PowerShell）

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python Q01\q01_atmovies_new.py
```

若 PowerShell 無法啟用虛擬環境，可直接使用環境中的 Python：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe Q01\q01_atmovies_new.py
```

### macOS

確認 `python3 --version` 為 3.12 以上後執行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python Q01/q01_atmovies_new.py
```

### Linux

先安裝 Python 3.12 以上、對應的 `venv` 套件、Chrome 與 `curl`，再執行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python Q01/q01_atmovies_new.py
```

每個作業系統都需各自建立虛擬環境。

## 一鍵執行全部題目

clone 後直接執行，腳本會自動建立虛擬環境、安裝套件、必要時複製 `.env.example` 為 `.env`，並依序跑完 17 題，結束時列出每題成功或失敗：

| 系統 | 指令 |
|---|---|
| macOS／Linux | `./run_all.sh` |
| Windows PowerShell | `.\run_all.ps1` |
| Windows cmd（或雙擊） | `run_all.bat` |

只跑部分題目時在後面加題號，例如 `./run_all.sh 1 5 17`。Windows、macOS 預設開啟可見瀏覽器，Linux 預設無頭；可用環境變數 `HEADLESS=1`（無頭）或 `HEADLESS=0`（有頭）覆蓋。第 7、17 題需先完成下方「設定」，否則該題會失敗，不影響其他題。

## 設定

第 7、17 題會讀取專案根目錄的 `.env`。第一次使用時複製設定範本；已有 `.env` 時直接編輯，避免覆蓋原設定。

macOS／Linux：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

### 第 7 題：Google Books API

在 `.env` 填入金鑰，並在金鑰所屬的 Google Cloud 專案啟用 Books API：

```dotenv
GOOGLE_BOOKS_API_KEY=你的GoogleBooksAPI金鑰
```

程式搜尋 `Python`，以 `maxResults=10`、`projection=lite`、`startIndex=0` 與 `10` 取得兩頁資料。API 未提供的欄位標示為「API未提供」。

### 第 17 題：GitHub 登入

在 `.env` 填入帳號、密碼與驗證器設定密鑰：

```dotenv
GITHUB_USERNAME=你的GitHub帳號
GITHUB_PASSWORD=你的GitHub密碼
GITHUB_TOTP_SECRET=你的驗證器設定密鑰
```

在 GitHub 的 Settings → Password and authentication 啟用驗證器（TOTP）兩步驟驗證，設定時保存 **setup key** 並填入 `GITHUB_TOTP_SECRET`。這是設定密鑰，不是六位驗證碼或 recovery code。程式會自動產生並填入驗證碼；電腦時間需保持同步。[GitHub 設定說明](https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa/configuring-two-factor-authentication)

登入狀態保存在 `Q17/.browser-profile/`，請勿同時執行多份第 17 題程式。原題的兩張卡片在 GitHub 新版介面可能不存在；缺少指定卡片時會報錯，不產生兩區 CSV。

環境變數可覆蓋 `.env` 設定。`.env`、瀏覽器登入資料與執行結果均不納入 Git。

## 執行與輸出

啟用虛擬環境後，在專案根目錄執行對應程式，例如：

```bash
python Q07/q07_google_books.py
python Q14/q14_hoopshype.py
python Q16/q16_agoda.py
```

程式會自動建立各題的 `output/`，重跑會更新同名結果。CSV 採用 UTF-8-SIG，可用 Excel 開啟。第 6 題預設使用 2026 球季；第 16 題搜尋台中，入住與退房日為台北時間執行日後 14、15 天。

| 題號 | 程式 | 主要輸出 |
|---|---|---|
| 1 | `Q01/q01_atmovies_new.py` | `q01_movies.csv` |
| 2 | `Q02/q02_bot_rates.py` | `bank.csv` |
| 3 | `Q03/q03_data_gov.py` | `NHI_EnteroviralInfection.csv` |
| 4 | `Q04/q04_books.py` | `booklist.csv` |
| 5 | `Q05/q05_atmovies_boxoffice.py` | `Taipei_movies.csv` |
| 6 | `Q06/q06_nba_players.py` | `players.csv` |
| 7 | `Q07/q07_google_books.py` | `pythonbook.csv` |
| 8 | `Q08/q08_upcoming_movies.py` | `movies.csv` |
| 9 | `Q09/q09_google_news.py` | `google_news.csv` |
| 10 | `Q10/q10_ptt_gossiping.py` | `ptt_gossiping.csv` |
| 11 | `Q11/q11_nba_products.py` | `NBA_Products1.csv` 等分頁檔 |
| 12 | `Q12/q12_google_steam.py` | `steam_games.csv` |
| 13 | `Q13/q13_momo.py` | `NBA_test.html` |
| 14 | `Q14/q14_hoopshype.py` | `all_play.csv`、`highest.csv` |
| 15 | `Q15/q15_google_xpath.py` | `xpath.csv` |
| 16 | `Q16/q16_agoda.py` | `agoda_result.csv` |
| 17 | `Q17/q17_github_dashboard.py` | `github_area1.csv`、`github_area2.csv` |

## 瀏覽器使用

Selenium 預設開啟可見瀏覽器，並自動管理 ChromeDriver；首次執行可能需要下載。若網站要求 CAPTCHA 或額外驗證，需在瀏覽器完成。

不需要人工操作時，可使用無頭模式。macOS／Linux：

```bash
HEADLESS=1 python Q11/q11_nba_products.py
```

Windows PowerShell：

```powershell
$env:HEADLESS = '1'
python Q11/q11_nba_products.py
Remove-Item Env:HEADLESS
```

第 4、16 題建議使用可見瀏覽器。網站改版、連線限制或驗證可能造成失敗，請依錯誤訊息檢查後重跑。
