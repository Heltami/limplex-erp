import streamlit as st
import pandas as pd
import io
import time
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from core.database import conectar_bd
from core.utils import registrar_auditoria

# IMPORTA O NOVO REPOSITÓRIO!
from repositories import produto_repo

def render():
    st.title("📦 Catálogo de Produtos e Precificação")

    # 1. Puxa os fornecedores
    df_forn = produto_repo.listar_fornecedores_combo()
    
    @st.dialog("➕ Adicionar Novo Produto")
    def modal_adicionar_produto():
        if df_forn.empty:
            st.warning("⚠️ Cadastre pelo menos um fornecedor no menu 'Fornecedores' antes de criar um produto.")
            return

        with st.form("form_novo_produto", clear_on_submit=True):
            lista_fornecedores = df_forn.apply(lambda x: f"{x['id_fornecedor']} - {x['nome_fantasia']}", axis=1).tolist()
            novo_forn = st.selectbox("Fornecedor do Produto *", lista_fornecedores)
            
            st.markdown("---")
            col_p1, col_p2 = st.columns([1, 3])
            with col_p1:
                novo_sku = st.text_input("Código / SKU *")
            with col_p2:
                nova_desc = st.text_input("Descrição do Produto *")
                
            col_p3, col_p4 = st.columns(2)
            with col_p3:
                novo_custo = st.number_input("Custo na Distribuidora (R$) *", min_value=0.0, format="%.2f")
            with col_p4:
                novo_venda = st.number_input("Preço de Mercado / Varejo (R$) *", min_value=0.0, format="%.2f", help="O valor de prateleira normal deste item.")
                
            st.info("💡 O Preço Limplex será gerado aplicando o seu Desconto Padrão sobre o Preço de Mercado. O Lucro e a Margem serão calculados automaticamente.")
            
            if st.form_submit_button("💾 Salvar Produto", type="primary", use_container_width=True):
                if not novo_sku or not nova_desc:
                    st.error("⚠️ O SKU e a Descrição são obrigatórios.")
                elif novo_venda <= 0:
                    st.error("⚠️ O preço de venda deve ser maior que zero.")
                else:
                    id_forn_escolhido = int(novo_forn.split(" - ")[0])
                    
                    # Usa o Repositório para salvar
                    sucesso, erro = produto_repo.salvar_produto(id_forn_escolhido, novo_sku.strip(), nova_desc.strip(), novo_custo, novo_venda)
                    
                    if sucesso:
                        produto_repo.aplicar_precificacao_limplex(sku_especifico=novo_sku.strip())
                        registrar_auditoria(st.session_state.usuario_logado, f"Criou o produto SKU: {novo_sku.strip()}")
                        st.success(f"✅ Produto '{nova_desc}' adicionado com sucesso!")
                        time.sleep(1.5); st.rerun()
                    else:
                        if "unique constraint" in erro.lower() or "duplicate key" in erro.lower():
                            st.error("⛔ Já existe um produto registado com este SKU. O código deve ser único.")
                        else:
                            st.error(f"Erro ao salvar: {erro}")

    st.markdown("### 📊 Tabela Geral de Produtos")
    
    col_f1, col_f2, col_f3, col_f4, col_f5, col_f6, col_f7 = st.columns([2, 2, 1, 1, 1, 1, 1])
    with col_f1:
        f_forn = st.selectbox("Fornecedor:", ["Todos"] + df_forn['nome_fantasia'].tolist(), key="filtro_forn_col")
    with col_f2:
        f_prod = st.text_input("Desc. / SKU:", placeholder="ex: luva", key="filtro_prod_col")
    with col_f3:
        f_custo = st.text_input("Custo:", placeholder="> 10", key="filtro_custo_col")
    with col_f4:
        f_venda = st.text_input("Varejo:", placeholder="< 100", key="filtro_venda_col")
    with col_f5:
        f_lucro = st.text_input("Lucro:", placeholder="> 15", key="filtro_lucro_col")
    with col_f6:
        f_margem = st.text_input("Margem:", placeholder=">= 20", key="filtro_margem_col")
    with col_f7:
        f_status = st.selectbox("Status:", ["Todos", "LUCRO", "NORMAL", "PERDA"], key="filtro_status_col")
        
    def parse_filtro_texto(texto_str, coluna_sql):
        texto_str = texto_str.strip()
        if not texto_str: return "", []
        import re
        partes = re.split(r'\s+(and|or)\s+', texto_str, flags=re.IGNORECASE)
        sql_conds = []; sql_params = []
        i = 0
        while i < len(partes):
            bloco = partes[i].strip()
            if bloco.lower() in ['and', 'or']:
                conectivo = bloco.upper(); i += 1
                if i < len(partes): bloco_val = partes[i].strip()
                else: break
            else:
                conectivo = None; bloco_val = bloco
            if bloco_val:
                if bloco_val.startswith('!='):
                    termo = bloco_val[2:].strip()
                    cond = f"({coluna_sql} NOT ILIKE %s AND sku NOT ILIKE %s)"
                    sql_params.extend([f"%{termo}%", f"%{termo}%"])
                else:
                    cond = f"({coluna_sql} ILIKE %s OR sku ILIKE %s)"
                    sql_params.extend([f"%{bloco_val}%", f"%{bloco_val}%"])
                if conectivo and sql_conds: sql_conds.append(f"{conectivo} {cond}")
                else: sql_conds.append(cond)
            i += 1
        if sql_conds: return f" AND ({' '.join(sql_conds)})", sql_params
        return "", []

    def parse_filtro_avancado(valor_str, coluna_sql):
        valor_str = valor_str.strip()
        if not valor_str: return "", []
        import re
        partes = re.split(r'\s+(and|or)\s+', valor_str, flags=re.IGNORECASE)
        sql_conds = []; sql_params = []
        i = 0
        while i < len(partes):
            bloco = partes[i].strip()
            if bloco.lower() in ['and', 'or']:
                conectivo = bloco.upper(); i += 1
                if i < len(partes): bloco_val = partes[i].strip()
                else: break
            else:
                conectivo = None; bloco_val = bloco
            match = re.match(r'^(>|<|>=|<=|!=|=)?\s*([\d\.,]+)$', bloco_val)
            if match:
                op, val = match.groups()
                val = val.replace(',', '.')
                try:
                    num = float(val); operador = op if op else '='
                    cond = f"{coluna_sql} {operador} %s"
                    if conectivo and sql_conds: sql_conds.append(f"{conectivo} {cond}")
                    else: sql_conds.append(cond)
                    sql_params.append(num)
                except: pass
            i += 1
        if sql_conds: return f" AND ({' '.join(sql_conds)})", sql_params
        return "", []

    # Combina filtros dinâmicos
    sql_extra = ""
    params_extra = []
    
    sql_t, param_t = parse_filtro_texto(f_prod, "p.descricao")
    sql_extra += sql_t; params_extra.extend(param_t)
    sql_c, param_c = parse_filtro_avancado(f_custo, "p.prc_distribuidora")
    sql_extra += sql_c; params_extra.extend(param_c)
    sql_v, param_v = parse_filtro_avancado(f_venda, "p.preco_venda")
    sql_extra += sql_v; params_extra.extend(param_v)
    sql_l, param_l = parse_filtro_avancado(f_lucro, "p.lucro_reais")
    sql_extra += sql_l; params_extra.extend(param_l)
    sql_m, param_m = parse_filtro_avancado(f_margem, "p.margem_lucro")
    sql_extra += sql_m; params_extra.extend(param_m)

    # --- CORREÇÃO: ADICIONAR A REGRA DO STATUS AQUI ---
    if f_status != "Todos":
        sql_extra += " AND p.status = %s"
        params_extra.append(f_status)
    # ---------------------------------------------------

    # 2. Executa a listagem via repositório
    df_p = produto_repo.listar_produtos(f_forn, sql_extra, params_extra)
    
    if not df_p.empty:
        col_m1, col_m2 = st.columns([2, 10])
        with col_m1:
            selecionar_todos = st.checkbox("Selecionar Todos", key="chk_sel_todos_prod")
            
        df_p.insert(0, "✅", selecionar_todos)
        df_p['custo'] = df_p['custo'].astype(float)
        df_p['preco_venda'] = df_p['preco_venda'].astype(float)
        df_p['preco_limplex'] = df_p['preco_limplex'].astype(float)
        df_p['lucro_reais'] = df_p['lucro_reais'].astype(float)
        df_p['margem_lucro'] = df_p['margem_lucro'].astype(float)
        
        edited_df = st.data_editor(
            df_p,
            column_config={
                "✅": st.column_config.CheckboxColumn("Sel.", default=False),
                "id_produto": st.column_config.NumberColumn("ID Prod.", disabled=True),
                "id_fornecedor": st.column_config.NumberColumn("ID Forn.", disabled=True),
                "sku": st.column_config.TextColumn("Código SKU", disabled=True),
                "descricao": st.column_config.TextColumn("Descrição do Produto"),
                "fornecedor": st.column_config.TextColumn("Fornecedor", disabled=True),
                "custo": st.column_config.NumberColumn("Custo (R$)", format="%.2f", min_value=0.0),
                "preco_venda": st.column_config.NumberColumn("Varejo (R$)", format="%.2f", min_value=0.0, help="Preço base de mercado"),
                "preco_limplex": st.column_config.NumberColumn("⭐ Limplex (R$)", format="%.2f", disabled=True, help="O preço competitivo aplicado ao cliente"),
                "lucro_reais": st.column_config.NumberColumn("Lucro Líq. (R$)", format="%.2f", disabled=True),
                "margem_lucro": st.column_config.NumberColumn("Margem (%)", format="%.2f", disabled=True),
                "status": st.column_config.TextColumn("Status", disabled=True, help="LUCRO, NORMAL ou PERDA"),
            },
            hide_index=True, use_container_width=True, key="editor_produtos_todos_campos", height=420
        )
        
        selecionados = edited_df[edited_df["✅"] == True]
        qtd_selecionados = len(selecionados)
        
        if qtd_selecionados > 0:
            st.markdown(f"📌 **{qtd_selecionados}** produto(s) selecionado(s) na tabela.")
        else:
            st.markdown("ℹ️ Nenhum produto selecionado no momento.")
        
        col_btn1, col_btn2, col_btn3, col_btn4, _ = st.columns([2, 2, 2, 2.5, 1.5])
        
        with col_btn1:
            if st.button("➕ Adicionar Produto", type="primary", use_container_width=True):
                modal_adicionar_produto()
                
        with col_btn2:
            if st.button("🔄 Recalcular Margens", help="Aplica impostos, descontos e margem desejada", use_container_width=True):
                sucesso, msg = produto_repo.aplicar_precificacao_limplex()
                if sucesso:
                    st.success("✅ Margens e Status recalculados!")
                    time.sleep(1); st.rerun()
                else:
                    st.error(f"Erro ao recalcular: {msg}")
                
        with col_btn3:
            if st.button("🗑️ Eliminar Selecionados", help="Inativa os produtos marcados", use_container_width=True):
                if not selecionados.empty:
                    if st.session_state.perfil_utilizador == 'admin':
                        ids_l = selecionados['id_produto'].tolist()
                        sucesso, msg = produto_repo.inativar_produtos(ids_l)
                        if sucesso:
                            st.success(f"✅ {len(selecionados)} produtos inativados!")
                            time.sleep(1); st.rerun()
                        else:
                            st.error(f"Erro ao inativar: {msg}")
                    else: st.error("⛔ Apenas administradores.")
                else: st.warning("⚠️ Marque itens na tabela.")

        with col_btn4:
            with st.popover("📥 Baixar (PDF/XLSX/CSV)", use_container_width=True):
                if selecionados.empty:
                    st.warning("⚠️ Marque produtos na tabela para exportar.")
                else:
                    df_export = selecionados.drop(columns=["✅"]).copy()
                    st.markdown("**Escolha o formato de exportação:**")
                    
                    # 1. EXPORTAR CSV
                    csv_data = df_export.to_csv(index=False).encode('utf-8')
                    st.download_button(label="📄 Baixar CSV", data=csv_data, file_name=f"produtos_limplex_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", use_container_width=True)
                    
                    # 2. EXPORTAR EXCEL
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Produtos Limplex')
                    excel_data = output_excel.getvalue()
                    st.download_button(label="📊 Baixar Excel (.xlsx)", data=excel_data, file_name=f"produtos_limplex_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    
                    # IMPORTA AS FUNÇÕES DE PDF DO NOSSO MOTOR CENTRAL
                    from core.pdf_generator import gerar_pdf_produtos_interno, gerar_pdf_catalogo_cliente
                    
                    # 3. PDF INTERNO (Gestão)
                    pdf_data = gerar_pdf_produtos_interno(df_export)
                    st.download_button(label="📄 Baixar PDF Relatório Interno", data=pdf_data, file_name=f"relatorio_interno_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)

                    # 4. PDF CLIENTE (Catálogo Oficial)
                    conn_pdf = conectar_bd()
                    df_cfg_pdf = pd.read_sql_query("SELECT * FROM configuracoes WHERE id = 1", conn_pdf)
                    conn_pdf.close()
                    empresa_dict = df_cfg_pdf.iloc[0].to_dict() if not df_cfg_pdf.empty else {}
                    
                    usuario_logado = st.session_state.get('usuario_logado', 'Sistema')
                    
                    pdf_cliente_data = gerar_pdf_catalogo_cliente(df_export, empresa_info=empresa_dict, usuario_emissao=usuario_logado)
                    st.download_button(label="🌟 Baixar PDF Cliente", data=pdf_cliente_data, file_name=f"tabela_precos_limplex_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf", mime="application/pdf", use_container_width=True)       

        # TRATA AS EDIÇÕES FEITAS DIRETAMENTE NA GRELHA
        mudancas = st.session_state.get("editor_produtos_todos_campos", {}).get("edited_rows", {})
        if mudancas:
            st.warning("⚠️ Foram detetadas edições na tabela. Clique no botão abaixo para guardar.")
            if st.button("💾 Confirmar e Salvar Alterações da Tabela", type="primary", use_container_width=True):
                sucesso, msg = produto_repo.atualizar_produtos_em_lote(mudancas, df_p)
                if sucesso:
                    produto_repo.aplicar_precificacao_limplex()
                    st.success("✅ Alterações salvas com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Erro ao atualizar produtos: {msg}")
    else:
        st.info("Nenhum produto encontrado com estes filtros.")
        if st.button("➕ Adicionar Produto", type="primary"):
            modal_adicionar_produto()

    # IMPORTAÇÃO POR FICHEIRO (AGORA USANDO O REPOSITÓRIO)
    st.markdown("---")
    st.markdown("### 📥 Importar Tabela de Produtos por Fornecedor")
    
    if df_forn.empty:
        st.warning("⚠️ Cadastre pelo menos um fornecedor no menu 'Fornecedores' antes de importar.")
    else:
        forn_upload_sel = st.selectbox("Fornecedor Destino:", df_forn.apply(lambda x: f"{x['id_fornecedor']} - {x['nome_fantasia']}", axis=1).tolist(), key="forn_up_prod")
        id_forn_destino = int(forn_upload_sel.split(" - ")[0])
        ficheiro_up = st.file_uploader("Carregar Ficheiro (Excel ou CSV):", type=["xlsx", "csv"], key="up_prod_file")
        
        if ficheiro_up is not None:
            try:
                if ficheiro_up.name.endswith('.csv'): df_upload = pd.read_csv(ficheiro_up)
                else: df_upload = pd.read_excel(ficheiro_up)
                
                st.markdown("**Pré-visualização dos dados carregados:**")
                st.dataframe(df_upload.head(3), use_container_width=True)
                
                col_u1, col_u2 = st.columns(2)
                col_sku = col_u1.selectbox("Coluna SKU/Código:", df_upload.columns.tolist(), key="sku_col")
                col_desc = col_u2.selectbox("Coluna Descrição:", df_upload.columns.tolist(), key="desc_col")
                col_u3, col_u4 = st.columns(2)
                col_custo = col_u3.selectbox("Coluna Custo (Distribuidora):", df_upload.columns.tolist(), key="custo_col")
                col_venda = col_u4.selectbox("Coluna Preço de Mercado (Varejo):", df_upload.columns.tolist(), key="venda_col")
                
                if st.button("🚀 Processar e Importar Produtos", type="primary"):
                    dados_para_importar = []
                    for _, row in df_upload.iterrows():
                        sku = str(row[col_sku]); desc = str(row[col_desc])
                        try:
                            custo = float(row[col_custo]); venda = float(row[col_venda])
                            dados_para_importar.append((sku, desc, custo, venda))
                        except: continue
                        
                    # Chama o repositório para salvar em lote
                    importados, msg = produto_repo.importar_produtos_excel_csv(id_forn_destino, dados_para_importar)
                    
                    if importados > 0:
                        produto_repo.aplicar_precificacao_limplex()
                        st.success(f"✅ {importados} produtos importados/atualizados com sucesso!")
                        time.sleep(1.5); st.rerun()
                    else:
                        st.error(f"Erro ao importar: {msg}")
            except Exception as e:
                st.error(f"Erro ao processar o ficheiro: {e}")