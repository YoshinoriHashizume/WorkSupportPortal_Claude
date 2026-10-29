@echo off
rem This script lives in src\scripts\windows, so the repo root is three levels up.
cd /d "%~dp0..\..\.."
powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0Start-ProductionApp.ps1"
