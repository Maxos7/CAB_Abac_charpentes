@echo off
cd /d "%~dp0"
echo Vidange des resultats...
if exist "resultats\portees_admissibles.csv" del /q "resultats\portees_admissibles.csv"
if exist "resultats\registre_calcul.csv" del /q "resultats\registre_calcul.csv"
if exist "resultats\stock_charpente.csv" del /q "resultats\stock_charpente.csv"
if exist "resultats\stock_enrichi.csv" del /q "resultats\stock_enrichi.csv"
echo Resultats vides.
pause