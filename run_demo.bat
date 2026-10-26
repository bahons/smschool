@echo off
chcp 65001 > nul
setlocal

set PYTHON_EXE=C:\Users\bakyt\AppData\Local\Python\pythoncore-3.14-64\python.exe
if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=python
)

"%PYTHON_EXE%" run_demo.py %*
pause
