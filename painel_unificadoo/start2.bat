@echo off
echo ===========================================
echo Iniciando os servidores Flask...
echo ===========================================

:: Ativa o ambiente virtual
call venv\Scripts\activate

:: Inicia o start_apps.py na porta 5002 em uma nova janela
start "Servidor 1 - start_apps.py" cmd /k "python start_apps.py"


echo.
echo Servidores iniciados com sucesso.
echo ===========================================
echo Pressione qualquer tecla para sair...
pause > nul
