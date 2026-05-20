@echo off
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
call .venv\Scripts\activate
python -m spkup
pause
