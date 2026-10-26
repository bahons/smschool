@echo off
chcp 65001 > nul
echo ========================================================
echo   Smart School AI: Веб-сайт және REST API іске қосылуда
echo   Веб-интерфейс: http://localhost:8000
echo   Swagger API:   http://localhost:8000/docs
echo ========================================================
"C:\Users\bakyt\AppData\Local\Python\pythoncore-3.14-64\python.exe" start_server.py
pause
