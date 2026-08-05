import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from core.database import conectar_bd
from repositories import vendas_repo

def render():
    st.title("📊 Painel Administrativo")
    st.write("A sua sala de controlo. Visão geral da operação B2B e da lucratividade real do negócio.")
    
    conn = conectar_bd()
    total_clientes = pd.read_sql_query("SELECT COUNT(*) as count FROM clientes", conn).iloc[0]['count']
    total_produtos = pd.read_sql_query("SELECT COUNT(*) as count FROM produtos", conn).iloc[0]['count']
    
    # Contar fornecedores de forma segura
    try:
        total_fornecedores = pd.read_sql_query("SELECT COUNT(*) as count FROM fornecedores", conn).iloc[0]['count']
    except:
        total_fornecedores = 0
    
    # Puxar pedidos e itens associados
    df_pedidos = pd.read_sql_query("SELECT id, nome_cliente, data_criacao, status, valor_total, custo_total, lucro_estimado FROM pedidos ORDER BY id DESC", conn)
    df_itens = pd.read_sql_query("""
        SELECT i.nome_produto, i.quantidade, i.subtotal_venda 
        FROM itens_pedido i 
        JOIN pedidos p ON i.pedido_id = p.id
    """, conn)
    
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
        
        # --- RESUMO FINANCEIRO GLOBAL ---
        st.markdown("### 💰 Resumo Financeiro Global (Todos os Pedidos)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Faturamento Bruto", f"R$ {faturamento_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col2.metric("Custo Total Fornecedor", f"R$ {custo_total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col3.metric("Lucro Bruto Estimado", f"R$ {lucro_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        st.write("") 
        col4, col5, col6, col7 = st.columns(4)
        col4.metric("Clientes Ativos", total_clientes)
        col5.metric("Produtos Disponíveis", total_produtos)
        col6.metric("Fornecedores", total_fornecedores)
        col7.metric("Total de Pedidos", len(df_pedidos))
        
        st.markdown("---")
        
        # ==========================================
        # MÓDULO LOGÍSTICO: SLA DE ENTREGAS
        # ==========================================
        st.subheader("🚚 SLA de Entregas (Prazos Acordados)")
        
        df_sla = vendas_repo.obter_dados_sla_entregas()
        
        if df_sla.empty:
            st.success("🎉 Todos os pedidos já foram entregues ou não existem pedidos pendentes de entrega no momento.")
        else:
            hoje = datetime.now().date()
            limite_5_dias = hoje + timedelta(days=5)
            
            # --- IDENTIFICAÇÃO DA PRÓXIMA ENTREGA ---
            df_sla['data_dt'] = pd.to_datetime(df_sla['data_previsao_entrega']).dt.date
            df_futuras = df_sla[df_sla['data_dt'] >= hoje].sort_values('data_dt')
            
            if not df_futuras.empty:
                prox_pedido = df_futuras.iloc[0]
                data_prox_str = prox_pedido['data_dt'].strftime('%d/%m/%Y')
                cliente_prox = prox_pedido['cliente']
            else:
                # Caso haja apenas entregas em atraso
                df_atrasados = df_sla.sort_values('data_dt')
                prox_pedido = df_atrasados.iloc[0]
                data_prox_str = prox_pedido['data_dt'].strftime('%d/%m/%Y')
                cliente_prox = f"{prox_pedido['cliente']} (Atrasado)"

            def classificar_sla(data_val):
                try:
                    d = pd.to_datetime(data_val).date()
                    if d < hoje: return "EM ATRASO"
                    elif hoje <= d <= limite_5_dias: return "EM ENTREGA (Próx. 5 dias)"
                    else: return "EM DIAS (> 5 dias)"
                except:
                    return "Sem Previsão"
                    
            df_sla["Status SLA"] = df_sla["data_previsao_entrega"].apply(classificar_sla)
            
            cores_map = {
                "EM DIAS (> 5 dias)": "#28a745",
                "EM ENTREGA (Próx. 5 dias)": "#ffc107",
                "EM ATRASO": "#d9534f",
                "Sem Previsão": "#888888"
            }
            
            # Destaque com o indicador da Próxima Entrega
            st.metric("🗓️ Próxima Entrega Agendada", data_prox_str, f"🏢 Cliente: {cliente_prox}")
            st.write("")
            
            c_lista, c_grafico = st.columns([1.5, 1.5])
            
            with c_grafico:
                contagem_sla = df_sla["Status SLA"].value_counts().reset_index()
                contagem_sla.columns = ["Status SLA", "Quantidade"]
                
                fig_sla = px.pie(
                    contagem_sla,
                    names="Status SLA",
                    values="Quantidade",
                    color="Status SLA",
                    color_discrete_map=cores_map,
                    hole=0.55,
                    title="Saúde das Entregas Pendentes"
                )
                fig_sla.update_traces(textposition='inside', textinfo='percent+label')
                
                # DATA DA PRÓXIMA ENTREGA EXIBIDA NO CENTRO DO DONUT
                fig_sla.add_annotation(
                    text=f"<b>Próxima:</b><br>{data_prox_str}",
                    x=0.5, y=0.5,
                    font_size=13,
                    font_color="#0f4c81",
                    showarrow=False
                )
                
                fig_sla.update_layout(margin=dict(t=40, b=0, l=0, r=0), showlegend=False)
                st.plotly_chart(fig_sla, use_container_width=True)
                
            with c_lista:
                st.markdown("**📋 Pedidos a Requerer Atenção:**")
                ordem_prioridade = {"EM ATRASO": 1, "EM ENTREGA (Próx. 5 dias)": 2, "EM DIAS (> 5 dias)": 3, "Sem Previsão": 4}
                df_sla['Prioridade'] = df_sla['Status SLA'].map(ordem_prioridade)
                df_lista = df_sla.sort_values('Prioridade')
                df_lista['Previsão'] = pd.to_datetime(df_lista['data_previsao_entrega']).dt.strftime('%d/%m/%Y')
                st.dataframe(df_lista[['id', 'cliente', 'Previsão', 'Status SLA']].set_index('id'), use_container_width=True, height=350)

        st.markdown("---")

        # --- LINHA 1: GRÁFICOS ORIGINAIS ---
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

        # --- LINHA 2: GRÁFICOS DE PRODUTOS ---
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

        # --- LINHA 3: GRÁFICOS DE PARCEIROS ---
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