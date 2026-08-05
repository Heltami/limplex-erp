import streamlit as st
import pandas as pd
import time
from datetime import datetime

from core.utils import registrar_auditoria
from core.pdf_generator import (
    gerar_pdf_pedido_mestre, gerar_pdf_pedido_fornecedor, gerar_pdf_pickup_entrega
)

# IMPORTA O NOVO REPOSITÓRIO!
from repositories import compras_repo

def render():
    st.title("📦 Central de Compras e Logística")
    st.markdown("Reúna todas as vendas confirmadas (Fase: **Pedido**) para gerar as **Ordens de Compra** aos Fornecedores e organizar a logística de entrega.")
    
    # 1. Puxa os dados da empresa via repositório
    empresa_dados = compras_repo.obter_dados_empresa()

    aba_cons1, aba_cons2 = st.tabs(["⏳ 1. Compras Pendentes (A Consolidar)", "🚚 2. Logística Operacional (Lote Consolidado)"])

    # ==========================================
    # ABA 1: ITENS PENDENTES DE PEDIDO AO FORNECEDOR
    # ==========================================
    with aba_cons1:
        st.subheader("Itens Pendentes de Compra (Baseado nas Vendas)")
        
        # 2. Busca itens para o saco azul via repositório
        df_cons = compras_repo.listar_itens_pendentes_compra()
        
        if df_cons.empty:
            st.info("ℹ️ Nenhum item pendente. Altere o status dos orçamentos para 'Pedido' no Módulo de Vendas.")
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
                
                # Nomenclatura Oficial: Pedido Mestre
                st.download_button(
                    label="📄 Pedido Mestre (Todos)",
                    data=pdf_mestre,
                    file_name=f"MESTRE_LIMPLEX_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    help="Documento interno contendo a soma de todos os fornecedores."
                )
                
            with c_indiv:
                st.markdown("**2. Enviar ao Fornecedor**")
                fornecedores_unicos = df_cons['Fornecedor'].fillna("SEM_FORNECEDOR").unique().tolist()
                
                forn_selecionado = st.selectbox("Escolha o Fornecedor:", fornecedores_unicos, label_visibility="collapsed")
                
                if forn_selecionado:
                    df_forn_especifico = df_cons[df_cons['Fornecedor'].fillna("SEM_FORNECEDOR") == forn_selecionado]
                    pdf_fornecedor = gerar_pdf_pedido_fornecedor(
                        fornecedor_nome=forn_selecionado, 
                        df_forn=df_forn_especifico, 
                        empresa_info=empresa_dados, 
                        usuario_emissao=st.session_state.get('usuario_logado', 'Sistema')
                    )
                    
                    # Nomenclatura Oficial: Ordem de Compra
                    nome_ficheiro_forn = str(forn_selecionado).replace(" ", "_").upper()
                    st.download_button(
                        label=f"📄 Gerar Ordem: {forn_selecionado}",
                        data=pdf_fornecedor,
                        file_name=f"ORDEM_{nome_ficheiro_forn}_LIMPLEX_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary"
                    )
                
            with c_fecho:
                st.markdown("**3. Fechamento Mensal**")
                with st.popover("🚀 Consolidar Lote Operacional", use_container_width=True):
                    st.markdown("⚠️ **Atenção:** Ao confirmar, todos os 'Pedidos' passarão para o status **Consolidado**.")
                    if st.button("✔️ Sim, Fechar e Consolidar", use_container_width=True, key="btn_fechar_lote"):
                        sucesso, msg = compras_repo.consolidar_pedidos_pendentes()
                        if sucesso:
                            registrar_auditoria(st.session_state.usuario_logado, "Fechou o lote e consolidou todos os Pedidos.")
                            st.success("✅ Lote consolidado! Avance para a Aba 2.")
                            time.sleep(1.5); st.rerun()
                        else:
                            st.error(f"Erro na Base de Dados: {msg}")

    # ==========================================
    # ABA 2: LOGÍSTICA E ROTEIRIZAÇÃO (CONSOLIDADOS)
    # ==========================================
    with aba_cons2:
        st.subheader("Painel de Roteirização e Entregas (Lote Atual)")
        
        # 3. Busca pedidos consolidados via repositório
        df_peds_cons = compras_repo.listar_pedidos_consolidados()
        
        romaneio_lista = []
        for _, row in df_peds_cons.iterrows():
            pid = row['id_pedido']
            cli_id = row['ped_cliente_id']
            data_compacta = str(row['data_criacao'])[:10].replace("-", "")
            doc_formatado = f"CON{int(cli_id):03d}{data_compacta}{int(pid):03d}"

            def pegar_campo(*opcoes):
                for op in opcoes:
                    if op in row.index and pd.notna(row[op]) and str(row[op]).strip():
                        return str(row[op]).strip()
                return ""

            rua_val = pegar_campo('endereco_entrega', 'endereco', 'rua', 'logradouro')
            num_val = pegar_campo('numero', 'num', 'nº')
            bairro_val = pegar_campo('bairro', 'distrito')
            cid_val = pegar_campo('cidade', 'municipio')
            est_val = pegar_campo('estado', 'uf')

            partes_end = []
            if rua_val: partes_end.append(rua_val)
            if num_val: partes_end.append(f"Nº {num_val}")
            if bairro_val: partes_end.append(bairro_val)
            if cid_val and est_val: partes_end.append(f"{cid_val}/{est_val}")
            elif cid_val: partes_end.append(cid_val)

            end_final = ", ".join(partes_end) if partes_end else "Endereço não informado"

            contato_linhas = []
            nome_ct = pegar_campo('contato_principal', 'contato', 'responsavel')
            if nome_ct: contato_linhas.append(f"<b>Nome:</b> {nome_ct}")
            cargo_ct = pegar_campo('cargo', 'funcao')
            if cargo_ct: contato_linhas.append(f"<b>Cargo:</b> {cargo_ct}")
            tel_ct = pegar_campo('whatsapp_telefone', 'telefone', 'celular')
            if tel_ct: contato_linhas.append(f"<b>Tel/Wpp:</b> {tel_ct}")
            email_ct = pegar_campo('email')
            if email_ct: contato_linhas.append(f"<b>E-mail:</b> {email_ct}")

            info_contato_final = "<br/>".join(contato_linhas) if contato_linhas else "Não informado"

            dist_val = pegar_campo('distancia_km')
            if not dist_val: dist_val = "N/D"
            elif not dist_val.endswith("km"): dist_val += " km"

            tempo_val = pegar_campo('tempo_minutos')
            if not tempo_val: tempo_val = "N/D"
            elif not tempo_val.endswith("min"): tempo_val += " min"

            nome_cliente = pegar_campo('razao_social', 'nome_fantasia')
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
        
        # 4. Busca dados de Picking via repositório
        df_picking_raw = compras_repo.listar_picking_consolidados()

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
            st.info("ℹ️ Nenhum pedido no status 'Consolidado'. Certifique-se de avançar o lote na Aba 1 para que os pedidos apareçam aqui.")
        else:
            st.markdown("**📄 Documento Unificado: Separação (Picking) e Entrega**")
            st.caption("Um único documento contendo os dados de roteirização e os itens a separar por cliente.")
            
            pdf_unificado = gerar_pdf_pickup_entrega(
                df_romaneio=df_romaneio, 
                df_picking=df_picking, 
                empresa_info=empresa_dados, 
                usuario_emissao=st.session_state.get('usuario_logado', 'Sistema')
            )
            
            # Nomenclatura Oficial: Romaneio
            st.download_button(
                label="🚚 Baixar Documento de Separação e Entrega (PDF)", 
                data=pdf_unificado, 
                file_name=f"ROM_LIMPLEX_{datetime.now().strftime('%Y%m%d')}.pdf", 
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
                if st.button("✔️ Sim, Reverter Lote Inteiro", type="primary", key="btn_reverte_lote"):
                    sucesso, msg = compras_repo.reverter_lote_consolidado()
                    if sucesso:
                        registrar_auditoria(st.session_state.usuario_logado, "Reverteu o lote Consolidado para Pedido.")
                        st.success("✅ Lote revertido com sucesso! Volte à Aba 1.")
                        time.sleep(1.5); st.rerun()
                    else:
                        st.error(f"Erro na Base de Dados: {msg}")