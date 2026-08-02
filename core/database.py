import os
import psycopg2
import streamlit as st
from dotenv import load_dotenv
import warnings

# Oculta o aviso do Pandas no terminal para manter os logs limpos
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy.*')

load_dotenv()

# =============================================================================
# BLOCO 2: MOTOR DE DADOS (Conexão BD PostgreSQL)
# =============================================================================
def conectar_bd():
    """Conecta à base de dados usando a URL segura escondida no .env"""
    url_banco = os.getenv("DATABASE_URL")
    
    # Prevenção: Se a URL não for encontrada no .env, avisa e bloqueia a app
    if not url_banco:
        st.error("⚠️ URL do banco de dados não encontrada no ficheiro .env!")
        st.stop()
        
    return psycopg2.connect(url_banco)