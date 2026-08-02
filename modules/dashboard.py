import streamlit as st
import pandas as pd
import plotly.express as px
from core.database import conectar_bd

def render():
    st.title("📊 Painel Administrativo")
    st.write("A sua sala de controlo. Visão geral da operação B2B e da lucratividade real do negócio.")
    
    conn = conectar_bd()
    total_clientes = pd.read_sql_query("SELECT COUNT(*) as count FROM clientes", conn).iloc[0]['count']
    total_produtos = pd.read_sql_query("SELECT COUNT(*) as count FROM produtos", conn).iloc[0]['count']
    
    # Contar fornecedores de forma segura (caso a tabela se chame 'fornecedores')
    try:
        total_fornecedores = pd.read_sql_query("SELECT COUNT(*) as count FROM fornecedores", conn).iloc[0]['count']
    except:
        total_fornecedores = 0
    
    # Puxar pedidos e itens associados (SUAS CONSULTAS ORIGINAIS)
    df_pedidos = pd.read_sql_query("SELECT id, nome_cliente, data_criacao, status, valor_total, custo_total, lucro_estimado FROM pedidos ORDER BY id DESC", conn)
    df_itens = pd.read_sql_query("""
        SELECT i.nome_produto, i.quantidade, i.subtotal_venda 
        FROM itens_pedido i 
        JOIN pedidos p ON i.pedido_id = p.id
    """, conn)
    
    # --- NOVAS CONSULTAS SEGURAS PARA OS NOVOS GRÁFICOS ---
    try:
        df_top_margem = pd.read_sql_query("""
            SELECT descricao, margem_lucro 
            FROM produtos 
            WHERE status != 'INATIVO' AND margem_lucro IS NOT NULL 
            ORDER BY margem_lucro DESC LIMIT 10
        """, conn)
    except:
        df_top_margem = pd.DataFrame()

    try:
        df_top_lucro = pd.read_sql_query("""
            SELECT descricao, lucro_reais 
            FROM produtos 
            WHERE status != 'INATIVO' AND lucro_reais IS NOT NULL 
            ORDER BY lucro_reais DESC LIMIT 10
        """, conn)
    except:
        df_top_lucro = pd.DataFrame()

    try:
        df_forn_vendas = pd.read_sql_query("""
            SELECT f.nome_fantasia as fornecedor, SUM(i.subtotal_venda) as total_vendas
            FROM itens_pedido i
            JOIN produtos pr ON i.nome_produto = pr.descricao
            JOIN fornecedores f ON pr.id_fornecedor = f.id_fornecedor
            GROUP BY f.nome_fantasia
            ORDER BY total_vendas DESC LIMIT 10
        """, conn)
    except:
        df_forn_vendas = pd.DataFrame()

    conn.close()
    
    if df_pedidos.empty:
        st.info("💡 Ainda não existem dados para gerar os gráficos financeiros. Crie alguns pedidos no Módulo de Pedidos primeiro!")
        col1, col2, col3 = st.columns(3)
        col1.metric("Clientes Registados", total_clientes)
        col2.metric("Produtos no Catálogo", total_produtos)
        col3.metric("Fornecedores Parceiros", total_fornecedores)
    else:
        faturamento_total = df_pedidos['valor_total'].sum()
        custo_total_geral = df_pedidos['custo_total'].sum()
        lucro_total = df_pedidos['lucro_estimado'].sum()
        
        # --- SEU RESUMO FINANCEIRO ORIGINAL ---
        st.markdown("### 💰 Resumo Financeiro Global (Todos os Pedidos)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Faturamento Bruto", f"R$ {faturamento_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col2.metric("Custo Total Fornecedor", f"R$ {custo_total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col3.metric("Lucro Bruto Estimado", f"R$ {lucro_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        st.write("") 
        # Segunda linha de métricas operacionais
        col4, col5, col6, col7 = st.columns(4)
        col4.metric("Clientes Ativos", total_clientes)
        col5.metric("Produtos Disponíveis", total_produtos)
        col6.metric("Fornecedores", total_fornecedores)
        col7.metric("Total de Pedidos", len(df_pedidos))
        
        st.markdown("---")
        # --- LINHA 1: SEUS GRÁFICOS ORIGINAIS ---
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Estado dos Pedidos Logísticos")
            fig_status = px.pie(df_pedidos, names='status', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_status, use_container_width=True)
            
        with col_graf2:
            st.subheader("Top 5 Produtos Mais Vendidos")
            if not df_itens.empty:
                top_produtos = df_itens.groupby('nome_produto')['quantidade'].sum().reset_index().sort_values(by='quantidade', ascending=False).head(5)
                fig_top = px.bar(top_produtos, x='quantidade', y='nome_produto', orientation='h', color='quantidade', color_continuous_scale='Blues')
                fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Unidades Vendidas", yaxis_title="")
                st.plotly_chart(fig_top, use_container_width=True)
            else:
                st.write("Sem dados de produtos suficientes nos pedidos.")

        # --- LINHA 2: NOVOS GRÁFICOS DE PRODUTOS (MARGEM % E LUCRO REAL R$) ---
        st.markdown("---")
        col_graf3, col_graf4 = st.columns(2)
        
        with col_graf3:
            st.subheader("Top 10 Produtos Mais Rentáveis (%)")
            if not df_top_margem.empty:
                fig_margem = px.bar(df_top_margem, x='margem_lucro', y='descricao', orientation='h', color='margem_lucro', color_continuous_scale='Greens')
                fig_margem.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Margem (%)", yaxis_title="")
                st.plotly_chart(fig_margem, use_container_width=True)
            else:
                st.write("Sem dados de margem cadastrados nos produtos.")

        with col_graf4:
            st.subheader("Top 10 Produtos com Maior Lucro Real (R$)")
            if not df_top_lucro.empty:
                fig_lucro_real = px.bar(df_top_lucro, x='lucro_reais', y='descricao', orientation='h', color='lucro_reais', color_continuous_scale='emrld')
                fig_lucro_real.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Lucro Real (R$)", yaxis_title="")
                st.plotly_chart(fig_lucro_real, use_container_width=True)
            else:
                st.write("Sem dados de lucro real cadastrados nos produtos.")

        # --- LINHA 3: NOVOS GRÁFICOS DE PARCEIROS (CLIENTES E FORNECEDORES) ---
        st.markdown("---")
        col_graf5, col_graf6 = st.columns(2)

        with col_graf5:
            st.subheader("Clientes por Valor Real de Compra")
            if 'nome_cliente' in df_pedidos.columns and 'valor_total' in df_pedidos.columns and not df_pedidos.empty:
                top_clientes = df_pedidos.groupby('nome_cliente')['valor_total'].sum().reset_index().sort_values(by='valor_total', ascending=False).head(10)
                fig_clientes = px.bar(top_clientes, x='valor_total', y='nome_cliente', orientation='h', color='valor_total', color_continuous_scale='Purples')
                fig_clientes.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Comprado (R$)", yaxis_title="")
                st.plotly_chart(fig_clientes, use_container_width=True)
            else:
                st.write("Sem dados de clientes nos pedidos.")

        with col_graf6:
            st.subheader("Fornecedores por Valor Real de Venda")
            if not df_forn_vendas.empty:
                fig_forn = px.bar(df_forn_vendas, x='total_vendas', y='fornecedor', orientation='h', color='total_vendas', color_continuous_scale='Sunset')
                fig_forn.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Vendido (R$)", yaxis_title="")
                st.plotly_chart(fig_forn, use_container_width=True)
            else:
                st.write("Sem dados de vendas associadas a fornecedores.")