@echo off
echo ============================================
echo   MARTINE IA - Lancement du script...
echo ============================================
cd /d "%~dp0"
cd src
python main.py
echo.
echo ============================================
echo   Fin du traitement.
echo ============================================
pause
