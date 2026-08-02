import pandas as pd
from core.database import conectar_bd

def garantir_colunas_clientes():
    """Garante que as colunas mais recentes existem na tabela de clientes."""
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS numero VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS complemento VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS estado VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS coordenada VARCHAR DEFAULT ''")
        cursor.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS distancia_km NUMERIC DEFAULT 0")
        cursor.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS tempo_minutos INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def listar_clientes():
    """Retorna todos os clientes ordenados do mais recente para o mais antigo."""
    conn = conectar_bd()
    try:
        df = pd.read_sql_query("SELECT * FROM clientes ORDER BY id_cliente DESC", conn)
        return df
    finally:
        conn.close()

def listar_clientes_analise():
    """Retorna os dados resumidos dos clientes para a tabela de Análise."""
    conn = conectar_bd()
    try:
        df = pd.read_sql_query('''
            SELECT id_cliente as "ID", razao_social as "Razão Social", 
                   cnpj as "CNPJ/CPF", cidade as "Cidade", coordenada as "GPS", 
                   distancia_km as "Km da Sede", tempo_minutos as "Minutos" 
            FROM clientes ORDER BY id_cliente DESC
        ''', conn)
        return df
    finally:
        conn.close()

def salvar_cliente(dados, id_cliente=None):
    """Insere um novo cliente ou atualiza um existente."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        if id_cliente is not None:
            # Atualização
            cursor.execute('''
                UPDATE clientes SET 
                    razao_social=%s, nome_fantasia=%s, cnpj=%s, inscricao_estadual=%s, 
                    contato_principal=%s, cargo=%s, whatsapp_telefone=%s, email=%s, 
                    endereco_entrega=%s, numero=%s, complemento=%s, bairro=%s, 
                    cep=%s, cidade=%s, estado=%s, coordenada=%s, distancia_km=%s, 
                    tempo_minutos=%s, condicao_pagamento=%s, horario_entrega=%s, observacoes=%s 
                WHERE id_cliente = %s
            ''', (*dados, int(id_cliente)))
        else:
            # Novo Registo
            cursor.execute('''
                INSERT INTO clientes (
                    razao_social, nome_fantasia, cnpj, inscricao_estadual, contato_principal, 
                    cargo, whatsapp_telefone, email, endereco_entrega, numero, complemento, 
                    bairro, cep, cidade, estado, coordenada, distancia_km, tempo_minutos, 
                    condicao_pagamento, horario_entrega, observacoes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', dados)
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def excluir_cliente(id_cliente):
    """Remove um cliente pelo ID."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM clientes WHERE id_cliente = %s", (int(id_cliente),))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()