# =============================================================================
# LIMPLEX ERP - ARQUIVO PRINCIPAL (ROTEADOR E AUTENTICAÇÃO)
# =============================================================================
# Este ficheiro é a "porta de entrada" do sistema. Ele não contém regras de 
# negócio profundas. A sua única função é configurar a página, validar quem 
# entra (Login) e encaminhar o utilizador para as telas corretas (Módulos).
# =============================================================================

# =============================================================================
# BLOCO 1: FUNDAÇÕES E CONFIGURAÇÕES GLOBAIS
# =============================================================================
import streamlit as st

# 1.1 Configuração Visual da Página (Deve ser SEMPRE o 1º comando Streamlit)
st.set_page_config(page_title="LIMPLEX ERP", page_icon="📦", layout="wide")

import pandas as pd
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 1.2 Configurações de Performance Pandas (Evita quebras ao carregar tabelas muito grandes)
pd.set_option("styler.render.max_elements", 1000000)

# 1.3 Carregamento das Variáveis de Ambiente Seguras (Ficheiro .env)
load_dotenv()


# =============================================================================
# BLOCO 2: IMPORTAÇÃO DA ARQUITETURA MODULAR
# =============================================================================
# Em vez de ter todo o código aqui, o sistema importa as funções de outros ficheiros.

# 2.1 Segurança (Hashes e Validações de Senha)
from seguranca import verificar_senha, validar_complexidade_senha, gerar_hash_senha

# 2.2 Core (Banco de Dados, Auditoria e Gerador de PDFs)
from core.database import conectar_bd
from core.utils import registrar_auditoria

# 2.3 Módulos (Telas do Sistema)
from modules import dashboard, clientes, fornecedores, produtos, vendas, compras, configuracoes, auditoria


# =============================================================================
# BLOCO 3: GESTÃO DE ESTADO (SESSION STATE INITIALIZATION)
# =============================================================================
# Prepara a memória do navegador antes de o utilizador tentar fazer qualquer coisa.
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.perfil_utilizador = ""
    st.session_state.usuario_logado = ""


# =============================================================================
# BLOCO 4: PORTAL DE ACESSO (LOGIN E SISTEMA ANTI-BRUTE-FORCE)
# =============================================================================
# Se o utilizador não estiver logado, exibe a tela de Login e esconde o resto.
if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.write("")
        st.write("")
        
        # Logótipo da Empresa (Se existir na pasta)
        if os.path.exists("marca0.png"):
            c_img1, c_img2, c_img3 = st.columns([1, 3, 1])
            with c_img2:
                st.image("marca0.png", width=500) 
        
        st.markdown("<h2 style='text-align: center;'>Portal Restrito - Limplex</h2>", unsafe_allow_html=True)
        
        # Formulário de Autenticação
        with st.form("login_form"):
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            
            if submit:
                try:
                    conn = conectar_bd()
                    cursor = conn.cursor()
                    cursor.execute("SELECT perfil, senha_hash, tentativas_falhas, bloqueado_ate, data_ultima_senha FROM utilizadores WHERE usuario = %s", (usuario_input,))
                    resultado = cursor.fetchone()
                    
                    if resultado:
                        perfil, hash_db, falhas, bloqueado_ate, data_senha = resultado
                        
                        # Tenta buscar regras de bloqueio nas configurações, se não conseguir, usa o padrão (5 falhas, 15 min)
                        try:
                            conn_cfg = conectar_bd()
                            df_reg = pd.read_sql_query("SELECT max_tentativas_bloqueio, tempo_bloqueio_min FROM configuracoes WHERE id = 1", conn_cfg)
                            conn_cfg.close()
                            max_tentativas = int(df_reg.iloc[0]['max_tentativas_bloqueio'])
                            tempo_blq_min = int(df_reg.iloc[0]['tempo_bloqueio_min'])
                        except:
                            max_tentativas = 5
                            tempo_blq_min = 15

                        # Verifica se a conta está sob castigo temporal
                        if bloqueado_ate and datetime.now() < bloqueado_ate:
                            tempo_restante = (bloqueado_ate - datetime.now()).seconds // 60
                            st.error(f"⛔ Conta bloqueada. Tente novamente em {tempo_restante + 1} minutos.")
                            registrar_auditoria(usuario_input, "Tentativa de login em conta bloqueada")
                            conn.close()
                            st.stop()

                        # Validação Dupla (Senha do Utilizador ou Senha Master de Emergência)
                        senha_valida = verificar_senha(senha_input, hash_db)
                        master_valida = os.getenv("MASTER_HASH") and verificar_senha(senha_input, os.getenv("MASTER_HASH"))

                        if senha_valida or master_valida:
                            # Login com Sucesso: Limpa as falhas
                            cursor.execute("UPDATE utilizadores SET tentativas_falhas = 0, bloqueado_ate = NULL WHERE usuario = %s", (usuario_input,))
                            conn.commit()
                            
                            st.session_state.autenticado = True
                            st.session_state.perfil_utilizador = 'admin' if master_valida else perfil
                            st.session_state.usuario_logado = usuario_input
                            st.session_state.ultima_atividade = time.time()
                            st.session_state.data_ultima_senha = data_senha
                            
                            tipo_login = "Login via Senha Master" if master_valida else "Login efetuado com sucesso"
                            registrar_auditoria(usuario_input, tipo_login)
                            
                            if master_valida: st.warning("⚠️ Login efetuado via Senha Master de Emergência.")
                            conn.close()
                            st.rerun()
                        else:
                            # Falha no Login: Incrementa o contador de erros
                            novas_falhas = falhas + 1
                            if novas_falhas >= max_tentativas:
                                tempo_bloqueio = datetime.now() + timedelta(minutes=tempo_blq_min)
                                cursor.execute("UPDATE utilizadores SET tentativas_falhas = %s, bloqueado_ate = %s WHERE usuario = %s", (novas_falhas, tempo_bloqueio, usuario_input))
                                registrar_auditoria(usuario_input, f"Conta BLOQUEADA ({max_tentativas} tentativas falhas)")
                                st.error(f"⛔ Conta bloqueada por segurança. Aguarde {tempo_blq_min} minutos.")
                            else:
                                cursor.execute("UPDATE utilizadores SET tentativas_falhas = %s WHERE usuario = %s", (novas_falhas, usuario_input))
                                registrar_auditoria(usuario_input, f"Falha de Login ({novas_falhas}/{max_tentativas})")
                                st.error(f"⚠️ Palavra-passe incorreta! Tentativa {novas_falhas} de {max_tentativas}.")
                            conn.commit()
                            conn.close()
                    else:
                        st.error("⚠️ Utilizador não encontrado.")
                        registrar_auditoria(usuario_input, "Tentativa de login - Utilizador inexistente")
                        conn.close()
                except Exception as e:
                    st.error(f"Erro no sistema de acesso: {e}")
    st.stop() # Interrompe a renderização para não mostrar o resto da aplicação


# =============================================================================
# BLOCO 5: AMBIENTE AUTENTICADO E NAVEGAÇÃO LATERAL (SIDEBAR)
# =============================================================================

# 5.1 GESTÃO DE TIMEOUT (Inatividade de 30 minutos faz Logout Automático)
if st.session_state.autenticado:
    if 'ultima_atividade' in st.session_state:
        tempo_inativo = time.time() - st.session_state.ultima_atividade
        if tempo_inativo > 1800: # 1800 segundos = 30 minutos
            registrar_auditoria(st.session_state.usuario_logado, "Logout Automático (Inatividade de 30 min)")
            st.session_state.autenticado = False
            st.session_state.usuario_logado = ""
            st.rerun()
    st.session_state.ultima_atividade = time.time()

# 5.2 VERIFICAÇÃO DE VALIDADE DA SENHA
try:
    conn = conectar_bd()
    cfg = pd.read_sql_query("SELECT senha_validade_dias FROM configuracoes WHERE id = 1", conn).iloc[0]
    validade_dias = int(cfg['senha_validade_dias'])
    conn.close()
    
    if st.session_state.get('data_ultima_senha'):
        dias_passados = (datetime.now() - st.session_state.data_ultima_senha).days
        if dias_passados >= validade_dias:
            st.warning(f"⚠️ A sua palavra-passe expirou (mais de {validade_dias} dias). Por favor, altere-a agora no menu lateral '🔑 Senha'.", icon="🚨")
except:
    pass

# 5.3 COMPONENTES VISUAIS (Janelas Flutuantes de Ação)
@st.dialog("🔑 Alterar Palavra-passe")
def modal_alterar_senha():
    st.info(f"A atualizar credenciais de: **{st.session_state.usuario_logado}**")
    senha_atual = st.text_input("Palavra-passe Atual", type="password")
    nova_senha = st.text_input("Nova Palavra-passe (Min. 12 chars, Mistas, Números, Símbolos)", type="password")
    nova_senha_conf = st.text_input("Confirmar Nova Palavra-passe", type="password")
    
    if st.button("🔄 Confirmar Alteração", type="primary", use_container_width=True):
        if nova_senha != nova_senha_conf:
            st.error("⚠️ As novas palavras-passe não coincidem!")
        else:
            valida, msg = validar_complexidade_senha(nova_senha)
            if not valida:
                st.error(f"⚠️ {msg}")
            else:
                conn = conectar_bd()
                cursor = conn.cursor()
                cursor.execute("SELECT senha_hash FROM utilizadores WHERE usuario = %s", (st.session_state.usuario_logado,))
                res = cursor.fetchone()
                hash_guardado = res[0] if res else ""
                
                if verificar_senha(senha_atual, hash_guardado) or (os.getenv("MASTER_HASH") and verificar_senha(senha_atual, os.getenv("MASTER_HASH"))):
                    novo_hash = gerar_hash_senha(nova_senha)
                    cursor.execute("UPDATE utilizadores SET senha_hash = %s, data_ultima_senha = CURRENT_TIMESTAMP WHERE usuario = %s", (novo_hash, st.session_state.usuario_logado))
                    conn.commit()
                    registrar_auditoria(st.session_state.usuario_logado, "Palavra-passe alterada pelo utilizador")
                    conn.close()
                    st.success("✅ Palavra-passe atualizada com sucesso!")
                    st.session_state.data_ultima_senha = datetime.now()
                    import time; time.sleep(1.5)
                    st.rerun()
                else:
                    conn.close()
                    st.error("⚠️ A palavra-passe atual está incorreta!")

@st.dialog("🚪 Confirmar Saída")
def modal_confirmar_saida():
    st.warning("Tem a certeza que deseja terminar a sessão e sair do sistema?")
    col_sim, col_nao = st.columns(2, gap="medium")
    with col_sim:
        if st.button("✅ Sim, Sair", use_container_width=True):
            registrar_auditoria(st.session_state.usuario_logado, "Logout Manual")
            st.session_state.autenticado = False
            st.session_state.usuario_logado = ""
            st.rerun()
    with col_nao:
        if st.button("❌ Cancelar", type="primary", use_container_width=True):
            st.rerun()

# 5.4 MENU LATERAL (SIDEBAR)
if os.path.exists("marca0.png"):
    st.sidebar.image("marca0.png", use_container_width=True)
else:
    st.sidebar.title("📦 LIMPLEX ERP")

st.sidebar.markdown("---")
st.sidebar.markdown(f"👤 **{st.session_state.usuario_logado}** (*{st.session_state.perfil_utilizador}*)")

col_btn_senha, col_btn_sair = st.sidebar.columns([1, 1], gap="small")
with col_btn_senha:
    if st.button("🔑 Senha", use_container_width=True):
        modal_alterar_senha()
with col_btn_sair:
    if st.button("🚪 Sair", use_container_width=True):
        modal_confirmar_saida()

st.sidebar.markdown("---")
st.sidebar.title("Navegação Principal")

# O Streamlit guarda aqui qual é a opção selecionada pelo utilizador
menu = st.sidebar.radio(
    "Selecione um módulo:",
    ["Dashboard", "Clientes", "Fornecedores", "Produtos", "Vendas", "Compras", "Configurações", "Auditoria"]
)


# =============================================================================
# BLOCO 6: ROTEADOR DE MÓDULOS (O Coração da Navegação)
# =============================================================================
# Consoante o clique no menu lateral, o app.py "chama" o ficheiro correto na pasta modules/

if menu == "Dashboard":
    dashboard.render()

elif menu == "Clientes":
    clientes.render()

elif menu == "Fornecedores":
    fornecedores.render()

elif menu == "Produtos":
    produtos.render()

elif menu == "Vendas":
    vendas.render()

elif menu == "Compras":
    compras.render()

elif menu == "Configurações":
    configuracoes.render()

elif menu == "Auditoria":
    auditoria.render()

# FIM DA APLICAÇÃO
# =============================================================================