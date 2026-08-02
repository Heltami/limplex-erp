import streamlit as st
import pandas as pd
import requests
import time

from core.database import conectar_bd
from core.utils import (
    validar_cpf_cnpj, validar_cep, buscar_cep, 
    buscar_coordenada, calcular_rota
)
# IMPORTAMOS O NOSSO NOVO REPOSITÓRIO!
from repositories import fornecedor_repo

def render():
    st.title("🏭 Gestão de Fornecedores")
    
    # 1. Garante colunas no banco de dados
    fornecedor_repo.garantir_colunas_fornecedores()

    def clean_str(val): return "" if pd.isna(val) else str(val).strip()

    # 2. Busca lista de fornecedores
    df_forn_lista = fornecedor_repo.listar_fornecedores()

    for k in ['cep', 'rua', 'num', 'bairro', 'cid', 'uf', 'coord', 'compl', 'dist', 'tempo']:
        if f'forn_auto_{k}' not in st.session_state: st.session_state[f'forn_auto_{k}'] = ''

    if 'last_selected_forn_id' not in st.session_state: st.session_state.last_selected_forn_id = None

    if not df_forn_lista.empty:
        lista_forn_sel = ["➕ Novo Fornecedor (Limpar Formulário)"] + df_forn_lista.apply(lambda x: f"{x['id_fornecedor']} - {x['nome_fantasia']} ({x['cnpj']})", axis=1).tolist()
        escolha_forn = st.selectbox("Selecione um fornecedor para editar ou crie um novo:", lista_forn_sel)
        forn_editando = None
        if escolha_forn != "➕ Novo Fornecedor (Limpar Formulário)":
            id_f_sel = int(escolha_forn.split(" - ")[0])
            forn_editando = df_forn_lista[df_forn_lista['id_fornecedor'] == id_f_sel].iloc[0]
    else:
        forn_editando = None
        st.info("Nenhum fornecedor cadastrado. Preencha abaixo.")

    current_forn_id = forn_editando['id_fornecedor'] if forn_editando is not None else 'novo'
    if st.session_state.last_selected_forn_id != current_forn_id:
        st.session_state.last_selected_forn_id = current_forn_id
        for k in ['cep', 'rua', 'num', 'bairro', 'cid', 'uf', 'coord', 'compl', 'dist', 'tempo']:
            st.session_state[f'forn_auto_{k}'] = ''

    def get_forn_val(campo, state_key, def_val=""):
        if st.session_state[f'forn_auto_{state_key}']: return st.session_state[f'forn_auto_{state_key}']
        if forn_editando is not None and campo in forn_editando and not pd.isna(forn_editando[campo]): return str(forn_editando[campo])
        return def_val

    with st.form("form_fornecedor_crud"):
        st.markdown("### CADASTRO")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Dados Empresariais**")
            nome_fantasia = st.text_input("Nome Fantasia *", value=forn_editando['nome_fantasia'] if forn_editando is not None else "")
            razao_social = st.text_input("Razão Social", value=forn_editando['razao_social'] if forn_editando is not None and not pd.isna(forn_editando['razao_social']) else "")
            cpf_cnpj = st.text_input("CPF / CNPJ *", value=forn_editando['cnpj'] if forn_editando is not None and not pd.isna(forn_editando['cnpj']) else "")
            prazo = st.text_input("Prazo Pagamento", value=forn_editando['prazo_pagamento'] if forn_editando is not None and not pd.isna(forn_editando['prazo_pagamento']) else "")
            
        with col2:
            st.markdown("**Contato**")
            contato = st.text_input("Pessoa de Contato", value=forn_editando['contato'] if forn_editando is not None and not pd.isna(forn_editando['contato']) else "")
            cargo = st.text_input("Cargo", value=forn_editando['cargo'] if forn_editando is not None and 'cargo' in forn_editando and not pd.isna(forn_editando['cargo']) else "")
            telefone = st.text_input("Telefone / WhatsApp", value=forn_editando['telefone'] if forn_editando is not None and not pd.isna(forn_editando['telefone']) else "")
            email = st.text_input("E-mail", value=forn_editando['email'] if forn_editando is not None and not pd.isna(forn_editando['email']) else "")
            
        with col3:
            st.markdown("**Logística, GPS e Distância**")
            col_cep, col_num, col_btn = st.columns([3, 2, 1])
            with col_cep: cep = st.text_input("CEP *", value=get_forn_val('cep', 'cep'))
            with col_num: numero = st.text_input("Número *", value=get_forn_val('numero', 'num'))
            with col_btn:
                st.write(""); st.write("")
                btn_buscar_cep_f = st.form_submit_button("🔍", help="Buscar Endereço e GPS via CEP")

            complemento = st.text_input("Complemento", value=get_forn_val('complemento', 'compl'))
            st.caption("⚡ *Preenchimento automático via CEP/GPS:*")
            
            val_rua, val_bairro = get_forn_val('endereco', 'rua'), get_forn_val('bairro', 'bairro')
            val_cid, val_uf = get_forn_val('cidade', 'cid', 'Fortaleza'), get_forn_val('estado', 'uf', 'CE')
            val_coord = get_forn_val('coordenada', 'coord')

            endereco = st.text_input("Rua / Avenida (Doca)", value=val_rua)
            bairro = st.text_input("Bairro", value=val_bairro)
            
            c_cid, c_est = st.columns([3, 1])
            with c_cid: cidade = st.text_input("Cidade", value=val_cid)
            with c_est: estado = st.text_input("UF", value=val_uf)
                
            coordenada = st.text_input("Coordenada GPS (Lat, Lon)", value=val_coord)

            c_dist, c_temp = st.columns(2)
            v_dist = get_forn_val('distancia_km', 'dist', 0.0)
            v_temp = get_forn_val('tempo_minutos', 'tempo', 0)
            with c_dist: distancia_km = st.number_input("Distância da Sede (Km)", value=float(v_dist if str(v_dist).strip() else 0.0), step=0.1)
            with c_temp: tempo_minutos = st.number_input("Tempo de Viagem (Min)", value=int(float(v_temp if str(v_temp).strip() else 0)), step=1)

            if val_coord and ',' in val_coord:
                coord_clean = val_coord.replace(' ', '')
                st.markdown(f"📍 [**Maps ↗️**](https://www.google.com/maps/search/?api=1&query={coord_clean})")
            elif val_rua and val_cid:
                query_maps = requests.utils.quote(f"{val_rua}, {numero} - {val_bairro}, {val_cid} - {val_uf}")
                st.markdown(f"📍 [**Maps ↗️**](https://www.google.com/maps/search/?api=1&query={query_maps})")
            
        col_f1, col_f2 = st.columns(2)
        with col_f1: salvar_f_btn = st.form_submit_button("💾 Salvar / Atualizar Fornecedor", type="primary")
        with col_f2: excluir_f_btn = st.form_submit_button("🗑️ Excluir Este Fornecedor (Admin)")

        if btn_buscar_cep_f:
            if cep and validar_cep(cep):
                with st.spinner("A calcular rotas e ler satélites GPS..."):
                    r_rua, r_bairro, r_cid, r_est = buscar_cep(cep)
                    if r_rua:
                        st.session_state.forn_auto_cep, st.session_state.forn_auto_rua = cep, r_rua
                        st.session_state.forn_auto_bairro, st.session_state.forn_auto_cid = r_bairro, r_cid
                        st.session_state.forn_auto_uf, st.session_state.forn_auto_num = r_est, numero
                        st.session_state.forn_auto_compl = complemento
                        
                        if numero:
                            coord = buscar_coordenada(r_rua, numero, r_cid, r_est)
                            st.session_state.forn_auto_coord = coord if coord else ""
                            
                            if coord:
                                conn_cfg = conectar_bd()
                                df_cfg = pd.read_sql_query("SELECT coordenada FROM configuracoes WHERE id = 1", conn_cfg)
                                conn_cfg.close()
                                if not df_cfg.empty and df_cfg.iloc[0]['coordenada']:
                                    coord_sede = df_cfg.iloc[0]['coordenada']
                                    d_km, t_min = calcular_rota(coord_sede, coord)
                                    st.session_state.forn_auto_dist = d_km
                                    st.session_state.forn_auto_tempo = t_min
                                    if d_km > 0: st.info(f"🛣️ Rota calculada: {d_km} km em ~{t_min} min.")
                        else:
                            st.session_state.forn_auto_coord = ""
                        
                        st.success(f"✅ Endereço localizado: {r_rua}, Nº {numero}")
                        time.sleep(1); st.rerun()
                    else: st.error("⚠️ CEP não encontrado.")
            else: st.error("⚠️ Digite um CEP válido.")

        if salvar_f_btn:
            erros = []
            if not nome_fantasia: erros.append("O Nome Fantasia é obrigatório.")
            if not cpf_cnpj or not validar_cpf_cnpj(cpf_cnpj): erros.append("CPF ou CNPJ inválido.")
            
            if not erros:
                # Alinhar os dados na exata ordem do Repositório
                dados_fornecedor = (
                    nome_fantasia, razao_social, cpf_cnpj, contato, cargo, 
                    telefone, email, endereco, numero, complemento, 
                    bairro, cep, cidade, estado, coordenada, 
                    distancia_km, tempo_minutos, prazo
                )

                if forn_editando is not None:
                    sucesso, erro_msg = fornecedor_repo.salvar_fornecedor(dados_fornecedor, id_fornecedor=forn_editando['id_fornecedor'])
                else:
                    sucesso, erro_msg = fornecedor_repo.salvar_fornecedor(dados_fornecedor)
                
                if sucesso:
                    st.success("✅ Fornecedor guardado!")
                    for k in ['cep', 'rua', 'num', 'bairro', 'cid', 'uf', 'coord', 'compl', 'dist', 'tempo']: 
                        st.session_state[f'forn_auto_{k}'] = ''
                    time.sleep(1); st.rerun()
                else:
                    st.error(f"Erro ao salvar: {erro_msg}")
            else:
                for e in erros: st.error(f"⚠️ {e}")

        if excluir_f_btn:
            if st.session_state.perfil_utilizador != 'admin': 
                st.error("⛔ Acesso negado! Apenas admins podem excluir fornecedores.")
            elif forn_editando is not None:
                sucesso, erro_msg = fornecedor_repo.excluir_fornecedor(forn_editando['id_fornecedor'])
                if sucesso:
                    st.warning("🗑️ Fornecedor excluído!")
                    time.sleep(1); st.rerun()
                else:
                    st.error(f"Erro ao excluir: {erro_msg}")

    st.markdown("---")
    st.subheader("ANÁLISE")
    
    # 3. Usa o repositório para a tabela analítica
    df_forn_atual = fornecedor_repo.listar_fornecedores_analise()
    
    pesquisa_forn = st.text_input("🔍 Buscar Fornecedor:")
    if pesquisa_forn: 
        df_forn_atual = df_forn_atual[df_forn_atual.apply(lambda row: row.astype(str).str.contains(pesquisa_forn, case=False, na=False).any(), axis=1)]
    st.dataframe(df_forn_atual, use_container_width=True)