@echo off
echo Configurando o ambiente virtual...
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo Ambiente configurado com sucesso!
pause
