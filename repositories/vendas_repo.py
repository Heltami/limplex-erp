import pandas as pd
from core.database import conectar_bd

def listar_clientes_combo():
    """Busca clientes para o selectbox."""
    conn = conectar_bd()
    try:
        return pd.read_sql_query("SELECT id_cliente, razao_social FROM clientes ORDER BY razao_social", conn)
    finally:
        conn.close()

def listar_produtos_combo():
    """Busca produtos disponíveis para o selectbox."""
    conn = conectar_bd()
    try:
        return pd.read_sql_query('''
            SELECT p.id_produto, p.descricao, p.preco_venda, p.prc_distribuidora, p.sku, f.nome_fantasia as fornecedor
            FROM produtos p
            LEFT JOIN fornecedores f ON p.id_fornecedor = f.id_fornecedor
            WHERE p.status != 'INATIVO' 
            ORDER BY p.descricao
        ''', conn)
    finally:
        conn.close()

def salvar_orcamento(cliente_id, nome_cliente, total_venda, total_custo, lucro_est, itens_carrinho, editando_id=None):
    """Guarda o Orçamento e faz o SNAPSHOT IMUTÁVEL."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        if editando_id:
            cursor.execute('''
                UPDATE pedidos 
                SET valor_total=%s, custo_total=%s, lucro_estimado=%s 
                WHERE id=%s
            ''', (total_venda, total_custo, lucro_est, editando_id))
            cursor.execute("DELETE FROM itens_pedido WHERE pedido_id=%s", (editando_id,))
            pedido_id = editando_id
        else:
            cursor.execute('''
                INSERT INTO pedidos (cliente_id, nome_cliente, status, valor_total, custo_total, lucro_estimado, observacoes)
                VALUES (%s, %s, 'Orçamento', %s, %s, %s, '') RETURNING id
            ''', (cliente_id, nome_cliente, total_venda, total_custo, lucro_est))
            pedido_id = cursor.fetchone()[0]

        for item in itens_carrinho:
            cursor.execute('''
                INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, quantidade, preco_unitario, custo_unitario, subtotal_venda, subtotal_custo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                pedido_id, item['produto_id'], item['nome_produto'], 
                item['quantidade'], item['preco_unitario'], item['custo_unitario'], 
                item['subtotal_venda'], item['subtotal_custo']
            ))
            
        conn.commit()
        return True, pedido_id, ""
    except Exception as e:
        conn.rollback()
        return False, None, str(e)
    finally:
        cursor.close()
        conn.close()

def listar_pedidos(busca=""):
    """Gera a tabela principal de documentos."""
    conn = conectar_bd()
    try:
        query = """
            SELECT p.id as id_pedido, c.id_cliente, c.razao_social as cliente, 
                   p.data_criacao, p.status, p.valor_total, p.lucro_estimado 
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id_cliente
            ORDER BY p.id DESC
        """
        df = pd.read_sql_query(query, conn)
        
        if busca and not df.empty:
            if any(op in busca for op in ['>', '<', '==', '!=']):
                try: df = df.query(busca)
                except: pass
            else:
                mask = df.astype(str).apply(lambda x: x.str.contains(busca, case=False, na=False)).any(axis=1)
                df = df[mask]
        return df
    finally:
        conn.close()

def obter_itens_pedido(pedido_id):
    """Busca o snapshot dos itens para PDFs e edição."""
    conn = conectar_bd()
    try:
        return pd.read_sql_query('''
            SELECT p.sku, i.nome_produto, i.quantidade, i.preco_unitario, i.subtotal_venda, 
                   i.produto_id, i.custo_unitario, i.subtotal_custo
            FROM itens_pedido i
            LEFT JOIN produtos p ON i.produto_id = p.id_produto
            WHERE i.pedido_id = %s
        ''', conn, params=(int(pedido_id),))
    finally:
        conn.close()

def excluir_pedido(pedido_id):
    """Elimina um orçamento/pedido permanentemente."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM pedidos WHERE id = %s", (int(pedido_id),))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

# =========================================================================
# NOVAS FUNÇÕES: GESTÃO DE DATAS, CARIMBOS DE TEMPO E PREVISÃO DE ENTREGA
# =========================================================================

def garantir_colunas_vendas():
    """Garante que as colunas de histórico de datas existem na tabela de pedidos."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data_pedido TIMESTAMP")
        cursor.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data_consolidado TIMESTAMP")
        cursor.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data_faturado TIMESTAMP")
        cursor.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data_entregue TIMESTAMP")
        # --- COLUNA NOVA: PREVISÃO DE ENTREGA ---
        cursor.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data_previsao_entrega DATE")
        conn.commit()
    except:
        pass
    finally:
        cursor.close()
        conn.close()

def obter_datas_pedido(pedido_id):
    """Busca os carimbos de tempo e a previsão de entrega do pedido."""
    conn = conectar_bd()
    try:
        df = pd.read_sql_query("SELECT data_criacao, data_pedido, data_consolidado, data_faturado, data_entregue, data_previsao_entrega FROM pedidos WHERE id = %s", conn, params=(int(pedido_id),))
        return df.iloc[0].to_dict() if not df.empty else {}
    finally:
        conn.close()

def alterar_status_pedido(pedido_id, novo_status, data_previsao=None):
    """Muda a fase do pedido na Régua de Status e grava a hora exata e a previsão."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        coluna_data = ""
        params = [novo_status]

        if novo_status == 'Pedido': 
            coluna_data = ", data_pedido = CURRENT_TIMESTAMP"
            # Se for aprovação e tivermos uma previsão, guardamo-la também
            if data_previsao:
                coluna_data += ", data_previsao_entrega = %s"
                params.append(data_previsao)
                
        elif novo_status == 'Consolidado': coluna_data = ", data_consolidado = CURRENT_TIMESTAMP"
        elif novo_status == 'Faturado': coluna_data = ", data_faturado = CURRENT_TIMESTAMP"
        elif novo_status == 'Entregue': coluna_data = ", data_entregue = CURRENT_TIMESTAMP"

        params.append(int(pedido_id))
        
        cursor.execute(f"UPDATE pedidos SET status = %s {coluna_data} WHERE id = %s", tuple(params))
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()
        
def obter_dados_sla_entregas():
    """Busca os pedidos em andamento com suas datas de previsão para o painel de SLA do Dashboard."""
    conn = conectar_bd()
    try:
        # Trazemos pedidos que já foram validados mas ainda não foram entregues
        return pd.read_sql_query('''
            SELECT p.id, c.razao_social as cliente, p.valor_total, p.status, p.data_previsao_entrega 
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id_cliente
            WHERE p.status NOT IN ('Rascunho', 'Orçamento', 'Entregue') 
              AND p.data_previsao_entrega IS NOT NULL
        ''', conn)
    finally:
        conn.close()