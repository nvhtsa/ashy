@echo off
cd /d "%~dp0"
python make-playlist.py || py make-playlist.py
echo.
pause
