import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

from core.database import conectar_bd
from core.utils import registrar_auditoria, validar_cpf_cnpj, validar_email, validar_telefone, validar_cep, buscar_cep, buscar_coordenada
from seguranca import validar_complexidade_senha

def render():
    st.title("⚙️ Configurações Globais do Sistema")
    st.markdown("Aqui você define a identidade da Limplex, as regras de precificação globais e a segurança do ERP.")
    
    aba1, aba2, aba3 = st.tabs(["🏢 Identidade da Empresa", "💰 Precificação e Margens", "🛡️ Segurança e Acessos"])
    
    with aba1:
        conn = conectar_bd()
        df_cfg = pd.read_sql_query("SELECT * FROM configuracoes WHERE id = 1", conn)
        conn.close()
        
        cfg = df_cfg.iloc[0].to_dict() if not df_cfg.empty else {}

        # CORREÇÃO 1: Inicializar as variáveis de sessão para evitar KeyError
        for k in ['cep', 'rua', 'num', 'bairro', 'cid', 'uf', 'coord', 'compl']:
            if f'emp_auto_{k}' not in st.session_state:
                st.session_state[f'emp_auto_{k}'] = ''

        # CORREÇÃO 2: Usar o método .get() para segurança absoluta
        def get_emp_val(campo, state_key, def_val=""):
            val_sessao = st.session_state.get(f'emp_auto_{state_key}', '')
            if val_sessao:
                return val_sessao
            if campo in cfg and cfg[campo] is not None and not pd.isna(cfg[campo]):
                return str(cfg[campo])
            return def_val

        with st.form("form_emp"):
            st.markdown("### CADASTRO DADOS DA EMPRESA")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Dados Cadastrais**")
                raz = st.text_input("Razão Social *", value=str(cfg.get('razao_social') or ""))
                fant = st.text_input("Nome Fantasia *", value=str(cfg.get('nome_fantasia') or ""))
                cnpj_e = st.text_input("CPF / CNPJ *", value=str(cfg.get('cnpj') or ""))

            with col2:
                st.markdown("**Contato**")
                tel = st.text_input("Telefone / WhatsApp", value=str(cfg.get('telefone') or ""))
                email_e = st.text_input("E-mail Oficial", value=str(cfg.get('email') or ""))

            with col3:
                st.markdown("**Logística e GPS (Sede da Empresa)**")
                col_cep, col_num, col_btn = st.columns([3, 2, 1])
                with col_cep:
                    cep = st.text_input("CEP *", value=get_emp_val('cep', 'cep'))
                with col_num:
                    numero = st.text_input("Número *", value=get_emp_val('numero', 'num'))
                with col_btn:
                    st.write("")
                    st.write("")
                    btn_buscar_cep_e = st.form_submit_button("🔍", help="Buscar Endereço e GPS via CEP")

                complemento = st.text_input("Complemento", value=get_emp_val('complemento', 'compl'))
                st.caption("⚡ *Preenchimento automático via CEP/GPS:*")
                
                val_rua = get_emp_val('endereco', 'rua')
                val_bairro = get_emp_val('bairro', 'bairro')
                val_cid = get_emp_val('cidade', 'cid', 'Fortaleza')
                val_uf = get_emp_val('estado', 'uf', 'CE')
                val_coord = get_emp_val('coordenada', 'coord')

                endereco = st.text_input("Rua / Avenida", value=val_rua)
                bairro = st.text_input("Bairro", value=val_bairro)
                
                c_cid, c_est = st.columns([3, 1])
                with c_cid:
                    cidade = st.text_input("Cidade", value=val_cid)
                with c_est:
                    estado = st.text_input("UF", value=val_uf)
                    
                coordenada = st.text_input("Coordenada GPS (Lat, Lon)", value=val_coord)

                if val_coord and ',' in val_coord:
                    coord_clean = val_coord.replace(' ', '')
                    maps_url = f"https://www.google.com/maps/search/?api=1&query={coord_clean}"
                    st.markdown(f"📍 [**Maps ↗️**]({maps_url})")
                elif val_rua and val_cid:
                    query_maps = requests.utils.quote(f"{val_rua}, {numero} - {val_bairro}, {val_cid} - {val_uf}")
                    maps_url = f"https://www.google.com/maps/search/?api=1&query={query_maps}"
                    st.markdown(f"📍 [**Maps ↗️**]({maps_url})")

            salvar_emp_btn = st.form_submit_button("💾 Salvar Dados da Empresa", type="primary")

            if btn_buscar_cep_e:
                if cep and validar_cep(cep):
                    with st.spinner("A consultar Correios e Satélite GPS..."):
                        r_rua, r_bairro, r_cid, r_est = buscar_cep(cep)
                        if r_rua:
                            st.session_state.emp_auto_cep = cep
                            st.session_state.emp_auto_rua = r_rua
                            st.session_state.emp_auto_bairro = r_bairro
                            st.session_state.emp_auto_cid = r_cid
                            st.session_state.emp_auto_uf = r_est
                            st.session_state.emp_auto_num = numero
                            st.session_state.emp_auto_compl = complemento
                            
                            if numero:
                                coord = buscar_coordenada(r_rua, numero, r_cid, r_est)
                                st.session_state.emp_auto_coord = coord if coord else ""
                            else:
                                st.session_state.emp_auto_coord = ""
                            
                            st.success(f"✅ Endereço localizado: {r_rua}, Nº {numero} - {r_bairro}, {r_cid}/{r_est}")
                            time.sleep(0.8)
                            st.rerun()
                        else:
                            st.error("⚠️ CEP não encontrado na base dos Correios.")
                else:
                    st.error("⚠️ Digite um CEP válido com 8 números para buscar.")

            if salvar_emp_btn:
                erros = []
                if not raz: erros.append("A Razão Social é obrigatória.")
                if not fant: erros.append("O Nome Fantasia é obrigatório.")
                if not cnpj_e or not validar_cpf_cnpj(cnpj_e): erros.append("O CPF ou CNPJ informado é inválido.")
                if not validar_email(email_e): erros.append("O formato do E-mail é inválido.")
                if not validar_telefone(tel): erros.append("O Telefone/WhatsApp deve ter 10 ou 11 dígitos.")
                if not validar_cep(cep): erros.append("O CEP deve conter exatamente 8 dígitos numéricos.")

                if not erros:
                    conn = conectar_bd()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE configuracoes SET 
                            razao_social=%s, nome_fantasia=%s, cnpj=%s, telefone=%s, email=%s,
                            endereco=%s, numero=%s, complemento=%s, bairro=%s, cep=%s, 
                            cidade=%s, estado=%s, coordenada=%s
                        WHERE id = 1
                    ''', (raz, fant, cnpj_e, tel, email_e, endereco, numero, complemento, bairro, cep, cidade, estado, coordenada))
                    conn.commit()
                    conn.close()
                    st.success("✅ Dados da empresa guardados com sucesso!")
                    for k in ['cep', 'rua', 'num', 'bairro', 'cid', 'uf', 'coord', 'compl']:
                        st.session_state[f'emp_auto_{k}'] = ''
                    time.sleep(1); st.rerun()
                else:
                    for e in erros:
                        st.error(f"⚠️ {e}")

    with aba2:
        st.subheader("💰 Estratégia de Precificação e Margens Globais")
        st.markdown("Estes percentuais são **deduzidos automaticamente** do Preço de Mercado para calcular o Preço Limplex, o Lucro Líquido e classificar a saúde dos produtos.")
        
        conn = conectar_bd()
        df_cfg2 = pd.read_sql_query("SELECT * FROM configuracoes WHERE id = 1", conn)
        conn.close()
        cfg_p2 = df_cfg2.iloc[0] if not df_cfg2.empty else {}

        with st.form("form_impostos"):
            c1, c2, c3, c4 = st.columns(4)
            p_desc = c1.number_input("Desconto Padrão (%)", value=float(cfg_p2.get('perc_desconto_padrao', 0.0)), help="Desconto base aplicado sobre o preço de mercado.")
            p_imp = c2.number_input("Imposto Simples Nacional (%)", value=float(cfg_p2.get('perc_imposto', 0.0)))
            p_frete = c3.number_input("Custo Logístico / Frete (%)", value=float(cfg_p2.get('perc_frete', 0.0)))
            p_lucro = c4.number_input("Lucro Desejado / Meta (%)", value=float(cfg_p2.get('margem_lucro_desejada', 15.0)), help="Margem mínima para o produto receber status de LUCRO.")
            
            if st.form_submit_button("Salvar Estratégia de Precificação", type="primary"):
                conn = conectar_bd()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE configuracoes SET perc_imposto = %s, perc_frete = %s, perc_desconto_padrao = %s, margem_lucro_desejada = %s WHERE id = 1", 
                    (p_imp, p_frete, p_desc, p_lucro)
                )
                
                cursor.execute('''
                    UPDATE produtos p
                    SET lucro_reais = 
                            (p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) 
                            - p.prc_distribuidora 
                            - ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) * c.perc_imposto / 100.0) 
                            - ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) * c.perc_frete / 100.0),
                        margem_lucro = ROUND(CAST((
                            ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) 
                             - p.prc_distribuidora 
                             - ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) * c.perc_imposto / 100.0) 
                             - ((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)) * c.perc_frete / 100.0)
                            ) / NULLIF((p.preco_venda * (1 - c.perc_desconto_padrao/100.0)), 0)
                        ) * 100 AS NUMERIC), 2)
                    FROM configuracoes c WHERE c.id = 1
                ''')
                
                cursor.execute('''
                    UPDATE produtos
                    SET status = CASE 
                        WHEN margem_lucro >= (SELECT margem_lucro_desejada FROM configuracoes WHERE id=1) THEN 'LUCRO'
                        WHEN margem_lucro > 0 THEN 'NORMAL'
                        ELSE 'PERDA'
                    END
                    WHERE status != 'INATIVO'
                ''')
                
                conn.commit()
                registrar_auditoria(st.session_state.usuario_logado, "Atualizou Estratégia de Precificação")
                conn.close()
                st.success("✅ Estratégia aplicada com sucesso a todo o catálogo!")
                time.sleep(1); st.rerun()

    with aba3:
        st.subheader("⚙️ Política de Segurança e Governança de Acessos")
        
        conn = conectar_bd()
        df_sec_cfg = pd.read_sql_query("SELECT * FROM configuracoes WHERE id = 1", conn)
        conn.close()
        
        s_cfg = df_sec_cfg.iloc[0] if not df_sec_cfg.empty else {}
        
        with st.form("form_politica_seguranca"):
            st.markdown("**Parâmetros Globais de Senhas e Bloqueio**")
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                p_val_dias = st.number_input("Validade da Senha (dias)", min_value=1, max_value=365, value=int(s_cfg.get('senha_validade_dias', 90)))
                p_tam_min = st.number_input("Tamanho Mínimo da Senha", min_value=6, max_value=32, value=int(s_cfg.get('senha_tamanho_min', 12)))
                p_complex = st.checkbox("Exigir Complexidade (Maiúsculas, Números, Símbolos)", value=bool(s_cfg.get('exigir_complexidade', True)))
                
            with col_s2:
                p_tentativas = st.number_input("Máximo de Tentativas Antes do Bloqueio", min_value=1, max_value=10, value=int(s_cfg.get('max_tentativas_bloqueio', 5)))
                p_tempo_blq = st.number_input("Tempo de Castigo / Bloqueio (minutos)", min_value=1, max_value=1440, value=int(s_cfg.get('tempo_bloqueio_min', 15)))
                p_hist_qtd = st.number_input("Memória de Senhas (Não repetir as últimas N)", min_value=0, max_value=20, value=int(s_cfg.get('historico_senhas_qtd', 3)))
                
            if st.form_submit_button("💾 Salvar Parâmetros de Segurança", type="primary"):
                if st.session_state.perfil_utilizador == 'admin':
                    conn = conectar_bd()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE configuracoes SET 
                            senha_validade_dias = %s,
                            senha_tamanho_min = %s,
                            exigir_complexidade = %s,
                            max_tentativas_bloqueio = %s,
                            tempo_bloqueio_min = %s,
                            historico_senhas_qtd = %s
                        WHERE id = 1
                    ''', (p_val_dias, p_tam_min, p_complex, p_tentativas, p_tempo_blq, p_hist_qtd))
                    conn.commit()
                    registrar_auditoria(st.session_state.usuario_logado, "Atualizou a Política de Segurança Global")
                    conn.close()
                    st.success("✅ Política de segurança atualizada com sucesso!")
                    time.sleep(1); st.rerun()
                else:
                    st.error("⛔ Apenas administradores podem alterar políticas de segurança.")

        st.markdown("---")
        st.subheader("👥 Criar Novo Colaborador / Usuário")
        
        if st.session_state.perfil_utilizador != 'admin':
            st.warning("⚠️ Apenas administradores podem gerenciar usuários.")
        else:
            with st.form("novo_user", clear_on_submit=True):
                col_u1, col_u2, col_u3 = st.columns(3)
                with col_u1:
                    novo_u = st.text_input("Novo Usuário (Login)")
                with col_u2:
                    nova_s = st.text_input("Palavra-passe Inicial", type="password")
                with col_u3:
                    novo_p = st.selectbox("Perfil de Acesso", ["operacional", "admin"])
                    
                if st.form_submit_button("Cadastrar Usuário"):
                    if novo_u and nova_s:
                        valida, msg = validar_complexidade_senha(nova_s)
                        if not valida:
                            st.error(f"⚠️ {msg}")
                        else:
                            try:
                                from seguranca import gerar_hash_senha
                                senha_encriptada = gerar_hash_senha(nova_s)
                                
                                conn = conectar_bd()
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT INTO utilizadores (usuario, senha_hash, perfil, data_ultima_senha) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)", 
                                    (novo_u, senha_encriptada, novo_p)
                                )
                                cursor.execute(
                                    "INSERT INTO historico_senhas (usuario, senha_hash) VALUES (%s, %s)",
                                    (novo_u, senha_encriptada)
                                )
                                conn.commit()
                                registrar_auditoria(st.session_state.usuario_logado, f"Criou o usuário '{novo_u}'")
                                conn.close()
                                st.success(f"Usuário '{novo_u}' cadastrado com sucesso!")
                                time.sleep(1); st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao cadastrar usuário (o usuário já existe?): {e}")
                    else:
                        st.error("Preencha todos os campos para criar o usuário.")
            
            @st.dialog("🔑 Redefinir Senha do Usuário")
            def modal_alterar_senha_usuario(usuario_alvo):
                st.markdown(f"**Usuário:** `{usuario_alvo}`")
                nova_senha_admin = st.text_input("Nova Palavra-passe", type="password")
                
                if st.button("🔄 Salvar Nova Senha", type="primary", use_container_width=True):
                    valida, msg = validar_complexidade_senha(nova_senha_admin)
                    if not valida:
                        st.error(f"⚠️ {msg}")
                    else:
                        from seguranca import gerar_hash_senha, verificar_senha
                        try:
                            conn = conectar_bd()
                            cursor = conn.cursor()
                            
                            qtd_memoria = int(s_cfg.get('historico_senhas_qtd', 3))
                            reutilizou = False
                            
                            if qtd_memoria > 0:
                                cursor.execute('''
                                    SELECT senha_hash FROM historico_senhas 
                                    WHERE usuario = %s 
                                    ORDER BY data_troca DESC LIMIT %s
                                ''', (usuario_alvo, qtd_memoria))
                                historico = cursor.fetchall()
                                
                                for (hash_antigo,) in historico:
                                    if verificar_senha(nova_senha_admin, hash_antigo):
                                        reutilizou = True
                                        break
                                        
                            if reutilizou:
                                st.error(f"⚠️ Segurança: A nova senha não pode ser igual a nenhuma das últimas {qtd_memoria} senhas.")
                            else:
                                novo_hash = gerar_hash_senha(nova_senha_admin)
                                cursor.execute(
                                    "UPDATE utilizadores SET senha_hash = %s, data_ultima_senha = CURRENT_TIMESTAMP WHERE usuario = %s", 
                                    (novo_hash, usuario_alvo)
                                )
                                cursor.execute(
                                    "INSERT INTO historico_senhas (usuario, senha_hash) VALUES (%s, %s)",
                                    (usuario_alvo, novo_hash)
                                )
                                conn.commit()
                                registrar_auditoria(st.session_state.usuario_logado, f"Redefiniu a senha do usuário '{usuario_alvo}'")
                                st.success(f"✅ Senha atualizada com sucesso!")
                                time.sleep(1.5); st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao redefinir a senha: {e}")
                        finally:
                            if 'cursor' in locals(): cursor.close()
                            if 'conn' in locals(): conn.close()

            @st.dialog("🗑️ Excluir Usuário")
            def modal_excluir_usuario(usuario_alvo):
                st.warning(f"Tem certeza que deseja excluir permanentemente o usuário **{usuario_alvo}**?")
                if usuario_alvo == st.session_state.usuario_logado:
                    st.error("⛔ Você não pode excluir a sua própria conta enquanto estiver logado.")
                else:
                    col_sim, col_nao = st.columns(2)
                    with col_sim:
                        if st.button("✅ Sim, Excluir", type="primary", use_container_width=True):
                            conn = conectar_bd()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM utilizadores WHERE usuario = %s", (usuario_alvo,))
                            cursor.execute("DELETE FROM historico_senhas WHERE usuario = %s", (usuario_alvo,))
                            conn.commit()
                            registrar_auditoria(st.session_state.usuario_logado, f"Excluiu o usuário '{usuario_alvo}'")
                            conn.close()
                            st.success(f"✅ Usuário excluído!")
                            time.sleep(1.5); st.rerun()
                    with col_nao:
                        if st.button("❌ Cancelar", use_container_width=True):
                            st.rerun()

            st.markdown("---")
            st.subheader("📋 Usuários Registados")
            conn = conectar_bd()
            df_users = pd.read_sql_query("SELECT id_utilizador, usuario, perfil FROM utilizadores ORDER BY id_utilizador", conn)
            conn.close()

            if not df_users.empty:
                col_h1, col_h2, col_h3, col_h4 = st.columns([1, 3, 2, 2])
                col_h1.markdown("**ID**")
                col_h2.markdown("**Login**")
                col_h3.markdown("**Acesso**")
                col_h4.markdown("**Ações**")
                st.markdown("---")
                
                for index, row in df_users.iterrows():
                    uid = row['id_utilizador']
                    ulogin = row['usuario']
                    uperfil = row['perfil']
                    
                    c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                    c1.write(f"#{uid}")
                    c2.write(f"👤 {ulogin}")
                    
                    if uperfil == 'admin':
                        c3.markdown("🛡️ `Admin`")
                    else:
                        c3.markdown("💼 `Operacional`")
                    
                    btn_c1, btn_c2 = c4.columns(2)
                    with btn_c1:
                        if st.button("🔑", key=f"pwd_{uid}", help=f"Redefinir senha de {ulogin}"):
                            modal_alterar_senha_usuario(ulogin)
                    with btn_c2:
                        if st.button("🗑️", key=f"del_{uid}", help=f"Excluir {ulogin}"):
                            modal_excluir_usuario(ulogin)
                            
                    st.markdown("<hr style='margin: 0px; opacity: 0.2;'>", unsafe_allow_html=True)
            else:
                st.info("Nenhum usuário encontrado.")