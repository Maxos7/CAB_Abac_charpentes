@echo off
cd /d "%~dp0"
uv run sapeg-regen-stock regenerer --source "." --filtres "configs_filtre.toml" --stock-enrichi "resultats\stock_enrichi.csv"
