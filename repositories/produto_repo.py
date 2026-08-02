import pandas as pd
from core.database import conectar_bd

def aplicar_precificacao_limplex(sku_especifico=None):
    """Calcula margens, lucros e o status de todos os produtos ou de um específico."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        sql_math = '''
            UPDATE produtos p
            SET lucro_reais = 
                    (p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) 
                    - p.prc_distribuidora 
                    - ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) * c.perc_imposto / 100.0) 
                    - ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) * c.perc_frete / 100.0),
                margem_lucro = ROUND(CAST((
                    ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) 
                     - p.prc_distribuidora 
                     - ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) * c.perc_imposto / 100.0) 
                     - ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) * c.perc_frete / 100.0)
                    ) / NULLIF((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)), 0)
                ) * 100 AS NUMERIC), 2)
            FROM configuracoes c WHERE c.id = 1
        '''
        
        sql_status = '''
            UPDATE produtos
            SET status = CASE 
                WHEN margem_lucro >= (SELECT margem_lucro_desejada FROM configuracoes WHERE id=1) THEN 'LUCRO'
                WHEN margem_lucro > 0 THEN 'NORMAL'
                ELSE 'PERDA'
            END
            WHERE status != 'INATIVO'
        '''
        
        if sku_especifico:
            sql_math += " AND p.sku = %s"
            cursor.execute(sql_math, (sku_especifico,))
            sql_status += " AND sku = %s"
            cursor.execute(sql_status, (sku_especifico,))
        else:
            cursor.execute(sql_math)
            cursor.execute(sql_status)
        
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def listar_fornecedores_combo():
    """Busca a lista de fornecedores para preencher os selectboxes."""
    conn = conectar_bd()
    try:
        return pd.read_sql_query("SELECT id_fornecedor, nome_fantasia FROM fornecedores ORDER BY nome_fantasia", conn)
    finally:
        conn.close()

def salvar_produto(id_fornecedor, sku, descricao, prc_distribuidora, preco_venda):
    """Insere um novo produto no catálogo."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO produtos (id_fornecedor, sku, descricao, prc_distribuidora, preco_venda, status)
            VALUES (%s, %s, %s, %s, %s, 'NORMAL')
        ''', (id_fornecedor, sku, descricao, prc_distribuidora, preco_venda))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def listar_produtos(filtro_forn, sql_add, params_add):
    """Gera a grelha de produtos baseada nos filtros dinâmicos."""
    query = '''
        SELECT p.id_produto, p.id_fornecedor, p.sku, p.descricao, f.nome_fantasia as fornecedor, 
               p.prc_distribuidora as custo, 
               p.preco_venda, 
               (p.preco_venda * (1 - c.perc_desconto_padrao / 100.0)) as preco_limplex,
               p.lucro_reais, p.margem_lucro, p.status
        FROM produtos p
        JOIN fornecedores f ON p.id_fornecedor = f.id_fornecedor
        CROSS JOIN (SELECT perc_desconto_padrao FROM configuracoes WHERE id = 1) c
        WHERE p.status != 'INATIVO'
    '''
    params = []
    if filtro_forn != "Todos":
        query += " AND f.nome_fantasia = %s"
        params.append(filtro_forn)
        
    if sql_add:
        query += sql_add
        params.extend(params_add)
        
    query += " ORDER BY p.descricao"
    
    conn = conectar_bd()
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()

def inativar_produtos(ids_lista):
    """Marca uma lista de produtos como INATIVO."""
    if not ids_lista: return True, ""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        if len(ids_lista) == 1:
            ids_tuple = f"({ids_lista[0]})"
        else:
            ids_tuple = tuple(ids_lista)
        cursor.execute(f"UPDATE produtos SET status = 'INATIVO' WHERE id_produto IN {ids_tuple}")
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def atualizar_produtos_em_lote(mudancas_dict, df_referencia):
    """Aplica edições feitas diretamente na grelha do Streamlit (Data Editor)."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        for row_idx, edits in mudancas_dict.items():
            id_p_real = df_referencia.iloc[row_idx]['id_produto']
            set_clauses = []
            set_params = []
            if 'descricao' in edits: 
                set_clauses.append("descricao = %s")
                set_params.append(edits['descricao'])
            if 'custo' in edits: 
                set_clauses.append("prc_distribuidora = %s")
                set_params.append(edits['custo'])
            if 'preco_venda' in edits: 
                set_clauses.append("preco_venda = %s")
                set_params.append(edits['preco_venda'])
                
            if set_clauses:
                set_params.append(int(id_p_real))
                cursor.execute(f"UPDATE produtos SET {', '.join(set_clauses)} WHERE id_produto = %s", set_params)
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def importar_produtos_excel_csv(id_forn_destino, dados_lista):
    """Faz o UPSERT (Insert or Update) em massa vindos de um Excel."""
    conn = conectar_bd()
    cursor = conn.cursor()
    importados = 0
    try:
        for sku, desc, custo, venda in dados_lista:
            cursor.execute('''
                INSERT INTO produtos (id_fornecedor, sku, descricao, prc_distribuidora, preco_venda, status)
                VALUES (%s, %s, %s, %s, %s, 'NORMAL')
                ON CONFLICT (sku) DO UPDATE 
                SET id_fornecedor = EXCLUDED.id_fornecedor,
                    descricao = EXCLUDED.descricao,
                    prc_distribuidora = EXCLUDED.prc_distribuidora,
                    preco_venda = EXCLUDED.preco_venda,
                    status = 'NORMAL'
            ''', (id_forn_destino, sku, desc, custo, venda))
            importados += 1
        conn.commit()
        return importados, ""
    except Exception as e:
        conn.rollback()
        return 0, str(e)
    finally:
        cursor.close()
        conn.close()