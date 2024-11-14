from flask import Flask, request, send_file, render_template, redirect, url_for, after_this_request
import zipfile
import os
import requests
import urllib.request
import re
import shutil
import time
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv


app = Flask(__name__)


def clean_folder():
    try:
        # Loop para percorrer todos os arquivos e subpastas dentro da pasta
        for root, dirs, files in os.walk("images", topdown=False):
            # Remover todos os arquivos dentro da pasta e subpastas
            for name in files:
                file_path = os.path.join(root, name)
                os.remove(file_path)  # Remove o arquivo

            # Remover todas as subpastas
            for name in dirs:
                dir_path = os.path.join(root, name)
                shutil.rmtree(dir_path)  # Remove a subpasta e seu conteúdo

        print(f"Pasta {"images"} limpa com sucesso!")
    except Exception as e:
        print(f"Erro ao limpar a pasta: {e}")


# Agendando a tarefa para rodar em um horário específico
def schedule_cleaning():
    scheduler = BackgroundScheduler()
    scheduler.add_job(clean_folder, 'cron', hour=3, minute=33)  # Agendar para rodar a cada 24 horas (ajuste conforme necessário)
    scheduler.start()


def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"[DEBUG] Pasta criada: {folder_path}")
    else:
        print(f"[DEBUG] Pasta já existente: {folder_path}")


def download_images(url, folder_path, order):
    image_path = os.path.join(folder_path, f"{order}.jpg")
    urllib.request.urlretrieve(url, image_path)


def get_images(mlb):
    # Usando os.path.join para montar o caminho da pasta principal
    main_folder = os.path.join("images", mlb)
    create_folder(main_folder)

    url = f"https://api.mercadolibre.com/items/{mlb}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Garante que erros HTTP sejam capturados
    except requests.RequestException as e:
        print(f"[ERROR] Falha ao acessar a API para o ID {mlb}: {e}")
        return None  # Opcionalmente, redirecionar ou retornar erro
    
    response = requests.get(url)
    response_data = response.json()
    variations = response_data.get("variations", [])
    pictures = response_data.get("pictures", [])

    if variations:
        for variation in variations:
            variation_name_parts = [
                f"{attribute['name']}-{attribute['value_name']}"
                for attribute in variation.get("attribute_combinations", [])
            ]
            variation_name = re.sub(r'[^a-zA-Z-]', '', "-".join(variation_name_parts))
            # Usando os.path.join para criar o caminho da pasta da variação
            folder_name = f"{mlb}-{variation_name}-{variation['id']}"
            img_folder = os.path.join(main_folder, folder_name)
            create_folder(img_folder)

            for order, picture_id in enumerate(variation.get("picture_ids", []), start=1):
                url = f"https://http2.mlstatic.com/D_{picture_id}-F.jpg"
                download_images(url, img_folder, order)
                
    elif pictures:
        for order, picture in enumerate(pictures, start=1):
            url = f"https://http2.mlstatic.com/D_{picture['id']}-F.jpg"
            download_images(url, main_folder, order)

    print(f"[+] Imagens do {mlb} baixadas!")
    return main_folder


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/baixar_imagens', methods=['POST'])
def baixar_imagens():
    id_usuario = request.form.get('id')
    if not id_usuario:
        return redirect(url_for('index'))
    
    caminho_imagens = get_images(id_usuario)
    caminho_zip = f"{caminho_imagens}.zip"
    
    # Criação do arquivo ZIP
    with zipfile.ZipFile(caminho_zip, 'w') as zipf:
        for root, _, files in os.walk(caminho_imagens):
            for file in files:
                print(f"Adicionando {file} ao ZIP")
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=caminho_imagens)
                zipf.write(file_path, arcname=arcname)
    
    if os.path.exists(caminho_zip):
        return send_file(caminho_zip, as_attachment=True)
    else:
        return "Erro: o arquivo ZIP não foi criado corretamente.", 500


if __name__ == '__main__':
    schedule_cleaning()
    #port = int(os.environ.get("PORT", 5000))  # Railway define a variável de ambiente PORT
    app.run(host="0.0.0.0", port=5000, debug=True)
