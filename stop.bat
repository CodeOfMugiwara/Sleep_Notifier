@echo off
taskkill /F /FI "WINDOWTITLE eq main.py" /FI "IMAGENAME eq pythonw.exe" >nul 2>&1
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq pythonw.exe" /NH') do (
    taskkill /F /PID %%a >nul 2>&1
)
del /f /q "%~dp0notifier.pid" >nul 2>&1
echo Notifier stopped.
