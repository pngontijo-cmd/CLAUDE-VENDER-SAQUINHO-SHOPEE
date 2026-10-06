@echo off
REM Roda o robô completo: busca lojas novas e depois envia as mensagens do dia.
REM Dê dois cliques neste arquivo, ou agende no Agendador de Tarefas do Windows.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

echo ==== Buscando lojas novas ====
python buscar_lojas.py

echo.
echo ==== Enviando mensagens ====
python enviar_mensagens.py

echo.
echo ==== Terminado em %date% %time% ====
