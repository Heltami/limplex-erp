import io
import os
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# =============================================================================
# MOTOR DE GERAÇÃO DE PDFs (3 FUNÇÕES DISTINTAS)
# =============================================================================

# --- 6.1 (B) PDF PEDIDO MESTRE GLOBAL DE COMPRAS ---
def gerar_pdf_pedido_mestre(df_cons, empresa_info=None, usuario_emissao=None):
    if empresa_info is None: empresa_info = {}
    if not usuario_emissao: usuario_emissao = "Sistema"
        
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor("#0f4c81"))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#555555"), leading=11)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#0f4c81"))
    forn_style = ParagraphStyle('FornStyle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#0f4c81"), spaceBefore=12, spaceAfter=6)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#333333"), leading=11)
    th_style = ParagraphStyle('ThStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.white)
    footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#666666"), leading=11, alignment=1)

    razao_empresa = empresa_info.get('razao_social', 'LIMPLEX DISTRIBUIDORA B2B LTDA')
    cnpj_empresa = empresa_info.get('cnpj', '26.644.910/0001-09')
    end_empresa = empresa_info.get('endereco', empresa_info.get('rua', 'Endereço LIMPLEX não cadastrado em Configurações'))

    texto_cabecalho = Paragraph(f"<b>LIMPLEX DISTRIBUIDORA</b><br/>Soluções em Produtos de Limpeza<br/><b>{razao_empresa}</b> | CNPJ: {cnpj_empresa}", subtitle_style)
    
    if os.path.exists("marca.PNG"):
        try:
            img = Image("marca.PNG", width=80, height=45)
            img.hAlign = 'LEFT'
            t_cabecalho = Table([[img, texto_cabecalho]], colWidths=[90, 440])
        except:
            t_cabecalho = Table([[Paragraph("<b>LIMPLEX</b>", title_style), texto_cabecalho]], colWidths=[90, 440])
    else:
        t_cabecalho = Table([[Paragraph("<b>LIMPLEX</b>", title_style), texto_cabecalho]], colWidths=[90, 440])
        
    t_cabecalho.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 0)]))
    story.append(t_cabecalho)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f4c81"), spaceAfter=10))

    story.append(Paragraph("<b>PEDIDO MESTRE DE COMPRAS — CONSOLIDAÇÃO CROSS-DOCKING</b>", header_style))
    story.append(Spacer(1, 10))

    fornecedores_unicos = df_cons['Fornecedor'].fillna("SEM FORNECEDOR DEFINIDO").unique()
    grand_total_custo = 0.0

    for forn in fornecedores_unicos:
        df_forn = df_cons[df_cons['Fornecedor'].fillna("SEM FORNECEDOR DEFINIDO") == forn]
        story.append(Paragraph(f"🏢 <b>FORNECEDOR: {str(forn).upper()}</b>", forn_style))
        
        table_data = [[Paragraph("Código", th_style), Paragraph("Descrição do Produto", th_style), Paragraph("Qtd Total", th_style), Paragraph("Custo Unit.", th_style), Paragraph("Custo Total", th_style)]]
        
        subtotal_forn = 0.0
        for _, row in df_forn.iterrows():
            qtd = int(row['Qtd Total'])
            c_unit = float(row['Custo Unitário'])
            c_tot = float(row['Custo Total'])
            subtotal_forn += c_tot
            table_data.append([Paragraph(str(row.get('Código', 'N/D')), normal_style), Paragraph(str(row['Produto']), normal_style), Paragraph(str(qtd), normal_style), Paragraph(f"R$ {c_unit:.2f}", normal_style), Paragraph(f"R$ {c_tot:.2f}", normal_style)])
            
        grand_total_custo += subtotal_forn
        table_data.append([Paragraph(f"<b>SUBTOTAL {str(forn).upper()}</b>", normal_style), "", "", "", Paragraph(f"<b>R$ {subtotal_forn:.2f}</b>", normal_style)])
        
        t_forn = Table(table_data, colWidths=[65, 245, 55, 80, 85])
        t_forn.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f4c81")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('PADDING', (0,0), (-1,-1), 5), ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor("#e0e0e0")), ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f0f4f8")), ('SPAN', (0,-1), (3,-1)), ('ALIGN', (2,0), (-1,-1), 'CENTER')]))
        story.append(t_forn)
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 5))
    story.append(Paragraph(f"<b>TOTAL GERAL DO LOTE DE COMPRAS: R$ {grand_total_custo:.2f}</b>", header_style))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=10))

    data_hora_emissao = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
    texto_rodape = f"LIMPLEX DISTRIBUIDORA B2B — Soluções em Produtos de Limpeza<br/>Razão Social: {razao_empresa} | CNPJ: {cnpj_empresa} | Endereço: {end_empresa}<br/>Emitido por: <b>{usuario_emissao}</b> em {data_hora_emissao} | Módulo de Compras Limplex"
    story.append(Paragraph(texto_rodape, footer_style))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# --- 6.1 (C) PDF DE ORÇAMENTO / PEDIDO INDIVIDUAL PARA O CLIENTE ---
def gerar_pdf_pedido(pedido_id=None, cliente_nome="", df_itens=None, valor_total=0.0, empresa_info=None, usuario_emissao=None, pedido_id_str=None, cliente_cnpj="", cliente_end="", data_pedido="", cond_pag="", **kwargs):
    if empresa_info is None: empresa_info = {}
    if not usuario_emissao: usuario_emissao = "Sistema"
    
    # 1. RECUPERAÇÃO DO DATAFRAME (Saco Azul Inteligente)
    if df_itens is None or (isinstance(df_itens, pd.DataFrame) and df_itens.empty):
        if 'df_itens_pedido' in kwargs: df_itens = kwargs['df_itens_pedido']
        elif 'df_produtos' in kwargs: df_itens = kwargs['df_produtos']
        else:
            for v in kwargs.values():
                if isinstance(v, pd.DataFrame) and not v.empty:
                    df_itens = v; break

    if valor_total == 0.0 or valor_total is None:
        if 'valor_pedido' in kwargs: valor_total = kwargs['valor_pedido']
        elif 'total' in kwargs: valor_total = kwargs['total']
        else:
            for k, v in kwargs.items():
                if ('valor' in k.lower() or 'total' in k.lower()) and isinstance(v, (int, float)):
                    valor_total = float(v); break
    try: valor_total = float(valor_total)
    except: valor_total = 0.0

    exibir_id = pedido_id_str if pedido_id_str else str(pedido_id)
        
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor("#0f4c81"))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#555555"), leading=11)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#0f4c81"))
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#333333"), leading=11)
    th_style = ParagraphStyle('ThStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.white)
    footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#666666"), leading=11, alignment=1)

    razao_empresa = empresa_info.get('razao_social', 'LIMPLEX DISTRIBUIDORA B2B LTDA')
    cnpj_empresa = empresa_info.get('cnpj', '26.644.910/0001-09')
    end_empresa = empresa_info.get('endereco', empresa_info.get('rua', 'Endereço LIMPLEX não cadastrado em Configurações'))

    texto_cabecalho = Paragraph(f"<b>LIMPLEX DISTRIBUIDORA</b><br/>Soluções em Produtos de Limpeza<br/><b>{razao_empresa}</b> | CNPJ: {cnpj_empresa}", subtitle_style)
    
    if os.path.exists("marca.PNG"):
        try:
            img = Image("marca.PNG", width=80, height=45)
            img.hAlign = 'LEFT'
            t_cabecalho = Table([[img, texto_cabecalho]], colWidths=[90, 440])
        except:
            t_cabecalho = Table([[Paragraph("<b>LIMPLEX</b>", title_style), texto_cabecalho]], colWidths=[90, 440])
    else:
        t_cabecalho = Table([[Paragraph("<b>LIMPLEX</b>", title_style), texto_cabecalho]], colWidths=[90, 440])
        
    t_cabecalho.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 0)]))
    story.append(t_cabecalho)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f4c81"), spaceAfter=10))

    story.append(Paragraph(f"<b>PROPOSTA COMERCIAL #{exibir_id}</b>", header_style))
    
    info_pedido = []
    if data_pedido and str(data_pedido).strip(): info_pedido.append(f"<b>Data:</b> {str(data_pedido)[:10]}")
    if cond_pag and str(cond_pag).strip(): info_pedido.append(f"<b>Pagamento:</b> {str(cond_pag).strip()}")
    if info_pedido: story.append(Paragraph(" | ".join(info_pedido), normal_style))
        
    story.append(Spacer(1, 5))
    
    texto_cliente = f"<b>Cliente:</b> {str(cliente_nome).upper()}"
    if cliente_cnpj and str(cliente_cnpj).strip(): texto_cliente += f" | <b>CNPJ:</b> {str(cliente_cnpj).strip()}"
    story.append(Paragraph(texto_cliente, normal_style))
    
    if cliente_end and str(cliente_end).strip() and str(cliente_end).strip() != "Endereço não informado":
        story.append(Paragraph(f"<b>Endereço de Entrega:</b> {str(cliente_end).strip()}", normal_style))
        
    story.append(Spacer(1, 10))

    table_data = [[Paragraph("Produto / Descrição", th_style), Paragraph("Qtd", th_style), Paragraph("Preço Unit.", th_style), Paragraph("Subtotal", th_style)]]
    
    calc_total = 0.0
    if df_itens is not None and not df_itens.empty:
        for _, row in df_itens.iterrows():
            
            # CAÇADOR ABSOLUTO DE PRODUTO
            prod_desc = "Produto N/D"
            for c in row.index:
                c_str = str(c).lower()
                if 'desc' in c_str or 'prod' in c_str or 'nome' in c_str:
                    if pd.notna(row[c]) and str(row[c]).strip() != "":
                        prod_desc = str(row[c])
                        break
            
            # CAÇADOR DE QUANTIDADE
            qtd_val = 1
            for c in row.index:
                if 'qtd' in str(c).lower() or 'quant' in str(c).lower():
                    if pd.notna(row[c]): qtd_val = row[c]; break
            try: qtd = int(qtd_val)
            except: qtd = 1
            
            # CAÇADOR DE PREÇO
            preco_val = 0.0
            for c in row.index:
                if 'pre' in str(c).lower() or 'unit' in str(c).lower() or 'valor' in str(c).lower():
                    if pd.notna(row[c]): preco_val = row[c]; break
            try: preco = float(preco_val)
            except: preco = 0.0
            
            # CAÇADOR DE SUBTOTAL
            sub_val = qtd * preco
            for c in row.index:
                if 'sub' in str(c).lower() or 'tot' in str(c).lower():
                    if pd.notna(row[c]): sub_val = row[c]; break
            try: subtotal = float(sub_val)
            except: subtotal = qtd * preco
            
            calc_total += subtotal
            table_data.append([
                Paragraph(str(prod_desc), normal_style), 
                Paragraph(str(qtd), normal_style), 
                Paragraph(f"R$ {preco:.2f}", normal_style), 
                Paragraph(f"R$ {subtotal:.2f}", normal_style)
            ])
        
    if valor_total <= 0 and calc_total > 0:
        valor_total = calc_total
        
    table_data.append([Paragraph("<b>VALOR TOTAL DO PEDIDO</b>", normal_style), "", "", Paragraph(f"<b>R$ {float(valor_total):.2f}</b>", normal_style)])
    
    t_ped = Table(table_data, colWidths=[275, 55, 100, 105])
    t_ped.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f4c81")), 
        ('TEXTCOLOR', (0,0), (-1,0), colors.white), 
        ('PADDING', (0,0), (-1,-1), 5), 
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor("#e0e0e0")), 
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f0f4f8")), 
        ('SPAN', (0,-1), (2,-1)), 
        ('ALIGN', (1,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_ped)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=10))

    data_hora_emissao = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
    texto_rodape = f"LIMPLEX DISTRIBUIDORA B2B — Soluções em Produtos de Limpeza<br/>Razão Social: {razao_empresa} | CNPJ: {cnpj_empresa} | Endereço: {end_empresa}<br/>Emitido por: <b>{usuario_emissao}</b> em {data_hora_emissao}"
    story.append(Paragraph(texto_rodape, footer_style))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- 6.2 (B) PDF ORDEM DE COMPRA INDIVIDUAL POR FORNECEDOR ---
def gerar_pdf_pedido_fornecedor(fornecedor_nome, df_forn, empresa_info=None, usuario_emissao=None):
    if empresa_info is None: empresa_info = {}
    if not usuario_emissao: usuario_emissao = "Sistema"
        
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor("#0f4c81"))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#555555"), leading=11)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#0f4c81"))
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#333333"), leading=11)
    th_style = ParagraphStyle('ThStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.white)
    footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#666666"), leading=11, alignment=1)

    razao_empresa = empresa_info.get('razao_social', 'LIMPLEX DISTRIBUIDORA B2B LTDA')
    cnpj_empresa = empresa_info.get('cnpj', '26.644.910/0001-09')
    end_empresa = empresa_info.get('endereco', empresa_info.get('rua', 'Endereço LIMPLEX não cadastrado em Configurações'))

    texto_cabecalho = Paragraph(f"<b>LIMPLEX DISTRIBUIDORA</b><br/>Soluções em Produtos de Limpeza<br/><b>{razao_empresa}</b> | CNPJ: {cnpj_empresa}", subtitle_style)
    
    if os.path.exists("marca.PNG"):
        try:
            img = Image("marca.PNG", width=80, height=45)
            img.hAlign = 'LEFT'
            t_cabecalho = Table([[img, texto_cabecalho]], colWidths=[90, 440])
        except:
            t_cabecalho = Table([[Paragraph("<b>LIMPLEX</b>", title_style), texto_cabecalho]], colWidths=[90, 440])
    else:
        t_cabecalho = Table([[Paragraph("<b>LIMPLEX</b>", title_style), texto_cabecalho]], colWidths=[90, 440])
        
    t_cabecalho.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 0)]))
    story.append(t_cabecalho)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f4c81"), spaceAfter=10))

    story.append(Paragraph(f"<b>ORDEM DE COMPRA — FORNECEDOR: {str(fornecedor_nome).upper()}</b>", header_style))
    story.append(Spacer(1, 10))

    table_data = [[Paragraph("Código", th_style), Paragraph("Descrição do Produto", th_style), Paragraph("Qtd Total", th_style), Paragraph("Custo Unit.", th_style), Paragraph("Custo Total", th_style)]]
    
    subtotal_forn = 0.0
    for _, row in df_forn.iterrows():
        qtd = int(row['Qtd Total'])
        c_unit = float(row['Custo Unitário'])
        c_tot = float(row['Custo Total'])
        subtotal_forn += c_tot
        table_data.append([
            Paragraph(str(row.get('Código', 'N/D')), normal_style), 
            Paragraph(str(row['Produto']), normal_style), 
            Paragraph(str(qtd), normal_style), 
            Paragraph(f"R$ {c_unit:.2f}", normal_style), 
            Paragraph(f"R$ {c_tot:.2f}", normal_style)
        ])
        
    table_data.append([Paragraph(f"<b>TOTAL A PAGAR AO FORNECEDOR</b>", normal_style), "", "", "", Paragraph(f"<b>R$ {subtotal_forn:.2f}</b>", normal_style)])
    
    t_forn = Table(table_data, colWidths=[65, 245, 55, 80, 85])
    t_forn.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f4c81")), 
        ('TEXTCOLOR', (0,0), (-1,0), colors.white), 
        ('PADDING', (0,0), (-1,-1), 5), 
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor("#e0e0e0")), 
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#e9ecef")), 
        ('SPAN', (0,-1), (3,-1)), 
        ('ALIGN', (2,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_forn)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=10))

    data_hora_emissao = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
    texto_rodape = f"LIMPLEX DISTRIBUIDORA B2B — Soluções em Produtos de Limpeza<br/>Razão Social: {razao_empresa} | CNPJ: {cnpj_empresa} | Endereço: {end_empresa}<br/>Emitido por: <b>{usuario_emissao}</b> em {data_hora_emissao}"
    story.append(Paragraph(texto_rodape, footer_style))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- 6.3 PDF MÓDULO 6 (DOCUMENTO UNIFICADO: SEPARAÇÃO E ENTREGA COM CONTATO COMPLETO) ---
def gerar_pdf_pickup_entrega(df_romaneio, df_picking, empresa_info=None, usuario_emissao=None):
    if empresa_info is None: empresa_info = {}
    if not usuario_emissao: usuario_emissao = "Sistema"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor("#0f4c81"))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#555555"), leading=11)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#0f4c81"))
    cli_title_style = ParagraphStyle('CliTitleStyle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#0f4c81"), spaceBefore=15, spaceAfter=5)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#333333"), leading=11)
    th_style = ParagraphStyle('ThStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)
    footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#666666"), leading=11, alignment=1)

    razao_empresa = empresa_info.get('razao_social', 'LIMPLEX DISTRIBUIDORA B2B LTDA')
    cnpj_empresa = empresa_info.get('cnpj', '26.644.910/0001-09')
    end_empresa = empresa_info.get('endereco', empresa_info.get('rua', empresa_info.get('logradouro', 'Endereço LIMPLEX não cadastrado em Configurações')))

    texto_cabecalho = Paragraph(
        f"<b>LIMPLEX DISTRIBUIDORA</b><br/>"
        f"Soluções em Produtos de Limpeza e Higienização Profissional<br/>"
        f"<b>{razao_empresa}</b> | CNPJ: {cnpj_empresa}",
        subtitle_style
    )

    if os.path.exists("marca.PNG"):
        try:
            img = Image("marca.PNG", width=80, height=45)
            img.hAlign = 'LEFT'
            t_cabecalho = Table([[img, texto_cabecalho]], colWidths=[90, 445])
        except:
            t_cabecalho = Table([[Paragraph("<b>LIMPLEX</b>", title_style), texto_cabecalho]], colWidths=[90, 445])
    else:
        t_cabecalho = Table([[Paragraph("<b>LIMPLEX</b>", title_style), texto_cabecalho]], colWidths=[90, 445])

    t_cabecalho.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 0)]))
    story.append(t_cabecalho)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f4c81"), spaceAfter=10))

    story.append(Paragraph("<b>DOCUMENTO UNIFICADO: SEPARAÇÃO (PICKING) E ROTEIRIZAÇÃO DE ENTREGAS</b>", header_style))
    story.append(Spacer(1, 5))

    total_geral = 0.0

    for _, row_rom in df_romaneio.iterrows():
        id_ped = row_rom["ID Pedido"]
        cliente = str(row_rom["Cliente"]).upper()
        endereco = str(row_rom["Endereço de Entrega"])
        contato_info = str(row_rom.get("Contato Info", "Não informado"))
        dist = str(row_rom.get("Distância", "N/D"))
        tempo = str(row_rom.get("Tempo", "N/D"))
        valor = float(row_rom["Valor a Receber"])
        total_geral += valor

        # Cabeçalho do Cliente
        story.append(Paragraph(f"📦 <b>PEDIDO #{id_ped} — CLIENTE: {cliente}</b>", cli_title_style))

        # Quadro de Entrega com Endereço e Contato Detalhado
        info_entrega = [
            [
                Paragraph(f"<b>Endereço de Entrega:</b><br/>{endereco}", normal_style),
                Paragraph(f"<b>Contato na Empresa:</b><br/>{contato_info}", normal_style),
                Paragraph(f"<b>Logística & Cobrança:</b><br/>📏 Rota: {dist} ({tempo})<br/><b>Cobrar: R$ {valor:.2f}</b>", normal_style)
            ]
        ]
        t_info = Table(info_entrega, colWidths=[230, 155, 150])
        t_info.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8f9fa")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        story.append(t_info)
        story.append(Spacer(1, 8))

        # Tabela de Picking de Produtos
        df_itens = df_picking[df_picking["Nº Pedido"] == id_ped]
        
        table_itens = [[Paragraph("OK", th_style), Paragraph("Descrição do Produto", th_style), Paragraph("Qtd", th_style)]]
        for _, item_row in df_itens.iterrows():
            table_itens.append([
                Paragraph("<font size=12>☐</font>", normal_style),
                Paragraph(str(item_row['Produto']), normal_style),
                Paragraph(f"<b>{item_row['Qtd']}</b>", normal_style)
            ])

        t_itens = Table(table_itens, colWidths=[30, 445, 60])
        t_itens.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f4c81")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('PADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),
            ('ALIGN', (2,0), (2,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        story.append(t_itens)
        story.append(Spacer(1, 15))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=10))

    # Resumo Final de Valores
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"<b>TOTAL GERAL A COBRAR NA ROTA: R$ {total_geral:.2f}</b>", header_style))
    story.append(Spacer(1, 15))

    # Rodapé Institucional
    data_hora_emissao = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
    linha1 = "LIMPLEX DISTRIBUIDORA B2B — Soluções em Produtos de Limpeza e Higienização Profissional"
    linha2 = f"Razão Social: {razao_empresa} | CNPJ: {cnpj_empresa}"
    linha3 = f"Endereço Matriz: <b>{end_empresa}</b>"
    linha4 = f"Emitido por: <b>{usuario_emissao}</b> em {data_hora_emissao} | Módulo de Logística Cross-Docking"
    
    texto_rodape = f"{linha1}<br/>{linha2}<br/>{linha3}<br/>{linha4}"
    story.append(Paragraph(texto_rodape, footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- 6.4 PDF RELATÓRIO INTERNO DE PRODUTOS ---
def gerar_pdf_produtos_interno(df_dados):
    buffer_pdf = io.BytesIO()
    doc = SimpleDocTemplate(buffer_pdf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story_pdf = []
    styles_pdf = getSampleStyleSheet()

    title_s = ParagraphStyle('TitleStyle', parent=styles_pdf['Heading1'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#0f4c81"))
    sub_s = ParagraphStyle('SubStyle', parent=styles_pdf['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#555555"), leading=11)
    th_s = ParagraphStyle('ThStyle', parent=styles_pdf['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)
    td_s = ParagraphStyle('TdStyle', parent=styles_pdf['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#333333"), leading=10)
    footer_s = ParagraphStyle('FooterStyle', parent=styles_pdf['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#666666"), alignment=1)

    story_pdf.append(Paragraph("<b>LIMPLEX DISTRIBUIDORA B2B</b>", title_s))
    story_pdf.append(Paragraph(f"Relatório Interno de Catálogo Selecionado | Emitido em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", sub_s))
    story_pdf.append(Spacer(1, 10))
    story_pdf.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f4c81"), spaceAfter=10))

    table_pdf_data = [[
        Paragraph("SKU", th_s), Paragraph("Descrição", th_s), Paragraph("Fornecedor", th_s), 
        Paragraph("Custo", th_s), Paragraph("Varejo", th_s), Paragraph("Limplex", th_s), 
        Paragraph("Lucro", th_s), Paragraph("Status", th_s)
    ]]

    for _, r in df_dados.iterrows():
        table_pdf_data.append([
            Paragraph(str(r['sku']), td_s), Paragraph(str(r['descricao']), td_s), 
            Paragraph(str(r['fornecedor']), td_s), Paragraph(f"R$ {float(r['custo']):.2f}", td_s), 
            Paragraph(f"R$ {float(r['preco_venda']):.2f}", td_s), Paragraph(f"R$ {float(r['preco_limplex']):.2f}", td_s), 
            Paragraph(f"R$ {float(r['lucro_reais']):.2f}", td_s), Paragraph(str(r['status']), td_s)
        ])

    t_pdf = Table(table_pdf_data, colWidths=[55, 140, 90, 50, 50, 55, 50, 45])
    t_pdf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f4c81")), 
        ('TEXTCOLOR', (0,0), (-1,0), colors.white), 
        ('PADDING', (0,0), (-1,-1), 4), 
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")), 
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story_pdf.append(t_pdf)
    story_pdf.append(Spacer(1, 15))
    story_pdf.append(Paragraph("Limplex Distribuidora — Gestão Interna", footer_s))
    
    doc.build(story_pdf)
    buffer_pdf.seek(0)
    return buffer_pdf.getvalue()

# --- 6.4 PDF RELATÓRIO INTERNO DE PRODUTOS ---
def gerar_pdf_produtos_interno(df_dados):
    buffer_pdf = io.BytesIO()
    doc = SimpleDocTemplate(buffer_pdf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story_pdf = []
    styles_pdf = getSampleStyleSheet()

    title_s = ParagraphStyle('TitleStyle', parent=styles_pdf['Heading1'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#0f4c81"))
    sub_s = ParagraphStyle('SubStyle', parent=styles_pdf['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor("#555555"), leading=11)
    th_s = ParagraphStyle('ThStyle', parent=styles_pdf['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)
    td_s = ParagraphStyle('TdStyle', parent=styles_pdf['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#333333"), leading=10)
    footer_s = ParagraphStyle('FooterStyle', parent=styles_pdf['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#666666"), alignment=1)

    story_pdf.append(Paragraph("<b>LIMPLEX DISTRIBUIDORA B2B</b>", title_s))
    story_pdf.append(Paragraph(f"Relatório Interno de Catálogo Selecionado | Emitido em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", sub_s))
    story_pdf.append(Spacer(1, 10))
    story_pdf.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f4c81"), spaceAfter=10))

    table_pdf_data = [[
        Paragraph("SKU", th_s), Paragraph("Descrição", th_s), Paragraph("Fornecedor", th_s), 
        Paragraph("Custo", th_s), Paragraph("Varejo", th_s), Paragraph("Limplex", th_s), 
        Paragraph("Lucro", th_s), Paragraph("Status", th_s)
    ]]

    for _, r in df_dados.iterrows():
        table_pdf_data.append([
            Paragraph(str(r['sku']), td_s), Paragraph(str(r['descricao']), td_s), 
            Paragraph(str(r['fornecedor']), td_s), Paragraph(f"R$ {float(r['custo']):.2f}", td_s), 
            Paragraph(f"R$ {float(r['preco_venda']):.2f}", td_s), Paragraph(f"R$ {float(r['preco_limplex']):.2f}", td_s), 
            Paragraph(f"R$ {float(r['lucro_reais']):.2f}", td_s), Paragraph(str(r['status']), td_s)
        ])

    t_pdf = Table(table_pdf_data, colWidths=[55, 140, 90, 50, 50, 55, 50, 45])
    t_pdf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f4c81")), 
        ('TEXTCOLOR', (0,0), (-1,0), colors.white), 
        ('PADDING', (0,0), (-1,-1), 4), 
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")), 
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story_pdf.append(t_pdf)
    story_pdf.append(Spacer(1, 15))
    story_pdf.append(Paragraph("Limplex Distribuidora — Gestão Interna", footer_s))
    
    doc.build(story_pdf)
    buffer_pdf.seek(0)
    return buffer_pdf.getvalue()


# --- 6.5 PDF CATÁLOGO DE PRODUTOS PARA CLIENTE (COM LOGO E NUMBERED CANVAS) ---
def gerar_pdf_catalogo_cliente(df_dados, empresa_info=None, usuario_emissao="Sistema"):
    from reportlab.pdfgen import canvas
    
    if empresa_info is None: empresa_info = {}
    
    razao_empresa = empresa_info.get('razao_social', 'DESC. E PAPELARIA LTDA')
    cnpj_empresa = empresa_info.get('cnpj', '26.644.910/0001-09')
    endereco_empresa = empresa_info.get('endereco', '')
    
    operador_atual = usuario_emissao
    data_hora_atual = datetime.now().strftime('%d/%m/%Y às %H:%M')

    buffer_pdf = io.BytesIO()
    doc = SimpleDocTemplate(buffer_pdf, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=40)
    story_pdf = []
    styles_pdf = getSampleStyleSheet()

    title_s = ParagraphStyle('TitleStyle', parent=styles_pdf['Heading1'], fontName='Helvetica-Bold', fontSize=15, textColor=colors.HexColor("#0f4c81"))
    subtitle_s = ParagraphStyle('SubTitleStyle', parent=styles_pdf['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor("#555555"))
    th_s = ParagraphStyle('ThStyle', parent=styles_pdf['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)
    td_s = ParagraphStyle('TdStyle', parent=styles_pdf['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#333333"), leading=12)
    td_price_s = ParagraphStyle('TdPriceStyle', parent=styles_pdf['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#0f4c81"), alignment=2, leading=12)

    # --- CABEÇALHO OFICIAL COM LOGÓTIPO ---
    texto_cabecalho = Paragraph(
        f"<b>LIMPLEX DISTRIBUIDORA</b><br/>"
        f"Soluções em Produtos de Limpeza e Higienização Profissional<br/>"
        f"{razao_empresa} | CNPJ: {cnpj_empresa}",
        subtitle_s
    )
    
    if os.path.exists("marca.PNG"):
        try:
            img = Image("marca.PNG", width=80, height=45)
            t_cab = Table([[img, texto_cabecalho]], colWidths=[90, 415])
            t_cab.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (0,0), 'LEFT'),
                ('ALIGN', (1,0), (1,0), 'LEFT'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            story_pdf.append(t_cab)
        except:
            story_pdf.append(Paragraph("<b>LIMPLEX DISTRIBUIDORA</b>", title_s))
            story_pdf.append(texto_cabecalho)
    else:
        story_pdf.append(Paragraph("<b>LIMPLEX DISTRIBUIDORA</b>", title_s))
        story_pdf.append(texto_cabecalho)

    story_pdf.append(Spacer(1, 8))
    story_pdf.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f4c81"), spaceAfter=10))

    # --- TÍTULO DO DOCUMENTO PADRONIZADO ---
    story_pdf.append(Paragraph("<b>TABELA DE PREÇOS / CATÁLOGO COMERCIAL</b>", ParagraphStyle('CatTitle', parent=title_s, fontSize=12, textColor=colors.HexColor("#0f4c81"))))
    story_pdf.append(Spacer(1, 8))

    # --- TABELA DE PRODUTOS COM COLUNA SEQUENCIAL À ESQUERDA ---
    table_pdf_data = [[
        Paragraph("Item", th_s), 
        Paragraph("Código (SKU)", th_s), 
        Paragraph("Descrição do Produto", th_s), 
        Paragraph("Preço Limplex (R$)", ParagraphStyle('ThPrice', parent=th_s, alignment=2))
    ]]

    for idx, r in enumerate(df_dados.iterrows(), start=1):
        row_data = r[1]
        table_pdf_data.append([
            Paragraph(str(idx), td_s), 
            Paragraph(str(row_data['sku']), td_s), 
            Paragraph(str(row_data['descricao']), td_s), 
            Paragraph(f"R$ {float(row_data['preco_limplex']):.2f}", td_price_s)
        ])

    t_pdf = Table(table_pdf_data, colWidths=[35, 100, 280, 90])
    t_pdf.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f4c81")), 
        ('TEXTCOLOR', (0,0), (-1,0), colors.white), 
        ('PADDING', (0,0), (-1,-1), 5), 
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")), 
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), 
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")])
    ]))
    story_pdf.append(t_pdf)
    
    # --- QUANTIDADE TOTAL DE PRODUTOS LISTADOS ---
    story_pdf.append(Spacer(1, 10))
    total_produtos = len(df_dados)
    story_pdf.append(Paragraph(f"<b>Total de Produtos Listados:</b> {total_produtos} item(ns)", ParagraphStyle('TotalStyle', parent=styles_pdf['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor("#0f4c81"))))

    # --- CANVAS PERSONALIZADO PARA RODAPÉ CORPORATIVO E NUMERAÇÃO X/Y ---
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super(NumberedCanvas, self).__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def draw_page_decorations(self, page_count):
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#555555"))
            
            # Linha divisória do rodapé
            self.setStrokeColor(colors.HexColor("#cccccc"))
            self.setLineWidth(0.5)
            self.line(30, 35, A4[0] - 30, 35)

            # Rodapé corporativo em 3 linhas
            self.drawString(30, 24, "LIMPLEX DISTRIBUIDORA B2B — Soluções em Produtos de Limpeza e Higienização Profissional")
            self.drawString(30, 14, f"Razão Social: {razao_empresa} | CNPJ: {cnpj_empresa} | Endereço: {endereco_empresa}")
            
            emitido_txt = f"Emitido por: {operador_atual.upper()} em {data_hora_atual} | Página {self._pageNumber}/{page_count}"
            self.drawString(30, 4, emitido_txt)
            self.restoreState()

    doc.build(story_pdf, canvasmaker=NumberedCanvas)
    buffer_pdf.seek(0)
    return buffer_pdf.getvalue() 