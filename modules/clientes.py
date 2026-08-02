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
from repositories import cliente_repo

def render():
    st.title("👥 Gestão de Clientes")
    
    # Executa a verificação estrutural nas tabelas via Repositório
    cliente_repo.garantir_colunas_clientes()

    def clean_str(val): return "" if pd.isna(val) else str(val).strip()

    # Busca os clientes usando o Repositório
    df_clientes = cliente_repo.listar_clientes()

    for k in ['cep', 'rua', 'num', 'bairro', 'cid', 'uf', 'coord', 'compl', 'end_fat', 'dist', 'tempo']:
        if f'cli_auto_{k}' not in st.session_state: st.session_state[f'cli_auto_{k}'] = ''

    if 'last_selected_cli_id' not in st.session_state: st.session_state.last_selected_cli_id = None

    if not df_clientes.empty:
        lista_cli_sel = ["➕ Novo Cadastro (Limpar Formulário)"] + df_clientes.apply(lambda x: f"{x['id_cliente']} - {x['razao_social']} ({x['cnpj']})", axis=1).tolist()
        escolha_cli = st.selectbox("Selecione um cliente para editar ou crie um novo:", lista_cli_sel)
        cli_editando = None
        if escolha_cli != "➕ Novo Cadastro (Limpar Formulário)":
            id_sel = int(escolha_cli.split(" - ")[0])
            cli_editando = df_clientes[df_clientes['id_cliente'] == id_sel].iloc[0]
    else:
        cli_editando = None
        st.info("Nenhum cliente cadastrado ainda. Preencha abaixo para criar o primeiro.")

    current_cli_id = cli_editando['id_cliente'] if cli_editando is not None else 'novo'
    if st.session_state.last_selected_cli_id != current_cli_id:
        st.session_state.last_selected_cli_id = current_cli_id
        for k in ['cep', 'rua', 'num', 'bairro', 'cid', 'uf', 'coord', 'compl', 'end_fat', 'dist', 'tempo']:
            st.session_state[f'cli_auto_{k}'] = ''

    def get_val(campo, state_key, def_val=""):
        if st.session_state[f'cli_auto_{state_key}']: return st.session_state[f'cli_auto_{state_key}']
        if cli_editando is not None and campo in cli_editando and not pd.isna(cli_editando[campo]): return str(cli_editando[campo])
        return def_val

    with st.form("form_cliente_crud"):
        st.markdown("### CADASTRO")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Empresa / Cliente**")
            razao_social = st.text_input("Razão Social *", value=cli_editando['razao_social'] if cli_editando is not None else "")
            nome_fantasia = st.text_input("Nome Fantasia", value=cli_editando['nome_fantasia'] if cli_editando is not None and not pd.isna(cli_editando['nome_fantasia']) else "")
            cpf_cnpj = st.text_input("CPF / CNPJ *", value=cli_editando['cnpj'] if cli_editando is not None and not pd.isna(cli_editando['cnpj']) else "")
            inscricao_estadual = st.text_input("Inscrição Estadual", value=cli_editando['inscricao_estadual'] if cli_editando is not None and not pd.isna(cli_editando['inscricao_estadual']) else "Isento")
            condiz = ["PIX / À Vista", "Boleto 15 dias", "Boleto 30 dias"]
            idx_cond = condiz.index(cli_editando['condicao_pagamento']) if cli_editando is not None and cli_editando['condicao_pagamento'] in condiz else 0
            condicao_pag = st.selectbox("Condição de Pagamento", condiz, index=idx_cond)

        with col2:
            st.markdown("**Contato**")
            contato_principal = st.text_input("Contato Principal", value=cli_editando['contato_principal'] if cli_editando is not None and not pd.isna(cli_editando['contato_principal']) else "")
            cargo = st.text_input("Cargo", value=cli_editando['cargo'] if cli_editando is not None and not pd.isna(cli_editando['cargo']) else "")
            whatsapp_telefone = st.text_input("WhatsApp / Telefone", value=cli_editando['whatsapp_telefone'] if cli_editando is not None and not pd.isna(cli_editando['whatsapp_telefone']) else "")
            email = st.text_input("E-mail", value=cli_editando['email'] if cli_editando is not None and not pd.isna(cli_editando['email']) else "")
            horario_entrega = st.text_input("Horário de Entrega", value=cli_editando['horario_entrega'] if cli_editando is not None and not pd.isna(cli_editando['horario_entrega']) else "08:00 - 12:00")

        with col3:
            st.markdown("**Logística, GPS e Distância**")
            col_cep, col_num, col_btn = st.columns([3, 2, 1])
            with col_cep: cep = st.text_input("CEP *", value=get_val('cep', 'cep'))
            with col_num: numero = st.text_input("Número *", value=get_val('numero', 'num'))
            with col_btn:
                st.write(""); st.write("")
                btn_buscar_cep = st.form_submit_button("🔍", help="Buscar Endereço, GPS e calcular distância")

            complemento = st.text_input("Complemento", value=get_val('complemento', 'compl'))
            st.caption("⚡ *Preenchimento automático via CEP/GPS:*")
            
            val_rua, val_bairro = get_val('endereco_entrega', 'rua'), get_val('bairro', 'bairro')
            val_cid, val_uf = get_val('cidade', 'cid', 'Fortaleza'), get_val('estado', 'uf', 'CE')
            val_coord = get_val('coordenada', 'coord')

            endereco_entrega = st.text_input("Rua / Avenida", value=val_rua)
            bairro = st.text_input("Bairro", value=val_bairro)
            
            c_cid, c_est = st.columns([3, 1])
            with c_cid: cidade = st.text_input("Cidade", value=val_cid)
            with c_est: estado = st.text_input("UF", value=val_uf)
            
            coordenada = st.text_input("Coordenada GPS (Lat, Lon)", value=val_coord)
            
            c_dist, c_temp = st.columns(2)
            v_dist = get_val('distancia_km', 'dist', 0.0)
            v_temp = get_val('tempo_minutos', 'tempo', 0)
            with c_dist: distancia_km = st.number_input("Distância da Sede (Km)", value=float(v_dist if str(v_dist).strip() else 0.0), step=0.1)
            with c_temp: tempo_minutos = st.number_input("Tempo de Viagem (Min)", value=int(float(v_temp if str(v_temp).strip() else 0)), step=1)
            
            if val_coord and ',' in val_coord:
                coord_clean = val_coord.replace(' ', '')
                st.markdown(f"📍 [**Maps ↗️**](https://www.google.com/maps/search/?api=1&query={coord_clean})")
            elif val_rua and val_cid:
                query_maps = requests.utils.quote(f"{val_rua}, {numero} - {val_bairro}, {val_cid} - {val_uf}")
                st.markdown(f"📍 [**Maps ↗️**](https://www.google.com/maps/search/?api=1&query={query_maps})")

        observacoes = st.text_area("Observações (Acesso, Restrições, etc)", value=cli_editando['observacoes'] if cli_editando is not None and not pd.isna(cli_editando['observacoes']) else "")
        
        col_b1, col_b2 = st.columns(2)
        with col_b1: salvar_btn = st.form_submit_button("💾 Salvar / Atualizar Cliente", type="primary")
        with col_b2: excluir_btn = st.form_submit_button("🗑️ Excluir Este Cliente (Admin)")

        # PROCESSAMENTO DE BUSCA DE CEP
        if btn_buscar_cep:
            if cep and validar_cep(cep):
                with st.spinner("A calcular rotas e ler satélites GPS..."):
                    r_rua, r_bairro, r_cid, r_est = buscar_cep(cep)
                    if r_rua:
                        st.session_state.cli_auto_cep, st.session_state.cli_auto_rua = cep, r_rua
                        st.session_state.cli_auto_bairro, st.session_state.cli_auto_cid = r_bairro, r_cid
                        st.session_state.cli_auto_uf, st.session_state.cli_auto_num = r_est, numero
                        st.session_state.cli_auto_compl = complemento
                        
                        if numero:
                            coord = buscar_coordenada(r_rua, numero, r_cid, r_est)
                            st.session_state.cli_auto_coord = coord if coord else ""
                            
                            if coord:
                                conn_cfg = conectar_bd()
                                df_cfg = pd.read_sql_query("SELECT coordenada FROM configuracoes WHERE id = 1", conn_cfg)
                                conn_cfg.close()
                                if not df_cfg.empty and df_cfg.iloc[0]['coordenada']:
                                    coord_sede = df_cfg.iloc[0]['coordenada']
                                    d_km, t_min = calcular_rota(coord_sede, coord)
                                    st.session_state.cli_auto_dist = d_km
                                    st.session_state.cli_auto_tempo = t_min
                                    if d_km > 0: st.info(f"🛣️ Rota calculada: {d_km} km em ~{t_min} min.")
                        else:
                            st.session_state.cli_auto_coord = ""
                        
                        st.success(f"✅ Endereço localizado: {r_rua}, Nº {numero}")
                        time.sleep(1); st.rerun()
                    else: st.error("⚠️ CEP não encontrado.")
            else: st.error("⚠️ Digite um CEP válido.")

        # PROCESSAMENTO DE SALVAR
        if salvar_btn:
            erros = []
            if not razao_social: erros.append("Razão Social obrigatória.")
            if not cpf_cnpj or not validar_cpf_cnpj(cpf_cnpj): erros.append("CPF/CNPJ inválido.")
            if not erros:
                # Tupla com os dados na ordem exata que o Repositório espera
                dados_cliente = (
                    razao_social, nome_fantasia, cpf_cnpj, inscricao_estadual, contato_principal, 
                    cargo, whatsapp_telefone, email, endereco_entrega, numero, complemento, 
                    bairro, cep, cidade, estado, coordenada, distancia_km, tempo_minutos, 
                    condicao_pag, horario_entrega, observacoes
                )
                
                # Chamada limpa ao Repositório
                if cli_editando is not None:
                    sucesso, erro_msg = cliente_repo.salvar_cliente(dados_cliente, id_cliente=cli_editando['id_cliente'])
                else:
                    sucesso, erro_msg = cliente_repo.salvar_cliente(dados_cliente)
                
                if sucesso:
                    st.success("✅ Cliente guardado com sucesso!")
                    for k in ['cep', 'rua', 'num', 'bairro', 'cid', 'uf', 'coord', 'compl', 'end_fat', 'dist', 'tempo']: 
                        st.session_state[f'cli_auto_{k}'] = ''
                    time.sleep(1); st.rerun()
                else:
                    st.error(f"Erro ao salvar na base de dados: {erro_msg}")
            else:
                for e in erros: st.error(f"⚠️ {e}")

        # PROCESSAMENTO DE EXCLUSÃO
        if excluir_btn:
            if st.session_state.perfil_utilizador != 'admin': 
                st.error("⛔ Acesso negado! Apenas administradores podem excluir clientes.")
            elif cli_editando is not None:
                sucesso, erro_msg = cliente_repo.excluir_cliente(cli_editando['id_cliente'])
                if sucesso:
                    st.warning("🗑️ Cliente excluído!")
                    time.sleep(1); st.rerun()
                else:
                    st.error(f"Erro ao excluir: {erro_msg}")

    st.markdown("---")
    st.subheader("ANÁLISE")
    
    # Busca da tabela de análise através do Repositório
    df_cli_atualizado = cliente_repo.listar_clientes_analise()
    
    pesquisa_cli = st.text_input("🔍 Buscar Cliente:")
    if pesquisa_cli: 
        df_cli_atualizado = df_cli_atualizado[df_cli_atualizado.apply(lambda row: row.astype(str).str.contains(pesquisa_cli, case=False, na=False).any(), axis=1)]
    
    st.dataframe(df_cli_atualizado, use_container_width=True)