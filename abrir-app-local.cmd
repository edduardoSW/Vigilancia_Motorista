@echo off
rem Abre o app DriveSafe em modo de teste local (sem servidor e sem banco). Precisa do Python 3 instalado.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 servir_app_local.py
) else (
  python servir_app_local.py
)
pause
