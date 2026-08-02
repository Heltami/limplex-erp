import streamlit as st
import pandas as pd
import time
from datetime import datetime

from core.database import conectar_bd
from core.utils import registrar_auditoria
from core.pdf_generator import gerar_pdf_pedido

def render():
    st.title("🛒 Gestão de Vendas (Orçamentos e Pedidos)")
    st.markdown("Inicie um orçamento para o cliente e, após aprovação, converta-o em um **Pedido Formal** aguardando a janela de compras.")
    
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []

    editando_id = st.session_state.get('editando_pedido_id', None)

    # Buscar dados da empresa globalmente para o PDF
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
        st.info("Adicione, altere quantidades ou remova itens antes de salvar. Depois, o registo será atualizado na tabela abaixo.")
    else:
        st.subheader("📝 Criar Novo Orçamento")

    conn = conectar_bd()
    df_clientes = pd.read_sql_query("SELECT * FROM clientes ORDER BY razao_social", conn)
    df_produtos = pd.read_sql_query("SELECT * FROM produtos ORDER BY descricao", conn)
    conn.close()

    if df_clientes.empty or df_produtos.empty:
        st.warning("⚠️ Precisa de ter pelo menos 1 Cliente e 1 Produto registados para criar orçamentos.")
    else:
        cli_id_col = 'id_cliente' if 'id_cliente' in df_clientes.columns else 'id'
        prod_id_col = 'id_produto' if 'id_produto' in df_produtos.columns else 'id'

        cliente_opcoes = dict(zip(df_clientes[cli_id_col], df_clientes['razao_social']))
        
        edit_cli_id = st.session_state.get('editando_cliente_id', None)
        idx_cli = 0
        if edit_cli_id and edit_cli_id in cliente_opcoes:
            idx_cli = list(cliente_opcoes.keys()).index(edit_cli_id)
        
        cliente_selecionado_id = st.selectbox(
            "👤 Selecione o Cliente:", 
            options=list(cliente_opcoes.keys()), 
            format_func=lambda x: cliente_opcoes[x], 
            index=idx_cli,
            key="select_cli_carrinho",
            disabled=bool(editando_id)
        )

        st.markdown("---")

        with st.form("form_add_item", clear_on_submit=True):
            c1, c2, c3 = st.columns([4.5, 0.7, 1.1])
            
            produto_opcoes = {}
            for _, p_row in df_produtos.iterrows():
                p_id = p_row[prod_id_col]
                p_desc = str(p_row.get('descricao', 'N/D'))
                p_preco = float(p_row.get('preco_venda') or 0.0)
                
                p_forn = str(p_row.get('fornecedor', p_row.get('marca', 'N/D')))
                if p_forn.lower() == 'nan' or not p_forn.strip(): 
                    p_forn = 'N/D'
                    
                label_rica = f"R$ {p_preco:.2f} | {p_desc} | Forn: {p_forn}"
                produto_opcoes[p_id] = label_rica
            
            produto_selecionado_id = c1.selectbox(
                "Adicionar Produto:", 
                options=list(produto_opcoes.keys()), 
                format_func=lambda x: produto_opcoes[x]
            )
            
            quantidade = c2.number_input("Qtd", min_value=1, value=1)

            with c3:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                submit_adicionar = st.form_submit_button("➕ Adicionar", use_container_width=True)

            if submit_adicionar:
                prod_info = df_produtos[df_produtos[prod_id_col] == produto_selecionado_id].iloc[0]
                preco_unit = float(prod_info['preco_venda'] or 0)
                custo_unit = float(prod_info['prc_distribuidora'] or 0)
                
                produto_existente = next((item for item in st.session_state.carrinho if item['produto_id'] == int(produto_selecionado_id)), None)
                
                if produto_existente:
                    produto_existente['quantidade'] += int(quantidade)
                    produto_existente['subtotal_venda'] = produto_existente['quantidade'] * produto_existente['preco_unitario']
                    produto_existente['subtotal_custo'] = produto_existente['quantidade'] * produto_existente['custo_unitario']
                    st.success(f"✅ Quantidade atualizada!")
                else:
                    item = {
                        'produto_id': int(produto_selecionado_id),
                        'nome_produto': str(prod_info['descricao']),
                        'sku': str(prod_info.get('sku', 'N/D')),
                        'quantidade': int(quantidade),
                        'preco_unitario': preco_unit,
                        'custo_unitario': custo_unit,
                        'subtotal_venda': preco_unit * quantidade,
                        'subtotal_custo': custo_unit * quantidade
                    }
                    st.session_state.carrinho.append(item)
                    st.success(f"✅ Adicionado ao carrinho!")
                st.rerun()

        if st.session_state.carrinho:
            st.markdown("<br>### 🛒 Resumo", unsafe_allow_html=True)
            
            ch1, ch2, ch3, ch4, ch5 = st.columns([3, 1, 1.5, 1.5, 1.5])
            ch1.markdown("<span style='font-size: 0.85em; color: #666;'>**Produto**</span>", unsafe_allow_html=True)
            ch2.markdown("<span style='font-size: 0.85em; color: #666;'>**Qtd**</span>", unsafe_allow_html=True)
            ch3.markdown("<span style='font-size: 0.85em; color: #666;'>**R$ Unit.**</span>", unsafe_allow_html=True)
            ch4.markdown("<span style='font-size: 0.85em; color: #666;'>**R$ Total**</span>", unsafe_allow_html=True)
            ch5.markdown("<span style='font-size: 0.85em; color: #666;'>**Ações**</span>", unsafe_allow_html=True)
            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
            
            for idx, item in enumerate(st.session_state.carrinho):
                ci1, ci2, ci3, ci4, ci5 = st.columns([3, 1, 1.5, 1.5, 1.5])
                ci1.markdown(f"<span style='font-size: 0.85em;'>📦 {item['nome_produto']}</span>", unsafe_allow_html=True)
                ci2.markdown(f"<span style='font-size: 0.85em;'><b>{item['quantidade']}</b></span>", unsafe_allow_html=True)
                ci3.markdown(f"<span style='font-size: 0.85em;'>R$ {item['preco_unitario']:.2f}</span>", unsafe_allow_html=True)
                ci4.markdown(f"<span style='font-size: 0.85em;'><b>R$ {item['subtotal_venda']:.2f}</b></span>", unsafe_allow_html=True)
                
                b_menos, b_mais, b_del = ci5.columns(3)
                with b_menos:
                    if st.button("➖", key=f"btn_menos_{idx}", help="Diminuir"):
                        if item['quantidade'] > 1:
                            st.session_state.carrinho[idx]['quantidade'] -= 1
                            st.session_state.carrinho[idx]['subtotal_venda'] = st.session_state.carrinho[idx]['quantidade'] * item['preco_unitario']
                            st.session_state.carrinho[idx]['subtotal_custo'] = st.session_state.carrinho[idx]['quantidade'] * item['custo_unitario']
                            st.rerun()
                with b_mais:
                    if st.button("➕", key=f"btn_mais_{idx}", help="Aumentar"):
                        st.session_state.carrinho[idx]['quantidade'] += 1
                        st.session_state.carrinho[idx]['subtotal_venda'] = st.session_state.carrinho[idx]['quantidade'] * item['preco_unitario']
                        st.session_state.carrinho[idx]['subtotal_custo'] = st.session_state.carrinho[idx]['quantidade'] * item['custo_unitario']
                        st.rerun()
                with b_del:
                    if st.button("🗑️", key=f"btn_del_{idx}", help="Remover"):
                        st.session_state.carrinho.pop(idx)
                        st.rerun()
                        
                st.markdown("<hr style='margin: 0; opacity: 0.1;'>", unsafe_allow_html=True)

            df_carrinho = pd.DataFrame(st.session_state.carrinho)
            total_venda = 0.0
            total_custo = 0.0
            if not df_carrinho.empty:
                total_venda = float(df_carrinho['subtotal_venda'].sum())
                total_custo = float(df_carrinho['subtotal_custo'].sum())
            
            lucro_estimado = total_venda - total_custo

            st.markdown("""
                <style>
                .metric-box { font-size: 0.85em; padding: 10px 0; }
                .metric-title { font-weight: bold; color: #555; }
                .metric-val-1 { color: #0f4c81; font-weight: bold; font-size: 1.3em; }
                .metric-val-2 { color: #888; font-weight: bold; font-size: 1.1em; }
                .metric-val-3 { color: #28a745; font-weight: bold; font-size: 1.1em; }
                </style>
            """, unsafe_allow_html=True)

            col_t1, col_t2, col_t3 = st.columns(3)
            col_t1.markdown(f"<div class='metric-box'><div class='metric-title'>Valor a Cobrar:</div><div class='metric-val-1'>R$ {total_venda:.2f}</div></div>", unsafe_allow_html=True)
            col_t2.markdown(f"<div class='metric-box'><div class='metric-title'>Custo Fornecedor:</div><div class='metric-val-2'>R$ {total_custo:.2f}</div></div>", unsafe_allow_html=True)
            col_t3.markdown(f"<div class='metric-box'><div class='metric-title'>Lucro Estimado:</div><div class='metric-val-3'>R$ {lucro_estimado:.2f}</div></div>", unsafe_allow_html=True)
            
            st.markdown("---")

            col_btn_canc, col_btn_salv, _ = st.columns([1.5, 1.5, 5])
            
            with col_btn_canc:
                if st.button("❌ Cancelar", use_container_width=True, key="btn_cancelar_geral"):
                    st.session_state.pop('editando_pedido_id', None)
                    st.session_state.pop('editando_cliente_id', None)
                    st.session_state.carrinho = []
                    st.rerun()

            with col_btn_salv:
                if st.session_state.carrinho:
                    if st.button("💾 Salvar", type="primary", use_container_width=True, key="btn_guardar_pedido"):
                        conn = conectar_bd()
                        cursor = conn.cursor()
                        try:
                            cli_id_val = int(cliente_selecionado_id)
                            nome_cliente = str(cliente_opcoes[cli_id_val])
                            v_total = float(total_venda)
                            c_total = float(total_custo)
                            l_est = float(lucro_estimado)
                            
                            if editando_id:
                                cursor.execute('''
                                    UPDATE pedidos 
                                    SET valor_total=%s, custo_total=%s, lucro_estimado=%s, observacoes=%s
                                    WHERE id=%s
                                ''', (v_total, c_total, l_est, "", editando_id))
                                
                                cursor.execute("DELETE FROM itens_pedido WHERE pedido_id=%s", (editando_id,))
                                
                                pedido_id = editando_id
                                msg_sucesso = f"✅ Orçamento atualizado com sucesso!"
                                acao_aud = f"Atualizou Orçamento ID {pedido_id}"
                            else:
                                data_str = datetime.now().strftime('%Y%m%d')
                                cursor.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = %s", (cli_id_val,))
                                seq_count = cursor.fetchone()[0] + 1
                                
                                cursor.execute('''
                                    INSERT INTO pedidos (cliente_id, nome_cliente, status, valor_total, custo_total, lucro_estimado, observacoes)
                                    VALUES (%s, %s, 'Orçamento', %s, %s, %s, %s) RETURNING id
                                ''', (cli_id_val, nome_cliente, v_total, c_total, l_est, ""))
                                pedido_id = cursor.fetchone()[0]
                                
                                num_customizado = f"ORC{cli_id_val:03d}{data_str}{seq_count:03d}"
                                msg_sucesso = f"✅ Documento `{num_customizado}` salvo com sucesso!"
                                acao_aud = f"Criou {num_customizado}"

                            for item in st.session_state.carrinho:
                                cursor.execute('''
                                    INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, quantidade, preco_unitario, custo_unitario, subtotal_venda, subtotal_custo)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ''', (
                                    int(pedido_id), 
                                    int(item['produto_id']), 
                                    str(item['nome_produto']), 
                                    int(item['quantidade']), 
                                    float(item['preco_unitario']), 
                                    float(item['custo_unitario']), 
                                    float(item['subtotal_venda']), 
                                    float(item['subtotal_custo'])
                                ))

                            conn.commit()
                            registrar_auditoria(st.session_state.usuario_logado, acao_aud)
                            st.session_state.carrinho = [] 
                            
                            if editando_id:
                                st.session_state.pop('editando_pedido_id', None)
                                st.session_state.pop('editando_cliente_id', None)
                                
                            st.success(msg_sucesso)
                            time.sleep(1.2); st.rerun()
                            
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Erro ao salvar: {e}")
                        finally:
                            conn.close()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border: 2px solid #ddd; margin: 30px 0;'>", unsafe_allow_html=True)

    # ==========================================
    # PARTE INFERIOR: TABELA GERAL DE REGISTOS
    # ==========================================
    st.subheader("📋 Base de Dados: Orçamentos e Pedidos")
    
    busca = st.text_input(
        "🔍 Busca Inteligente Livre:", 
        placeholder="Digite Cliente, Status (Orçamento, Pedido, Consolidado), Nº Pedido ou lógica (Ex: valor_total > 500)",
        key="busca_inteligente_pedidos"
    )
    
    conn = conectar_bd()
    query_pedidos = """
        SELECT p.id as id_pedido, c.id_cliente, c.razao_social as cliente, p.data_criacao, p.status, p.valor_total, p.lucro_estimado 
        FROM pedidos p
        JOIN clientes c ON p.cliente_id = c.id_cliente
        ORDER BY p.id DESC
    """
    df_pedidos = pd.read_sql_query(query_pedidos, conn)
    conn.close()

    if busca and not df_pedidos.empty:
        if any(op in busca for op in ['>', '<', '==', '!=']):
            try: df_pedidos = df_pedidos.query(busca)
            except:
                mask = df_pedidos.astype(str).apply(lambda x: x.str.contains(busca, case=False, na=False)).any(axis=1)
                df_pedidos = df_pedidos[mask]
        else:
            mask = df_pedidos.astype(str).apply(lambda x: x.str.contains(busca, case=False, na=False)).any(axis=1)
            df_pedidos = df_pedidos[mask]

    @st.dialog("⚠️ Confirmar Exclusão")
    def modal_confirmar_exclusao(pid, num_formatado):
        st.warning(f"Tem a certeza que deseja eliminar o registo **{num_formatado}**? Esta ação é irreversível.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✔️ Cancelar", use_container_width=True, key=f"canc_del_mod_{pid}"):
                st.rerun()
        with c2:
            if st.button("🗑️ Sim, Eliminar", type="primary", use_container_width=True, key=f"confirm_del_mod_{pid}"):
                conn = conectar_bd()
                cursor = conn.cursor()
                try:
                    cursor.execute("DELETE FROM pedidos WHERE id = %s", (pid,))
                    conn.commit()
                    registrar_auditoria(st.session_state.usuario_logado, f"Eliminou Registo {num_formatado}")
                    st.success(f"✅ Registo {num_formatado} eliminado com sucesso!")
                    time.sleep(1.2); st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Erro ao eliminar: {e}")
                finally:
                    conn.close()

    @st.dialog("⚙️ Detalhes e Ações")
    def modal_gerir_pedido(pid, pcliente, pstatus, pnum_formatado):
        st.markdown(f"### {pnum_formatado} - {pcliente}")
        
        conn = conectar_bd()
        df_itens = pd.read_sql_query('''
            SELECT p.sku, p.descricao as nome_produto, i.quantidade, i.preco_unitario, i.subtotal_venda 
            FROM itens_pedido i
            LEFT JOIN produtos p ON i.produto_id = p.id_produto
            WHERE i.pedido_id = %s
        ''', conn, params=(pid,))
        conn.close()
        
        st.dataframe(df_itens, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔄 Alteração de Status e Ações")
        
        status_opcoes = ["Orçamento", "Pedido", "Consolidado"]
        pstatus_map = pstatus
        if pstatus == 'Rascunho': pstatus_map = 'Orçamento'
        elif pstatus == 'Aprovado': pstatus_map = 'Pedido'
        
        idx_atual = status_opcoes.index(pstatus_map) if pstatus_map in status_opcoes else 0
        
        c_st, c_act1, c_act2 = st.columns([2, 1.2, 1.2])
        
        novo_status = c_st.selectbox(
            "Status Atual:", 
            options=status_opcoes, 
            index=idx_atual, 
            key=f"sel_st_modal_{pid}"
        )
        
        with c_act1:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            with st.popover("💾 Salvar", use_container_width=True):
                st.markdown(f"Alterar status de **{pstatus_map}** para **{novo_status}**?")
                if st.button("✔️ Confirmar", type="primary", key=f"btn_salvar_st_{pid}", use_container_width=True):
                    conn = conectar_bd()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE pedidos SET status = %s WHERE id = %s", (novo_status, pid))
                    conn.commit()
                    registrar_auditoria(st.session_state.usuario_logado, f"Alterou Status de {pnum_formatado} para '{novo_status}'")
                    conn.close()
                    st.success(f"✅ Status alterado para **{novo_status}**!")
                    time.sleep(1.2); st.rerun()

        with c_act2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            with st.popover("🗑️ Eliminar", use_container_width=True):
                st.markdown("⚠️ **Confirma a exclusão irreversível?**")
                if st.button("✔️ Sim, Eliminar", type="primary", key=f"confirm_del_in_modal_{pid}", use_container_width=True):
                    conn = conectar_bd()
                    cursor = conn.cursor()
                    try:
                        cursor.execute("DELETE FROM pedidos WHERE id = %s", (pid,))
                        conn.commit()
                        registrar_auditoria(st.session_state.usuario_logado, f"Eliminou {pnum_formatado}")
                        st.success("Registo eliminado com sucesso.")
                        time.sleep(1.2); st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao eliminar: {e}")
                    finally:
                        conn.close()

    if not df_pedidos.empty:
        col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns([2.0, 3.2, 1.7, 1.9, 1.6, 2.8])
        col_h1.markdown("**Nº Registo**")
        col_h2.markdown("**Cliente**")
        col_h3.markdown("**Data**")
        col_h4.markdown("**Valor (R$)**")
        col_h5.markdown("**Status**")
        col_h6.markdown("**Ações**")
        st.markdown("---")
        
        for index, row in df_pedidos.iterrows():
            pid = row['id_pedido']
            cli_id = row['id_cliente']
            cliente = row['cliente']
            data_ped = str(row['data_criacao'])[:10]
            data_compacta = str(row['data_criacao'])[:10].replace("-", "")
            
            valor = row['valor_total']
            status = row['status']
            
            if status in ['Orçamento', 'Rascunho']: prefixo_dinamico = "ORC"
            elif status in ['Pedido', 'Aprovado']: prefixo_dinamico = "PED"
            elif status == 'Consolidado': prefixo_dinamico = "CON"
            else: prefixo_dinamico = "DOC"
            
            doc_formatado = f"{prefixo_dinamico}{cli_id:03d}{data_compacta}{pid:03d}"
            
            c1, c2, c3, c4, c5, c6 = st.columns([2.0, 3.2, 1.7, 1.9, 1.6, 2.8])
            
            c1.write(f"`{doc_formatado}`")
            c2.write(f"🏢 {cliente}")
            c3.write(data_ped)
            c4.write(f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            if status in ['Orçamento', 'Rascunho']: c5.markdown("📝 `Orçamento`")
            elif status in ['Pedido', 'Aprovado']: c5.markdown("✅ `Pedido`")
            elif status == 'Consolidado': c5.markdown("📦 `Consolidado`")
            else: c5.markdown(f"`{status}`")
            
            b_det, b_pdf, b_edit, b_del = c6.columns(4)
            
            with b_det:
                if st.button("👁️", key=f"det_{pid}", help=f"Ver detalhes de {doc_formatado}"):
                    modal_gerir_pedido(pid, cliente, status, doc_formatado)
                    
            with b_pdf:
                conn_i = conectar_bd()
                df_cli_det = pd.read_sql_query("SELECT * FROM clientes WHERE id_cliente = %s", conn_i, params=(cli_id,))
                cnpj_cli = "N/D"
                end_cli = "Endereço não informado"
                if not df_cli_det.empty:
                    r_cli = df_cli_det.iloc[0]
                    for col_c in ['cnpj', 'documento']:
                        if col_c in r_cli and r_cli[col_c]: cnpj_cli = str(r_cli[col_c])
                    for col_e in ['endereco', 'rua', 'logradouro', 'morada']:
                        if col_e in r_cli and r_cli[col_e]: end_cli = str(r_cli[col_e])

                df_itens_pdf = pd.read_sql_query('''
                    SELECT p.sku, p.descricao as nome_produto, i.quantidade, i.preco_unitario, i.subtotal_venda 
                    FROM itens_pedido i
                    LEFT JOIN produtos p ON i.produto_id = p.id_produto
                    WHERE i.pedido_id = %s
                ''', conn_i, params=(pid,))
                conn_i.close()
                
                pdf_bytes_reimp = gerar_pdf_pedido(
                    pedido_id_str=doc_formatado,
                    cliente_nome=cliente,
                    cliente_cnpj=cnpj_cli,
                    cliente_end=end_cli,
                    data_pedido=str(row['data_criacao']),
                    cond_pag="PIX / À Vista",
                    itens_df=df_itens_pdf,
                    total_pedido=float(valor),
                    empresa_info=empresa_dados,
                    usuario_emissao=st.session_state.get('usuario_logado', 'Sistema')
                )
                
                st.download_button(label="📄", data=pdf_bytes_reimp, file_name=f"{doc_formatado}.pdf", mime="application/pdf", key=f"reimp_pdf_{pid}", help=f"Baixar PDF: {doc_formatado}")
            
            with b_edit:
                if status in ['Orçamento', 'Rascunho']:
                    if st.button("✏️", key=f"edit_ped_{pid}", help=f"Editar {doc_formatado}"):
                        st.session_state.editando_pedido_id = pid
                        st.session_state.editando_cliente_id = cli_id
                        
                        conn_ed = conectar_bd()
                        df_itens_ed = pd.read_sql_query("SELECT * FROM itens_pedido WHERE pedido_id = %s", conn_ed, params=(pid,))
                        df_produtos_ed = pd.read_sql_query("SELECT * FROM produtos", conn_ed)
                        p_id_col = 'id_produto' if 'id_produto' in df_produtos_ed.columns else 'id'
                        
                        st.session_state.carrinho = []
                        for _, r_it in df_itens_ed.iterrows():
                            p_id_val = int(r_it['produto_id'])
                            sku_val = "N/D"
                            prod_match = df_produtos_ed[df_produtos_ed[p_id_col] == p_id_val]
                            if not prod_match.empty:
                                sku_val = str(prod_match.iloc[0].get('sku', 'N/D'))
                                
                            st.session_state.carrinho.append({
                                'produto_id': p_id_val,
                                'nome_produto': str(r_it['nome_produto']),
                                'sku': sku_val,
                                'quantidade': int(r_it['quantidade']),
                                'preco_unitario': float(r_it['preco_unitario']),
                                'custo_unitario': float(r_it['custo_unitario']),
                                'subtotal_venda': float(r_it['subtotal_venda']),
                                'subtotal_custo': float(r_it['subtotal_custo'])
                            })
                        
                        conn_ed.close()
                        
                        st.success("✅ Orçamento carregado! Desloque-se ao topo da página para editar.")
                        time.sleep(1.2); st.rerun()

            with b_del:
                if st.button("🗑️", key=f"del_ped_{pid}", help=f"Eliminar {doc_formatado}"):
                    modal_confirmar_exclusao(pid, doc_formatado)
                    
            st.markdown("<hr style='margin: 0px; opacity: 0.2;'>", unsafe_allow_html=True)
    else:
        st.info("Nenhum orçamento ou pedido encontrado.")