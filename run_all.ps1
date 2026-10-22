# Windows PowerShell：建立虛擬環境、安裝套件並一次跑完 Q01–Q17。用法：.\run_all.ps1 [題號...]
Set-Location $PSScriptRoot
$venv = '.venv'
$py = "$venv\Scripts\python.exe"
if ((Test-Path $venv) -and -not (Test-Path $py)) { $venv = '.venv-win'; $py = "$venv\Scripts\python.exe" }
if (-not (Test-Path $py)) { py -3.12 -m venv $venv; if ($LASTEXITCODE -ne 0) { python -m venv $venv } }
& $py -m pip install -q -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& $py run_all.py @args
exit $LASTEXITCODE
