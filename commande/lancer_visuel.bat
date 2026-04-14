@echo off
cd /d "%~dp0"
uv run abac-visuel generer --donnees "resultats\portees_admissibles.csv" --configs "configs_calcul.toml" --sortie "resultats\graphiques"
pause
