import subprocess

# Nomes dos arquivos Python a serem iniciados
arquivos = ["app.py", "app2.py", "app3.py","app_login.py"]

# Lista para armazenar os processos
processos = []

try:
    # Iniciar cada arquivo como um subprocesso
    for arquivo in arquivos:
        print(f"Iniciando {arquivo}...")
        processo = subprocess.Popen(["python", arquivo], shell=True)
        processos.append(processo)

    # Manter o script principal em execução até que todos os subprocessos terminem
    for processo in processos:
        processo.wait()
except KeyboardInterrupt:
    # Caso o usuário pressione Ctrl+C, encerre todos os subprocessos
    print("\nInterrompendo subprocessos...")
    for processo in processos:
        processo.terminate()
        processo.wait()
    print("Todos os subprocessos foram encerrados.")
