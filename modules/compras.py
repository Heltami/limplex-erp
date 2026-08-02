import streamlit as st
import pandas as pd
import time
from datetime import datetime

from core.database import conectar_bd
from core.utils import registrar_auditoria
from core.pdf_generator import (
    gerar_pdf_pedido_mestre, gerar_pdf_pedido_fornecedor, gerar_pdf_pickup_entrega
)

def render():
    st.title("📦 Central de Compras e Logística")
    st.markdown("Reúna todas as vendas confirmadas (Fase: **Pedido**) para gerar as **Ordens de Compra** aos Fornecedores e organizar a logística de entrega.")
    
    conn_global = conectar_bd()
    try:
        df_empresa = pd.read_sql_query("SELECT * FROM configuracoes LIMIT 1", conn_global)
        empresa_dados = df_empresa.iloc[0].to_dict() if not df_empresa.empty else {}
    except:
        empresa_dados = {}
    conn_global.close()

    aba_cons1, aba_cons2 = st.tabs(["⏳ 1. Compras Pendentes (A Consolidar)", "🚚 2. Logística Operacional (Lote Consolidado)"])

    # ==========================================
    # ABA 1: ITENS PENDENTES DE PEDIDO AO FORNECEDOR
    # ==========================================
    with aba_cons1:
        st.subheader("Itens Pendentes de Compra (Baseado nas Vendas)")
        
        conn = conectar_bd()
        df_cons = pd.read_sql_query('''
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
        conn.close()
        
        if df_cons.empty:
            st.info("ℹ️ Nenhum item pendente. Altere o status dos orçamentos para 'Pedido' no Módulo de Pedidos.")
        else:
            st.dataframe(
                df_cons.style.format({"Custo Unitário": "R$ {:.2f}", "Custo Total": "R$ {:.2f}"}), 
                use_container_width=True
            )
            
            custo_lote = float(df_cons["Custo Total"].sum())
            st.markdown(f"### Custo Estimado Deste Lote: **R$ {custo_lote:,.2f}**".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
            st.markdown("### 📥 Ações e Emissão de Documentos")
            
            c_mestre, c_indiv, c_fecho = st.columns([1, 1.5, 1])
            
            with c_mestre:
                st.markdown("**1. Resumo Interno**")
                pdf_mestre = gerar_pdf_pedido_mestre(
                    df_cons=df_cons,
                    empresa_info=empresa_dados,
                    usuario_emissao=st.session_state.get('usuario_logado', 'Sistema')
                )
                st.download_button(
                    label="📄 Pedido Mestre (Todos)",
                    data=pdf_mestre,
                    file_name=f"pedido_mestre_global_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    help="Documento interno contendo a soma de todos os fornecedores."
                )
                
            with c_indiv:
                st.markdown("**2. Enviar ao Fornecedor**")
                fornecedores_unicos = df_cons['Fornecedor'].fillna("SEM FORNECEDOR DEFINIDO").unique().tolist()
                
                forn_selecionado = st.selectbox("Escolha o Fornecedor:", fornecedores_unicos, label_visibility="collapsed")
                
                if forn_selecionado:
                    df_forn_especifico = df_cons[df_cons['Fornecedor'].fillna("SEM FORNECEDOR DEFINIDO") == forn_selecionado]
                    pdf_fornecedor = gerar_pdf_pedido_fornecedor(
                        fornecedor_nome=forn_selecionado, 
                        df_forn=df_forn_especifico, 
                        empresa_info=empresa_dados, 
                        usuario_emissao=st.session_state.get('usuario_logado', 'Sistema')
                    )
                    
                    nome_ficheiro_forn = str(forn_selecionado).replace(" ", "_").lower()
                    st.download_button(
                        label=f"📄 Gerar Ordem: {forn_selecionado}",
                        data=pdf_fornecedor,
                        file_name=f"ordem_compra_{nome_ficheiro_forn}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary"
                    )
                
            with c_fecho:
                st.markdown("**3. Fechamento Mensal**")
                with st.popover("🚀 Consolidar Lote Operacional", use_container_width=True):
                    st.markdown("⚠️ **Atenção:** Ao confirmar, todos os 'Pedidos' passarão para o status **Consolidado**.")
                    if st.button("✔️ Sim, Fechar e Consolidar", use_container_width=True):
                        conn = conectar_bd()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE pedidos SET status = 'Consolidado' WHERE status = 'Pedido'")
                        conn.commit()
                        registrar_auditoria(st.session_state.usuario_logado, "Fechou o lote e consolidou todos os Pedidos.")
                        conn.close()
                        st.success("✅ Lote consolidado! Avance para a Aba 2.")
                        time.sleep(1.5); st.rerun()

    # ==========================================
    # ABA 2: LOGÍSTICA E ROTEIRIZAÇÃO (CONSOLIDADOS)
    # ==========================================
    with aba_cons2:
        st.subheader("Painel de Roteirização e Entregas (Lote Atual)")
        
        conn = conectar_bd()
        
        # Puxa os dados dos pedidos consolidados cruzando com a tabela de clientes
        df_peds_cons = pd.read_sql_query('''
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
        
        romaneio_lista = []
        for _, row in df_peds_cons.iterrows():
            pid = row['id_pedido']
            cli_id = row['ped_cliente_id']
            data_compacta = str(row['data_criacao'])[:10].replace("-", "")
            doc_formatado = f"CON{int(cli_id):03d}{data_compacta}{int(pid):03d}"

            # 1. Função auxiliar flexível para encontrar colunas com nomes variados
            def pegar_campo(*opcoes):
                for op in opcoes:
                    if op in row.index and pd.notna(row[op]) and str(row[op]).strip():
                        return str(row[op]).strip()
                return ""

            # 2. Montagem do Endereço Completo do Cliente
            rua_val = pegar_campo('endereco', 'rua', 'logradouro', 'morada')
            num_val = pegar_campo('numero', 'num', 'nº')
            bairro_val = pegar_campo('bairro', 'distrito')
            cid_val = pegar_campo('cidade', 'localidade', 'municipio')
            est_val = pegar_campo('estado', 'uf')

            partes_end = []
            if rua_val: partes_end.append(rua_val)
            if num_val: partes_end.append(f"Nº {num_val}")
            if bairro_val: partes_end.append(bairro_val)
            if cid_val and est_val:
                partes_end.append(f"{cid_val}/{est_val}")
            elif cid_val:
                partes_end.append(cid_val)

            end_final = ", ".join(partes_end) if partes_end else "Endereço não informado"

            # 3. Informações de Contato Completas (Nome, Cargo, Telefone, WhatsApp e E-mail)
            contato_linhas = []
            
            nome_ct = pegar_campo('contato', 'responsavel', 'nome_contato', 'pessoa_contato', 'nome', 'responsavel_nome')
            if nome_ct: contato_linhas.append(f"<b>Nome:</b> {nome_ct}")

            cargo_ct = pegar_campo('cargo', 'funcao', 'papel')
            if cargo_ct: contato_linhas.append(f"<b>Cargo:</b> {cargo_ct}")

            tel_ct = pegar_campo('telefone', 'tel', 'fone')
            if tel_ct: contato_linhas.append(f"<b>Tel:</b> {tel_ct}")

            wpp_ct = pegar_campo('whatsapp', 'celular', 'cel', 'wpp')
            if wpp_ct: contato_linhas.append(f"<b>WhatsApp:</b> {wpp_ct}")

            email_ct = pegar_campo('email', 'e-mail', 'correio')
            if email_ct: contato_linhas.append(f"<b>E-mail:</b> {email_ct}")

            info_contato_final = "<br/>".join(contato_linhas) if contato_linhas else "Não informado"

            # 4. Distância e Tempo
            dist_val = pegar_campo('distancia_km', 'distancia', 'dist_km', 'km')
            if not dist_val: dist_val = "N/D"
            elif not dist_val.endswith("km"): dist_val += " km"

            tempo_val = pegar_campo('tempo_minutos', 'tempo_min', 'tempo', 'minutos', 'duracao')
            if not tempo_val: tempo_val = "N/D"
            elif not tempo_val.endswith("min"): tempo_val += " min"

            nome_cliente = pegar_campo('razao_social', 'nome_fantasia', 'nome', 'empresa')
            if not nome_cliente: nome_cliente = "Cliente N/D"

            romaneio_lista.append({
                "ID Pedido": doc_formatado,
                "Cliente": nome_cliente,
                "Endereço de Entrega": end_final,
                "Contato Info": info_contato_final,
                "Distância": dist_val,
                "Tempo": tempo_val,
                "Valor a Receber": float(row["valor_pedido"]) if pd.notna(row["valor_pedido"]) else 0.0
            })
            
        df_romaneio = pd.DataFrame(romaneio_lista)
        
        # Puxa os dados para o Picking de forma limpa
        df_picking_raw = pd.read_sql_query('''
            SELECT c.razao_social as "Cliente", p.id as id_pedido, p.cliente_id, p.data_criacao, pr.descricao as "Produto", i.quantidade as "Qtd"
            FROM itens_pedido i 
            JOIN pedidos p ON i.pedido_id = p.id 
            JOIN produtos pr ON i.produto_id = pr.id_produto 
            JOIN clientes c ON p.cliente_id = c.id_cliente
            WHERE p.status = 'Consolidado' 
            ORDER BY c.razao_social, pr.descricao
        ''', conn)
        conn.close()

        picking_lista = []
        for _, row in df_picking_raw.iterrows():
            pid = row['id_pedido']
            cli_id = row['cliente_id']
            data_compacta = str(row['data_criacao'])[:10].replace("-", "")
            doc_formatado = f"CON{int(cli_id):03d}{data_compacta}{int(pid):03d}"
            
            picking_lista.append({
                "Cliente": row["Cliente"],
                "Nº Pedido": doc_formatado,
                "Produto": row["Produto"],
                "Qtd": row["Qtd"]
            })
            
        df_picking = pd.DataFrame(picking_lista)
        
        if df_romaneio.empty:
            st.info("ℹ️ Nenhum pedido no status 'Consolidado'. Certifique-se de avançar o lote na Aba 1 (clicando em Consolidar Lote) para que os pedidos apareçam aqui.")
        else:
            st.markdown("**📄 Documento Unificado: Separação (Picking) e Entrega**")
            st.caption("Um único documento contendo os dados de roteirização e os itens a separar por cliente.")
            
            pdf_unificado = gerar_pdf_pickup_entrega(
                df_romaneio=df_romaneio, 
                df_picking=df_picking, 
                empresa_info=empresa_dados, 
                usuario_emissao=st.session_state.get('usuario_logado', 'Sistema')
            )
            
            st.download_button(
                label="🚚 Baixar Documento de Separação e Entrega (PDF)", 
                data=pdf_unificado, 
                file_name=f"separacao_entrega_{datetime.now().strftime('%Y%m%d')}.pdf", 
                mime="application/pdf", 
                use_container_width=True, 
                type="primary"
            )
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Resumo das Entregas (Rota)**")
                st.dataframe(df_romaneio.style.format({"Valor a Receber": "R$ {:.2f}"}), use_container_width=True, height=200)
            with c2:
                st.markdown("**Resumo de Produtos (Estoque)**")
                st.dataframe(df_picking, use_container_width=True, height=200)
                
            st.markdown("---")
            with st.popover("⏪ Reabrir Lote Consolidado", use_container_width=False):
                st.markdown("Isto irá devolver todos os registos Consolidados para a fase de **Pedido**.")
                if st.button("✔️ Sim, Reverter Lote Inteiro", type="primary"):
                    conn = conectar_bd()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE pedidos SET status = 'Pedido' WHERE status = 'Consolidado'")
                    conn.commit()
                    registrar_auditoria(st.session_state.usuario_logado, "Reverteu o lote Consolidado para Pedido.")
                    conn.close()
                    st.success("✅ Lote revertido com sucesso! Volte à Aba 1.")
                    time.sleep(1.5); st.rerun()