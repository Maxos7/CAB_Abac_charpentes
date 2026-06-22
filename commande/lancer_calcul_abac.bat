@echo off
cd /d "%~dp0"
uv run abac-vect --toml-calcul "configs_calcul_vect.toml"