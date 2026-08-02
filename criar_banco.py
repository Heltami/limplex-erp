import sqlite3

def atualizar_estrutura_banco():
    conn = sqlite3.connect('limplex_erp.db')
    cursor = conn.cursor()

    # 1. FORNECEDORES
    cursor.execute('DROP TABLE IF EXISTS fornecedores')
    cursor.execute('''
    CREATE TABLE fornecedores (
        id_fornecedor INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_fantasia TEXT NOT NULL,
        razao_social TEXT,
        cnpj TEXT UNIQUE,
        contato TEXT,
        telefone TEXT,
        email TEXT,
        endereco TEXT,
        cidade TEXT,
        prazo_pagamento TEXT
    )
    ''')
    cursor.execute("INSERT INTO fornecedores (id_fornecedor, nome_fantasia, cidade) VALUES (1, 'Fornecedor Principal (Padrão)', 'Fortaleza')")

    # 2. PRODUTOS (Com a nova estrutura de precificação)
    cursor.execute('DROP TABLE IF EXISTS produtos')
    cursor.execute('''
    CREATE TABLE produtos (
        id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
        id_fornecedor INTEGER NOT NULL,
        sku TEXT NOT NULL,
        descricao TEXT NOT NULL,
        prc_varejo REAL,
        prc_distribuidora REAL,
        preco_venda REAL,
        imposto_reais REAL,
        frete_reais REAL,
        custo_total REAL,
        lucro_reais REAL,
        margem_lucro REAL,
        status TEXT,
        FOREIGN KEY (id_fornecedor) REFERENCES fornecedores (id_fornecedor),
        UNIQUE(sku, id_fornecedor)
    )
    ''')

    # 3. CLIENTES
    cursor.execute('DROP TABLE IF EXISTS clientes')
    cursor.execute('''
    CREATE TABLE clientes (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        razao_social TEXT NOT NULL,
        nome_fantasia TEXT,
        cnpj TEXT UNIQUE NOT NULL,
        inscricao_estadual TEXT,
        contato_principal TEXT,
        cargo TEXT,
        whatsapp_telefone TEXT,
        email TEXT,
        endereco_faturamento TEXT,
        endereco_entrega TEXT,
        bairro TEXT,
        cep TEXT,
        cidade TEXT,
        distancia_km REAL,
        condicao_pagamento TEXT,
        horario_entrega TEXT,
        observacoes TEXT
    )
    ''')

    # 4. CONFIGURAÇÕES (Foco na sua nova estratégia de Pricing)
    cursor.execute('DROP TABLE IF EXISTS configuracoes')
    cursor.execute('''
    CREATE TABLE configuracoes (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        razao_social TEXT,
        nome_fantasia TEXT,
        cnpj TEXT,
        telefone TEXT,
        email TEXT,
        endereco TEXT,
        perc_imposto REAL,
        perc_frete REAL,
        perc_desconto_padrao REAL
    )
    ''')
    # Valores padrão iniciais (ex: 4% imposto, 5% frete, 10% de desconto atrativo)
    cursor.execute('''
    INSERT INTO configuracoes (id, nome_fantasia, perc_imposto, perc_frete, perc_desconto_padrao) 
    VALUES (1, 'Limplex', 4.0, 5.0, 10.0)
    ''')

    # 5. PEDIDOS E ITENS
    cursor.execute('DROP TABLE IF EXISTS pedidos')
    cursor.execute('''
    CREATE TABLE pedidos (
        id_pedido INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente INTEGER,
        data_pedido TEXT,
        status TEXT,
        valor_total REAL,
        FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
    )
    ''')
    cursor.execute('DROP TABLE IF EXISTS itens_pedido')
    cursor.execute('''
    CREATE TABLE itens_pedido (
        id_item INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pedido INTEGER,
        id_produto INTEGER,
        quantidade INTEGER NOT NULL,
        preco_aplicado REAL NOT NULL,
        FOREIGN KEY (id_pedido) REFERENCES pedidos (id_pedido),
        FOREIGN KEY (id_produto) REFERENCES produtos (id_produto)
    )
    ''')

    conn.commit()
    conn.close()
    print("Banco de dados recriado com a nova Estrutura de Precificação Limplex!")

if __name__ == '__main__':
    atualizar_estrutura_banco()