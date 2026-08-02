import streamlit as st
import pandas as pd
from core.database import conectar_bd

def render():
    st.title("🕵️‍♂️ Registo de Auditoria do Sistema")
    st.markdown("Este painel é estritamente informativo e de segurança. Acompanhe todas as ações sensíveis realizadas pelos utilizadores no ERP Limplex.")

    conn = conectar_bd()
    try:
        df_auditoria = pd.read_sql_query('''
            SELECT data_hora as "Data e Hora", 
                   usuario as "Utilizador Responsável", 
                   acao as "Descrição da Ação",
                   estacao as "Computador / Estação",
                   ip as "Endereço IP"
            FROM auditoria
            ORDER BY data_hora DESC
            LIMIT 500
        ''', conn)
        
        if df_auditoria.empty:
            st.info("ℹ️ Nenhum registo de auditoria encontrado até ao momento.")
        else:
            st.dataframe(
                df_auditoria, 
                use_container_width=True, 
                height=600,
                hide_index=True
            )
            st.caption("A exibir os últimos 500 registos de segurança do sistema.")
            
    except Exception as e:
        st.error(f"⚠️ Erro ao carregar os registos de auditoria. Detalhes técnicos: {e}")
    finally:
        conn.close()