@echo off
chcp 65001 >nul
rem YT İndirici — Windows çalıştırıcı. Normalde "YT İndirici.vbs" bunu gizli çalıştırır.
cd /d "%~dp0"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo İlk kurulum: uv yükleniyor ^(Python yöneticisi^)...
  powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
if not exist ".venv\Scripts\python.exe" uv venv --python 3.12 .venv
echo Bileşenler güncelleniyor...
uv pip install -q --python .venv -U -r requirements.txt
".venv\Scripts\python.exe" app.py
if not "%~1"=="gizli" pause
