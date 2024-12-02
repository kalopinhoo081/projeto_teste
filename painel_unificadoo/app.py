from flask import Flask, request, render_template, jsonify, send_file
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import io
import time

app = Flask(__name__)

CHROMEDRIVER_PATH = "chromedriver.exe"
service = Service(CHROMEDRIVER_PATH)

driver = None
progress = {"current": 0, "total": 0}
generated_file = None
site_url = None  # URL do site será definida pelo front-end


@app.route("/")
def index():
    """Renderiza a página inicial."""
    return render_template("index.html")


@app.route("/configurar", methods=["POST"])
def configurar():
    """Configura a URL do site para login."""
    global site_url
    site_url = request.form.get("site_url")
    if not site_url:
        return jsonify({"error": "A URL do site não foi fornecida!"}), 400
    return jsonify({"message": "URL configurada com sucesso!"}), 200


@app.route("/iniciar", methods=["GET"])
def iniciar():
    """Inicia o navegador para login."""
    global driver
    if not site_url:
        return jsonify({"error": "A URL do site não foi configurada!"}), 400

    try:
        if driver is None:
            options = webdriver.ChromeOptions()
            options.add_experimental_option("detach", True)
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(site_url)
        return jsonify({"message": "Navegador iniciado. Faça login manualmente."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reiniciar", methods=["GET"])
def reiniciar():
    """Reinicia o navegador e permite um novo login."""
    global driver
    try:
        if driver:
            driver.quit()
        driver = None
        return jsonify({"message": "Consulta reiniciada. Configure novamente o sistema para iniciar."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/consultar", methods=["POST"])
def consultar():
    global progress, generated_file, driver

    consulta_tipo = request.form.get("tipo")
    consulta_dados = request.form.get("consulta")

    if not consulta_dados:
        return jsonify({"error": "Nenhum dado fornecido!"}), 400

    dados = consulta_dados.split("\n")
    dados = [d.strip() for d in dados if d.strip()]

    if not dados:
        return jsonify({"error": "Nenhum dado fornecido após processamento!"}), 400

    # Verifica se o driver está configurado; caso contrário, reinicia
    try:
        if driver is None:
            options = webdriver.ChromeOptions()
            options.add_experimental_option("detach", True)  # Mantenha o navegador aberto
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(site_url)  # Abre a URL configurada
    except Exception as e:
        return jsonify({"error": f"Erro ao inicializar o navegador: {str(e)}"}), 500

    progress["current"] = 0
    progress["total"] = len(dados)
    resultados = []

    try:
        for item in dados:
            try:
                # Seleção do campo de consulta
                if consulta_tipo == "ids":
                    campo_input = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[1]/div/form/span/span[2]/div[3]/div/div[1]/input'))
                    )
                elif consulta_tipo == "usernames":
                    campo_input = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[1]/div/form/span/span[2]/div[2]/div/div[1]/input'))
                    )
                else:
                    return jsonify({"error": "Tipo de consulta inválido!"}), 400

                campo_input.clear()
                campo_input.send_keys(item)

                # Clique no botão pesquisar
                botao_pesquisar = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[1]/div/form/div[3]/div/button'))
                )
                botao_pesquisar.click()

                time.sleep(1)  # Aguarda para garantir que os dados sejam carregados

                # Captura dos dados
                total_recarga = WebDriverWait(driver, 20).until(
                    lambda d: d.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/div/a[1]').text
                )
                total_recarga = ''.join(filter(str.isdigit, total_recarga.split(",")[0]))

                total_pessoas = WebDriverWait(driver, 20).until(
                    lambda d: d.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/div/a[2]').text
                )
                total_pessoas = ''.join(filter(str.isdigit, total_pessoas))

                valor_apostas = WebDriverWait(driver, 20).until(
                    lambda d: d.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[2]/div[1]/div[1]/div/div[1]/div/div/span').text
                )
                valor_apostas = valor_apostas.replace(",", "")  # Remove separador de milhar
                valor_apostas = valor_apostas.split(".")[0]  # Remove os centavos
                if valor_apostas.isdigit():
                    valor_apostas = int(valor_apostas)  # Converte para inteiro
                else:
                    valor_apostas = "Erro"

                # Cálculo do índice de apostas
                if total_recarga.isdigit() and int(total_recarga) > 0:
                    indice_apostas = float(valor_apostas) / float(total_recarga)
                else:
                    indice_apostas = "Erro"

                # Adicionando os resultados
                resultados.append({
                    "Consulta": item,
                    "Total de Recarga": total_recarga,
                    "Total de Pessoas": total_pessoas,
                    "Valor de Apostas": valor_apostas,
                    "Índice de Apostas": indice_apostas
                })
            except Exception as e:
                resultados.append({
                    "Consulta": item,
                    "Total de Recarga": "Erro",
                    "Total de Pessoas": "Erro",
                    "Valor de Apostas": "Erro",
                    "Índice de Apostas": "Erro"
                })

            progress["current"] += 1

        # Geração do arquivo Excel
        output = io.BytesIO()
        df = pd.DataFrame(resultados)
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Resultados')
        output.seek(0)
        generated_file = output

        return jsonify({"message": "Consulta concluída. Clique no botão para baixar o arquivo."}), 200

    except Exception as e:
        print(f"Erro durante a consulta: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Erro inesperado na consulta!"}), 500



@app.route("/download", methods=["GET"])
def download():
    """Permite o download do arquivo Excel gerado."""
    global generated_file
    if not generated_file:
        return jsonify({"error": "Nenhum arquivo disponível para download. Execute uma consulta primeiro."}), 400

    return send_file(
        generated_file,
        as_attachment=True,
        download_name="resultados.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/progress", methods=["GET"])
def get_progress():
    """Retorna o progresso atual da consulta."""
    return jsonify(progress)


@app.teardown_appcontext
def close_driver(exception):
    global driver
    pass


if __name__ == "__main__":
    app.run(port=5002, debug=True)
