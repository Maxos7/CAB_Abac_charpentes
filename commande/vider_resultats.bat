@echo off
cd /d "%~dp0"
echo Vidange des resultats...
if exist "resultats\abaque_complet_global.csv" del /q "resultats\abaque_complet_global.csv"
if exist "resultats\abaque_questionnaire.csv" del /q "resultats\abaque_questionnaire.csv"
if exist "resultats\verification_calcul.csv" del /q "resultats\verification_calcul.csv"
if exist "resultats\stock_charpente.csv" del /q "resultats\stock_charpente.csv"
if exist "resultats\stock_enrichi.csv" del /q "resultats\stock_enrichi.csv"
if exist "resultats\tenseurs.duckdb" del /q "resultats\tenseurs.duckdb"
echo Resultats vides.
pause
