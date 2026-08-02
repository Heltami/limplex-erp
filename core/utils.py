import re
import socket
import requests
from core.database import conectar_bd

def registrar_auditoria(usuario, acao):
    try:
        nome_estacao = socket.gethostname()
        ip_maquina = socket.gethostbyname(nome_estacao)
    except Exception:
        nome_estacao = "Desconhecida"
        ip_maquina = "0.0.0.0"

    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO auditoria (usuario, acao, estacao, ip) 
                VALUES (%s, %s, %s, %s)
            ''', (usuario, acao, nome_estacao, ip_maquina))
            conn.commit()
        except Exception as e:
            print(f"Erro ao registrar auditoria: {e}")
        finally:
            cursor.close()
            conn.close()

def validar_cpf_cnpj(doc):
    doc = re.sub(r'\D', '', str(doc))
    if len(doc) == 11:
        if doc == doc[0] * len(doc): return False
        soma = sum(int(doc[i]) * (10 - i) for i in range(9))
        d1 = (soma * 10 % 11) % 10
        if d1 != int(doc[9]): return False
        soma = sum(int(doc[i]) * (11 - i) for i in range(10))
        d2 = (soma * 10 % 11) % 10
        if d2 != int(doc[10]): return False
        return True
    elif len(doc) == 14:
        if doc == doc[0] * len(doc): return False
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma1 = sum(int(doc[i]) * pesos1[i] for i in range(12))
        d1 = 11 - (soma1 % 11)
        d1 = 0 if d1 >= 10 else d1
        if d1 != int(doc[12]): return False
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma2 = sum(int(doc[i]) * pesos2[i] for i in range(13))
        d2 = 11 - (soma2 % 11)
        d2 = 0 if d2 >= 10 else d2
        if d2 != int(doc[13]): return False
        return True
    return False

def validar_email(email):
    if not email: return True
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', str(email)) is not None

def validar_telefone(telefone):
    if not telefone: return True  
    num = re.sub(r'\D', '', str(telefone))
    return 10 <= len(num) <= 11

def validar_cep(cep):
    if not cep: return True  
    num = re.sub(r'\D', '', str(cep))
    return len(num) == 8

def buscar_cep(cep_str):
    cep_num = re.sub(r'\D', '', str(cep_str))
    if len(cep_num) == 8:
        try:
            r = requests.get(f"https://viacep.com.br/ws/{cep_num}/json/", timeout=5)
            if r.status_code == 200:
                dados = r.json()
                if "erro" not in dados:
                    return dados.get('logradouro',''), dados.get('bairro',''), dados.get('localidade',''), dados.get('uf','')
        except: pass
    return "", "", "", ""

def buscar_coordenada(rua, numero, cidade, estado):
    try:
        query = f"{rua}, {numero}, {cidade}, {estado}, Brazil"
        headers = {'User-Agent': 'LimplexERP/1.0'}
        r = requests.get(f"https://nominatim.openstreetmap.org/search?format=json&q={query}", headers=headers, timeout=5)
        if r.status_code == 200:
            dados = r.json()
            if len(dados) > 0:
                return f"{dados[0]['lat']}, {dados[0]['lon']}"
    except: pass
    return ""

def calcular_rota(coord_origem, coord_destino):
    try:
        if not coord_origem or not coord_destino: 
            return 0.0, 0
        lat1, lon1 = coord_origem.replace(" ", "").split(",")
        lat2, lon2 = coord_destino.replace(" ", "").split(",")
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            dados = r.json()
            if dados.get("routes") and len(dados["routes"]) > 0:
                distancia_km = round(dados["routes"][0]["distance"] / 1000, 1)
                tempo_minutos = round(dados["routes"][0]["duration"] / 60)
                return distancia_km, tempo_minutos
    except: pass
    return 0.0, 0