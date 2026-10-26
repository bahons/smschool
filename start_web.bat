@echo off
chcp 65001 > nul
setlocal

:: Python жолын автоматты анықтау
set PYTHON_EXE=C:\Users\bakyt\AppData\Local\Python\pythoncore-3.14-64\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

echo ========================================================
echo   🏫 Smart School AI: Веб-сайт және REST API
echo ========================================================
echo [1] Сервер іске қосылуда...
echo [2] Браузерден ашылатын мекенжай: http://localhost:8080
echo [3] API Swagger құжаттамасы:      http://localhost:8080/docs
echo ========================================================

:: Браузерді автоматты ашу
start http://localhost:8080

:: Серверді іске қосу
"%PYTHON_EXE%" start_server.py

pause
