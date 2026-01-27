@echo off
chcp 950 > nul
cd /d "%~dp0"

.venv\Scripts\python.exe run_auto_thumbnail.py

