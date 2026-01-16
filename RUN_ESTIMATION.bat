@echo off
chcp 65001 > nul
echo 🧠 MARTINE IA - Lanceur Automatique
echo ===================================
echo.
cd /d "%~dp0"

echo 1. Lancement de l'environnement virtuel (si présent)...
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat

echo.
echo 2. Lancement de l'estimation des projets (GPT-4o)...
python src/estimate_projects.py

echo.
echo ===================================
echo ✅ Terminé ! Appuyez sur une touche pour quitter.
pause > nul
