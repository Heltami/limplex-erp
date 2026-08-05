import pandas as pd
from core.database import conectar_bd

def obter_dados_empresa():
    """Busca as configurações globais da empresa para cabeçalhos de PDF."""
    conn = conectar_bd()
    try:
        df = pd.read_sql_query("SELECT * FROM configuracoes LIMIT 1", conn)
        return df.iloc[0].to_dict() if not df.empty else {}
    finally:
        conn.close()

def listar_itens_pendentes_compra():
    """Agrupa todos os pedidos validados e calcula quanto precisamos comprar de cada fornecedor."""
    conn = conectar_bd()
    try:
        return pd.read_sql_query('''
            SELECT f.nome_fantasia as "Fornecedor", 
                   p.sku as "Código", 
                   p.descricao as "Produto", 
                   SUM(i.quantidade) as "Qtd Total", 
                   i.custo_unitario as "Custo Unitário", 
                   SUM(i.subtotal_custo) as "Custo Total" 
            FROM itens_pedido i 
            JOIN pedidos ped ON i.pedido_id = ped.id 
            JOIN produtos p ON i.produto_id = p.id_produto 
            LEFT JOIN fornecedores f ON p.id_fornecedor = f.id_fornecedor 
            WHERE ped.status = 'Pedido' 
            GROUP BY f.nome_fantasia, p.sku, p.descricao, i.custo_unitario
            ORDER BY f.nome_fantasia, p.descricao
        ''', conn)
    finally:
        conn.close()

def consolidar_pedidos_pendentes():
    """Avança todos os 'Pedidos' para 'Consolidado' e grava a hora exata da consolidação."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE pedidos SET status = 'Consolidado', data_consolidado = CURRENT_TIMESTAMP WHERE status = 'Pedido'")
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def listar_pedidos_consolidados():
    """Puxa os dados dos clientes cujos pedidos estão no Lote Logístico atual."""
    conn = conectar_bd()
    try:
        return pd.read_sql_query('''
            SELECT p.id as id_pedido, 
                   p.cliente_id as ped_cliente_id, 
                   p.data_criacao, 
                   p.valor_total as valor_pedido, 
                   c.*
            FROM pedidos p 
            JOIN clientes c ON p.cliente_id = c.id_cliente 
            WHERE p.status = 'Consolidado' 
            ORDER BY c.id_cliente
        ''', conn)
    finally:
        conn.close()

def listar_picking_consolidados():
    """Gera a lista de separação de estoque (Picking) por cliente."""
    conn = conectar_bd()
    try:
        return pd.read_sql_query('''
            SELECT c.razao_social as "Cliente", p.id as id_pedido, p.cliente_id, p.data_criacao, pr.descricao as "Produto", i.quantidade as "Qtd"
            FROM itens_pedido i 
            JOIN pedidos p ON i.pedido_id = p.id 
            JOIN produtos pr ON i.produto_id = pr.id_produto 
            JOIN clientes c ON p.cliente_id = c.id_cliente
            WHERE p.status = 'Consolidado' 
            ORDER BY c.razao_social, pr.descricao
        ''', conn)
    finally:
        conn.close()

def reverter_lote_consolidado():
    """Em caso de erro logístico, devolve os 'Consolidados' para 'Pedido'."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE pedidos SET status = 'Pedido' WHERE status = 'Consolidado'")
        conn.commit()
        return True, ""
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()