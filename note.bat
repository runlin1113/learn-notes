@echo off
rem note 快捷入口（Windows）
rem 优先使用项目自带的 .venv（已含 mkdocs-material），否则回退到系统 python
set "VENV=%~dp0.venv\Scripts\python.exe"
if exist "%VENV%" (
  "%VENV%" "%~dp0tools\note.py" %*
) else (
  python "%~dp0tools\note.py" %*
)
