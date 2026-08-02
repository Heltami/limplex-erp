import pandas as pd
from core.database import conectar_bd

def garantir_colunas_fornecedores():
    """Garante que a tabela de fornecedores tem a estrutura logística correta."""
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS cargo VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS cep VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS numero VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS complemento VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS bairro VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS estado VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS coordenada VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS distancia_km NUMERIC DEFAULT 0")
        cursor.execute("ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS tempo_minutos INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def listar_fornecedores():
    """Retorna a lista completa de fornecedores."""
    conn = conectar_bd()
    try:
        df = pd.read_sql_query("SELECT * FROM fornecedores ORDER BY id_fornecedor DESC", conn)
        return df
    finally:
        conn.close()

def listar_fornecedores_analise():
    """Retorna os dados formatados para a grelha de análise."""
    conn = conectar_bd()
    try:
        df = pd.read_sql_query('''
            SELECT id_fornecedor as "ID", nome_fantasia as "Fornecedor", 
                   cidade as "Cidade", coordenada as "GPS", 
                   distancia_km as "Km da Sede", tempo_minutos as "Minutos" 
            FROM fornecedores ORDER BY id_fornecedor DESC
        ''', conn)
        return df
    finally:
        conn.close()

def salvar_fornecedor(dados, id_fornecedor=None):
    """Insere um novo fornecedor ou atualiza um existente."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        if id_fornecedor is not None:
            cursor.execute('''
                UPDATE fornecedores SET 
                    nome_fantasia=%s, razao_social=%s, cnpj=%s, contato=%s, cargo=%s, 
                    telefone=%s, email=%s, endereco=%s, numero=%s, complemento=%s, 
                    bairro=%s, cep=%s, cidade=%s, estado=%s, coordenada=%s, 
                    distancia_km=%s, tempo_minutos=%s, prazo_pagamento=%s 
                WHERE id_fornecedor = %s
            ''', (*dados, int(id_fornecedor)))
        else:
            cursor.execute('''
                INSERT INTO fornecedores (
                    nome_fantasia, razao_social, cnpj, contato, cargo, telefone, email, 
                    endereco, numero, complemento, bairro, cep, cidade, estado, 
                    coordenada, distancia_km, tempo_minutos, prazo_pagamento
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', dados)
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def excluir_fornecedor(id_fornecedor):
    """Elimina um fornecedor pelo ID."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM fornecedores WHERE id_fornecedor = %s", (int(id_fornecedor),))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()