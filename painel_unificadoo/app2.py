from flask import Flask, request, render_template, jsonify, send_file
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import io
import time
import re  # Adicionado para manipular o texto do saldo

app = Flask(__name__)

CHROMEDRIVER_PATH = "chromedriver.exe"
service = Service(CHROMEDRIVER_PATH)

driver = None
progress = {"current": 0, "total": 0}
generated_file = None
site_url = None  # URL do site será definida pelo front-end


@app.route("/index2")
def index2():
    return render_template("index2.html")


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
    """Consulta os dados fornecidos e gera o arquivo Excel."""
    global progress, generated_file

    consulta_tipo = request.form.get("tipo")
    consulta_dados = request.form.get("consulta")

    if not consulta_dados:
        return jsonify({"error": "Nenhum dado fornecido!"}), 400

    dados = consulta_dados.split("\n")
    dados = [d.strip() for d in dados if d.strip()]

    if not dados:
        return jsonify({"error": "Nenhum dado fornecido após processamento!"}), 400

    progress["current"] = 0
    progress["total"] = len(dados)
    resultados = []

    try:
        for item in dados:
            try:
                # Campo de entrada
                campo_input = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[1]/div[1]/form/span[1]/div[2]/div/div[1]/input'))
                )
                campo_input.clear()
                campo_input.send_keys(item)

                # Botão de pesquisa
                botao_pesquisar = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[1]/div[1]/form/div/div/button[1]'))
                )
                botao_pesquisar.click()

                time.sleep(1.3)

                if consulta_tipo == "ids":
                    # Consulta nome de usuário pelo ID
                    nome_usuario = WebDriverWait(driver, 10).until(
                        lambda d: d.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[3]/div[2]/div[3]/div[3]/table/tbody/tr/td[2]/div/div[1]/button').text
                    )
                    saldo_completo = WebDriverWait(driver, 10).until(
                        lambda d: d.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[3]/div[2]/div[3]/div[3]/table/tbody/tr/td[4]/div/div[4]').text
                    )
                    # Extração apenas dos números do saldo
                    saldo = re.search(r'\d+', saldo_completo).group()
                    resultados.append({"ID": item, "Nome de Usuário": nome_usuario, "Saldo": saldo})
                elif consulta_tipo == "usernames":
                    # Consulta ID pelo nome de usuário
                    id_usuario = WebDriverWait(driver, 10).until(
                        lambda d: d.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[3]/div[2]/div[3]/div[3]/table/tbody/tr/td[2]/div/div[2]/button').text
                    )
                    saldo_completo = WebDriverWait(driver, 10).until(
                        lambda d: d.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/section/div[1]/div[3]/div[2]/div[3]/div[3]/table/tbody/tr/td[4]/div/div[4]').text
                    )
                    # Extração apenas dos números do saldo
                    saldo = re.search(r'\d+', saldo_completo).group()
                    resultados.append({"Nome de Usuário": item, "ID": id_usuario, "Saldo": saldo})
                else:
                    return jsonify({"error": "Tipo de consulta inválido!"}), 400

            except Exception as e:
                resultados.append({
                    "Consulta": item,
                    "Resultado": "Erro na consulta",
                    "Saldo": "N/A"
                })

            progress["current"] += 1

        # Gera o arquivo Excel
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
    app.run(port=5001, debug=True)
