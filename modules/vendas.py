import streamlit as st
import pandas as pd
import time
from datetime import datetime

from core.database import conectar_bd
from core.utils import registrar_auditoria
from core.pdf_generator import gerar_pdf_pedido
from repositories import vendas_repo

def render():
    st.title("🛒 Painel de Vendas (Orçamentos e Pedidos)")
    st.markdown("Crie propostas comerciais. Após aprovação, elas convertem-se em **Pedidos Imutáveis** e avançam na Linha do Tempo Logística e Financeira.")
    
    vendas_repo.garantir_colunas_vendas()
    
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []

    editando_id = st.session_state.get('editando_pedido_id', None)

    conn_global = conectar_bd()
    try:
        df_empresa = pd.read_sql_query("SELECT * FROM configuracoes LIMIT 1", conn_global)
        empresa_dados = df_empresa.iloc[0].to_dict() if not df_empresa.empty else {}
    except:
        empresa_dados = {}
    conn_global.close()

    # ==========================================
    # PARTE SUPERIOR: ÁREA DE TRABALHO (CARRINHO)
    # ==========================================
    st.markdown("<div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
    
    if editando_id:
        st.subheader(f"✏️ Editando Orçamento #{editando_id}")
    else:
        st.subheader("📝 Criar Novo Orçamento")

    df_clientes = vendas_repo.listar_clientes_combo()
    df_produtos = vendas_repo.listar_produtos_combo()

    if df_clientes.empty or df_produtos.empty:
        st.warning("⚠️ Precisa de ter pelo menos 1 Cliente e 1 Produto registados para criar orçamentos.")
    else:
        cliente_opcoes = dict(zip(df_clientes['id_cliente'], df_clientes['razao_social']))
        edit_cli_id = st.session_state.get('editando_cliente_id', None)
        idx_cli = list(cliente_opcoes.keys()).index(edit_cli_id) if edit_cli_id and edit_cli_id in cliente_opcoes else 0
        
        cliente_selecionado_id = st.selectbox(
            "👤 Selecione o Cliente:", 
            options=list(cliente_opcoes.keys()), 
            format_func=lambda x: cliente_opcoes[x], 
            index=idx_cli,
            disabled=bool(editando_id)
        )

        st.markdown("---")

        with st.form("form_add_item", clear_on_submit=True):
            c1, c2, c3 = st.columns([4.5, 0.7, 1.1])
            produto_opcoes = {}
            for _, p_row in df_produtos.iterrows():
                p_id = p_row['id_produto']
                p_desc = str(p_row.get('descricao', 'N/D'))
                p_preco = float(p_row.get('preco_venda') or 0.0)
                p_forn = str(p_row.get('fornecedor', 'N/D'))
                if p_forn.lower() == 'nan': p_forn = 'N/D'
                produto_opcoes[p_id] = f"R$ {p_preco:.2f} | {p_desc} | Forn: {p_forn}"
            
            produto_selecionado_id = c1.selectbox("Adicionar Produto:", options=list(produto_opcoes.keys()), format_func=lambda x: produto_opcoes[x])
            quantidade = c2.number_input("Qtd", min_value=1, value=1)

            with c3:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                submit_adicionar = st.form_submit_button("➕ Adicionar", use_container_width=True)

            if submit_adicionar:
                prod_info = df_produtos[df_produtos['id_produto'] == produto_selecionado_id].iloc[0]
                preco_unit = float(prod_info['preco_venda'] or 0)
                custo_unit = float(prod_info['prc_distribuidora'] or 0)
                produto_existente = next((item for item in st.session_state.carrinho if item['produto_id'] == int(produto_selecionado_id)), None)
                
                if produto_existente:
                    produto_existente['quantidade'] += int(quantidade)
                    produto_existente['subtotal_venda'] = produto_existente['quantidade'] * produto_existente['preco_unitario']
                    produto_existente['subtotal_custo'] = produto_existente['quantidade'] * produto_existente['custo_unitario']
                else:
                    st.session_state.carrinho.append({
                        'produto_id': int(produto_selecionado_id),
                        'nome_produto': str(prod_info['descricao']),
                        'sku': str(prod_info.get('sku', 'N/D')),
                        'quantidade': int(quantidade),
                        'preco_unitario': preco_unit,
                        'custo_unitario': custo_unit,
                        'subtotal_venda': preco_unit * quantidade,
                        'subtotal_custo': custo_unit * quantidade
                    })
                st.rerun()

        if st.session_state.carrinho:
            st.markdown("<br>### 🛒 Resumo", unsafe_allow_html=True)
            for idx, item in enumerate(st.session_state.carrinho):
                ci1, ci2, ci3, ci4, ci5 = st.columns([3, 1, 1.5, 1.5, 1.5])
                ci1.markdown(f"📦 {item['nome_produto']}")
                ci2.markdown(f"<b>{item['quantidade']}</b>", unsafe_allow_html=True)
                ci3.markdown(f"R$ {item['preco_unitario']:.2f}")
                ci4.markdown(f"<b>R$ {item['subtotal_venda']:.2f}</b>", unsafe_allow_html=True)
                
                b_menos, b_mais, b_del = ci5.columns(3)
                if b_menos.button("➖", key=f"menos_{idx}") and item['quantidade'] > 1:
                    st.session_state.carrinho[idx]['quantidade'] -= 1
                    st.session_state.carrinho[idx]['subtotal_venda'] = st.session_state.carrinho[idx]['quantidade'] * item['preco_unitario']
                    st.session_state.carrinho[idx]['subtotal_custo'] = st.session_state.carrinho[idx]['quantidade'] * item['custo_unitario']
                    st.rerun()
                if b_mais.button("➕", key=f"mais_{idx}"):
                    st.session_state.carrinho[idx]['quantidade'] += 1
                    st.session_state.carrinho[idx]['subtotal_venda'] = st.session_state.carrinho[idx]['quantidade'] * item['preco_unitario']
                    st.session_state.carrinho[idx]['subtotal_custo'] = st.session_state.carrinho[idx]['quantidade'] * item['custo_unitario']
                    st.rerun()
                if b_del.button("🗑️", key=f"del_{idx}"):
                    st.session_state.carrinho.pop(idx)
                    st.rerun()

            df_carrinho = pd.DataFrame(st.session_state.carrinho)
            total_venda = float(df_carrinho['subtotal_venda'].sum()) if not df_carrinho.empty else 0.0
            total_custo = float(df_carrinho['subtotal_custo'].sum()) if not df_carrinho.empty else 0.0
            lucro_estimado = total_venda - total_custo

            col_t1, col_t2, col_t3 = st.columns(3)
            col_t1.metric("Valor a Cobrar (R$)", f"{total_venda:.2f}")
            col_t2.metric("Custo Fornecedor (R$)", f"{total_custo:.2f}")
            col_t3.metric("Lucro Estimado (R$)", f"{lucro_estimado:.2f}")
            st.markdown("---")

            col_canc, col_salv, _ = st.columns([1.5, 1.5, 5])
            if col_canc.button("❌ Cancelar", use_container_width=True):
                st.session_state.pop('editando_pedido_id', None)
                st.session_state.pop('editando_cliente_id', None)
                st.session_state.carrinho = []
                st.rerun()

            if col_salv.button("💾 Salvar Orçamento", type="primary", use_container_width=True):
                nome_cliente = str(cliente_opcoes[int(cliente_selecionado_id)])
                sucesso, pid, msg = vendas_repo.salvar_orcamento(
                    cliente_selecionado_id, nome_cliente, total_venda, total_custo, 
                    lucro_estimado, st.session_state.carrinho, editando_id
                )
                if sucesso:
                    registrar_auditoria(st.session_state.usuario_logado, f"Salvou Orçamento/Pedido ID {pid}")
                    st.session_state.carrinho = []
                    st.session_state.pop('editando_pedido_id', None)
                    st.session_state.pop('editando_cliente_id', None)
                    st.success("✅ Documento guardado e blindado!")
                    time.sleep(1.2); st.rerun()
                else:
                    st.error(f"Erro ao salvar: {msg}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border: 2px solid #ddd; margin: 30px 0;'>", unsafe_allow_html=True)

    # ==========================================
    # PARTE INFERIOR: BASE DE DADOS E PAINEL DE CONTROLE
    # ==========================================
    st.subheader("📋 Pipeline de Vendas")
    busca = st.text_input("🔍 Busca Rápida:", placeholder="Cliente, Status, Valores...")
    df_pedidos = vendas_repo.listar_pedidos(busca)

    # --- O PAINEL DE COMANDO INTELIGENTE ---
    @st.dialog("🚀 Painel de Comando do Pedido", width="large")
    def modal_painel_comando(pid, pcli_id, pcliente, pstatus, pvalor, pdata):
        
        # =========================================================================
        # MODO DE VISÃO 1: O CALENDÁRIO CENTRALIZADO
        # =========================================================================
        if st.session_state.get(f'show_calendar_{pid}', False):
            st.markdown("<h3 style='text-align: center; color: #0f4c81;'>📅 Previsão de Entrega</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 15px;'>Selecione a data de entrega acordada com o cliente para confirmar esta venda.</p>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            c_cal1, c_cal2, c_cal3 = st.columns([1.5, 2, 1.5])
            with c_cal2:
                data_prev_selecionada = st.date_input("Data", min_value=datetime.today(), label_visibility="collapsed", key=f"cal_modal_{pid}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            c_conf, c_canc = st.columns(2)
            with c_conf:
                if st.button("✔️ Confirmar Aprovação", type="primary", use_container_width=True, key=f"conf_modal_{pid}"):
                    sucesso, erro = vendas_repo.alterar_status_pedido(pid, "Pedido", data_previsao=data_prev_selecionada)
                    if sucesso:
                        registrar_auditoria(st.session_state.usuario_logado, f"Aprovou Pedido #{pid} c/ entrega p/ {data_prev_selecionada}")
                        st.session_state.pop(f'show_calendar_{pid}', None)
                        st.success("✅ Pedido Aprovado e Valor Congelado!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Erro na Base de Dados: {erro}")
            with c_canc:
                st.button("❌ Cancelar", use_container_width=True, key=f"canc_modal_{pid}", on_click=lambda: st.session_state.pop(f'show_calendar_{pid}', None))
            
            return 

        # =========================================================================
        # MODO DE VISÃO 2: A LINHA DO TEMPO NORMAL
        # =========================================================================
        st.markdown(f"### Pedido #{pid} — {pcliente}")
        st.caption(f"Valor: **R$ {pvalor:,.2f}** | Data Criação: **{pdata}**")
        
        fases = ["Orçamento", "Pedido", "Consolidado", "Faturado", "Entregue"]
        datas = vendas_repo.obter_datas_pedido(pid)

        def formata_data(dt_val):
            if pd.isna(dt_val) or not dt_val: return "---"
            try: return pd.to_datetime(dt_val).strftime("%d/%m %H:%M")
            except: return "---"

        datas_fases = [
            formata_data(datas.get('data_criacao')),
            formata_data(datas.get('data_pedido')),
            formata_data(datas.get('data_consolidado')),
            formata_data(datas.get('data_faturado')),
            formata_data(datas.get('data_entregue'))
        ]
        
        # --- PREPARAÇÃO DA DATA DE PREVISÃO PARA A LINHA DO TEMPO E O PDF ---
        previsao_crua = datas.get('data_previsao_entrega')
        data_prev_formatada = "" # <- Garantimos que a variável existe sempre
        if pd.notna(previsao_crua) and previsao_crua:
            data_prev_formatada = pd.to_datetime(previsao_crua).strftime("%d/%m/%Y")
            if datas_fases[4] == "---":
                datas_fases[4] = f"<span style='color:#d9534f; font-weight:bold;'>Prev: {data_prev_formatada}</span>"

        status_map = pstatus
        if pstatus in ['Rascunho', 'Orçamento']: status_map = "Orçamento"
        elif pstatus == 'Aprovado': status_map = "Pedido"
        
        try: idx_atual = fases.index(status_map)
        except: idx_atual = 0

        st.markdown("<br>", unsafe_allow_html=True)
        cols_fases = st.columns(len(fases))
        for i, fase in enumerate(fases):
            data_html = f"<span style='font-size: 11px; color: #888;'>{datas_fases[i]}</span>"
            if i < idx_atual: cols_fases[i].markdown(f"<div style='text-align:center; color:#28a745;'>✅<br><b>{fase}</b><br>{data_html}</div>", unsafe_allow_html=True)
            elif i == idx_atual: cols_fases[i].markdown(f"<div style='text-align:center; color:#0f4c81;'>🔵<br><b>{fase}</b><br>{data_html}</div>", unsafe_allow_html=True)
            else: cols_fases[i].markdown(f"<div style='text-align:center; color:#cccccc;'>⚪<br>{fase}<br>{data_html}</div>", unsafe_allow_html=True)
        
        st.progress(idx_atual / (len(fases)-1))
        st.markdown("<hr>", unsafe_allow_html=True)

        c_act, c_docs = st.columns([2.5, 1.5], gap="large")
        
        with c_act:
            st.markdown("#### ⚙️ Próxima Ação")
            
            if status_map == 'Orçamento':
                st.info("🟡 O cliente está a analisar a proposta. Assim que o cliente der o 'De Acordo', converta para Pedido.")
                st.button(
                    "✔️ Aprovar e Converter em Pedido", 
                    type="primary", 
                    use_container_width=True, 
                    key=f"btn_aprovar_{pid}",
                    on_click=lambda: st.session_state.update({f'show_calendar_{pid}': True})
                )
                    
            elif status_map == 'Pedido':
                st.warning("⏳ Venda garantida! Aguarde a equipa de Logística consolidar o lote no módulo de Compras.")
                
            elif status_map == 'Consolidado':
                st.info("📦 Logística preparada. Pode gerar as notas e faturas deste pedido.")
                if st.button("🧾 Emitir Faturamento (NF-e/Boleto)", type="primary", use_container_width=True, key=f"btn_faturar_{pid}"):
                    sucesso, erro = vendas_repo.alterar_status_pedido(pid, "Faturado")
                    if sucesso:
                        from repositories import financeiro_repo
                        financeiro_repo.gerar_fatura_do_pedido(pid)
                        registrar_auditoria(st.session_state.usuario_logado, f"Faturou Pedido #{pid}")
                        st.success("✅ Faturamento Emitido! A carregar...")
                        time.sleep(1)
                        st.rerun()
                    else: st.error(f"Erro: {erro}")
                        
            elif status_map == 'Faturado':
                st.info("🚚 Mercadoria a caminho do cliente final com Danfe e Boleto impresso.")
                if st.button("🏁 Confirmar Entrega ao Cliente", type="primary", use_container_width=True, key=f"btn_entregar_{pid}"):
                    sucesso, erro = vendas_repo.alterar_status_pedido(pid, "Entregue")
                    if sucesso:
                        registrar_auditoria(st.session_state.usuario_logado, f"Marcou Pedido #{pid} como Entregue")
                        st.success("🎉 Entrega Confirmada! A carregar...")
                        time.sleep(1)
                        st.rerun()
                    else: st.error(f"Erro: {erro}")
                        
            elif status_map == 'Entregue':
                st.success("🎉 Ciclo finalizado com sucesso! Cliente abastecido.")
                
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("⚠️ Opções de Risco (Reversão e Exclusão)"):
                if st.button("⏪ Voltar Fase", help="Reverte para o status anterior", key=f"btn_voltar_{pid}"):
                    if idx_atual > 0:
                        vendas_repo.alterar_status_pedido(pid, fases[idx_atual-1])
                        st.success("⏪ Fase revertida!")
                        time.sleep(1)
                        st.rerun()
                if st.button("🗑️ Eliminar Documento Definitivamente", key=f"btn_eliminar_{pid}"):
                    sucesso, erro = vendas_repo.excluir_pedido(pid)
                    if sucesso:
                        registrar_auditoria(st.session_state.usuario_logado, f"Eliminou Pedido #{pid}")
                        st.warning("🗑️ Pedido Eliminado!")
                        time.sleep(1)
                        st.rerun()

        with c_docs:
            st.markdown("#### 📎 Documentos (PDF)")
            df_itens_pdf = vendas_repo.obter_itens_pedido(pid)
            
            data_compacta = pdata.replace("-", "").replace("/", "")
            if status_map == 'Orçamento': prefixo = "ORC"
            elif status_map == 'Pedido': prefixo = "PED"
            elif status_map == 'Consolidado': prefixo = "CON"
            elif status_map == 'Faturado': prefixo = "FAT"
            elif status_map == 'Entregue': prefixo = "ENT"
            else: prefixo = "DOC"
            
            doc_formatado = f"{prefixo}{int(pcli_id):03d}{data_compacta}{pid:03d}"
            
            # --- INJEÇÃO DA DATA DE PREVISÃO DE ENTREGA ---
            # Passa a data_previsao para o motor de PDF apenas se não for mais um orçamento
            pdf_bytes = gerar_pdf_pedido(
                pedido_id_str=doc_formatado, 
                cliente_nome=pcliente, 
                data_pedido=pdata,
                data_previsao=data_prev_formatada if status_map != 'Orçamento' else "",
                df_itens=df_itens_pdf, 
                valor_total=pvalor, 
                empresa_info=empresa_dados,
                usuario_emissao=st.session_state.get('usuario_logado', 'Sistema')
            )
            
            st.download_button(label="📄 Proposta / Pedido Oficial", data=pdf_bytes, file_name=f"{doc_formatado}.pdf", mime="application/pdf", use_container_width=True)
            if status_map in ['Faturado', 'Entregue']:
                st.download_button("🧾 Visualizar DANFE (NF-e)", data=b"", file_name="danfe.pdf", disabled=True, use_container_width=True)
                st.download_button("💰 Baixar Boleto Bancário", data=b"", file_name="boleto.pdf", disabled=True, use_container_width=True)
            st.markdown("---")
            st.markdown("**Itens Protegidos:**")
            st.dataframe(df_itens_pdf[['nome_produto', 'quantidade', 'preco_unitario']], hide_index=True, use_container_width=True, height=150) 

    if not df_pedidos.empty:
        col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns([1, 4, 2, 2, 2, 1.5])
        col_h1.markdown("**ID**")
        col_h2.markdown("**Cliente**")
        col_h3.markdown("**Data**")
        col_h4.markdown("**Valor (R$)**")
        col_h5.markdown("**Fase (Status)**")
        col_h6.markdown("**Ações**")
        st.markdown("---")
        
        for _, row in df_pedidos.iterrows():
            pid = row['id_pedido']
            cliente = row['cliente']
            valor = row['valor_total']
            status = row['status']
            data_ped = str(row['data_criacao'])[:10]
            
            c1, c2, c3, c4, c5, c6 = st.columns([1, 4, 2, 2, 2, 1.5])
            c1.write(f"#{pid:03d}")
            c2.write(f"🏢 {cliente}")
            c3.write(data_ped)
            c4.write(f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            if status in ['Orçamento', 'Rascunho']: c5.markdown("📝 `Orçamento`")
            elif status in ['Pedido', 'Aprovado']: c5.markdown("🟢 `Pedido Validado`")
            elif status == 'Consolidado': c5.markdown("📦 `Consolidado`")
            elif status == 'Faturado': c5.markdown("🧾 `Faturado (Pendente Entrega)`")
            elif status == 'Entregue': c5.markdown("🏁 `Entregue e Finalizado`")
            else: c5.markdown(f"`{status}`")
            
            b_det, b_edit = c6.columns(2)
            with b_det:
                if st.button("⚙️", key=f"painel_{pid}", help="Abrir Painel de Comando"):
                    modal_painel_comando(pid, row['id_cliente'], cliente, status, valor, data_ped)
            with b_edit:
                if status in ['Orçamento', 'Rascunho']:
                    if st.button("✏️", key=f"edit_ped_{pid}", help="Editar Orçamento"):
                        st.session_state.editando_pedido_id = pid
                        st.session_state.editando_cliente_id = row['id_cliente']
                        df_itens_ed = vendas_repo.obter_itens_pedido(pid)
                        st.session_state.carrinho = []
                        for _, r_it in df_itens_ed.iterrows():
                            st.session_state.carrinho.append({
                                'produto_id': int(r_it['produto_id']), 'nome_produto': str(r_it['nome_produto']),
                                'quantidade': int(r_it['quantidade']), 'preco_unitario': float(r_it['preco_unitario']),
                                'custo_unitario': float(r_it['custo_unitario']), 'subtotal_venda': float(r_it['subtotal_venda']),
                                'subtotal_custo': float(r_it['subtotal_custo'])
                            })
                        st.rerun()
            st.markdown("<hr style='margin: 0px; opacity: 0.2;'>", unsafe_allow_html=True)
    else:
        st.info("Nenhum orçamento ou pedido encontrado.")