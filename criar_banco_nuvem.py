from sqlalchemy import create_engine, text

# A sua Connection String do Supabase
URL_BANCO = "postgresql://postgres.xbcapilxzapzxripouna:Pass4Limplex2026!@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

def criar_tabelas_nuvem():
    print("A conectar à nuvem (Supabase)...")
    engine = create_engine(URL_BANCO)
    
    with engine.connect() as conn:
        print("A apagar tabelas antigas (se existirem)...")
        # Apagamos em ordem inversa para não dar erro de chave estrangeira
        conn.execute(text("DROP TABLE IF EXISTS itens_pedido CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS pedidos CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS configuracoes CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS clientes CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS produtos CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS fornecedores CASCADE;"))
        
        print("A criar tabela: Fornecedores...")
        conn.execute(text('''
            CREATE TABLE fornecedores (
                id_fornecedor SERIAL PRIMARY KEY,
                nome_fantasia VARCHAR NOT NULL,
                razao_social VARCHAR,
                cnpj VARCHAR UNIQUE,
                contato VARCHAR,
                telefone VARCHAR,
                email VARCHAR,
                endereco VARCHAR,
                cidade VARCHAR,
                prazo_pagamento VARCHAR
            )
        '''))
        conn.execute(text("INSERT INTO fornecedores (nome_fantasia, cidade) VALUES ('Fornecedor Principal', 'Fortaleza')"))

        print("A criar tabela: Produtos...")
        conn.execute(text('''
            CREATE TABLE produtos (
                id_produto SERIAL PRIMARY KEY,
                id_fornecedor INTEGER REFERENCES fornecedores(id_fornecedor),
                sku VARCHAR NOT NULL,
                descricao VARCHAR NOT NULL,
                prc_varejo NUMERIC,
                prc_distribuidora NUMERIC,
                preco_venda NUMERIC,
                imposto_reais NUMERIC,
                frete_reais NUMERIC,
                custo_total NUMERIC,
                lucro_reais NUMERIC,
                margem_lucro NUMERIC,
                status VARCHAR,
                UNIQUE(sku, id_fornecedor)
            )
        '''))

        print("A criar tabela: Clientes...")
        conn.execute(text('''
            CREATE TABLE clientes (
                id_cliente SERIAL PRIMARY KEY,
                razao_social VARCHAR NOT NULL,
                nome_fantasia VARCHAR,
                cnpj VARCHAR UNIQUE NOT NULL,
                inscricao_estadual VARCHAR,
                contato_principal VARCHAR,
                cargo VARCHAR,
                whatsapp_telefone VARCHAR,
                email VARCHAR,
                endereco_faturamento VARCHAR,
                endereco_entrega VARCHAR,
                bairro VARCHAR,
                cep VARCHAR,
                cidade VARCHAR,
                distancia_km NUMERIC,
                condicao_pagamento VARCHAR,
                horario_entrega VARCHAR,
                observacoes TEXT
            )
        '''))

        print("A criar tabela: Configurações...")
        conn.execute(text('''
            CREATE TABLE configuracoes (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                razao_social VARCHAR,
                nome_fantasia VARCHAR,
                cnpj VARCHAR,
                telefone VARCHAR,
                email VARCHAR,
                endereco VARCHAR,
                perc_imposto NUMERIC,
                perc_frete NUMERIC,
                perc_desconto_padrao NUMERIC
            )
        '''))
        conn.execute(text('''
            INSERT INTO configuracoes (id, nome_fantasia, perc_imposto, perc_frete, perc_desconto_padrao) 
            VALUES (1, 'Limplex', 4.0, 5.0, 10.0)
        '''))

        print("A criar tabela: Pedidos...")
        conn.execute(text('''
            CREATE TABLE pedidos (
                id_pedido SERIAL PRIMARY KEY,
                id_cliente INTEGER REFERENCES clientes(id_cliente),
                data_pedido VARCHAR,
                status VARCHAR,
                valor_total NUMERIC
            )
        '''))

        print("A criar tabela: Itens_Pedido...")
        conn.execute(text('''
            CREATE TABLE itens_pedido (
                id_item SERIAL PRIMARY KEY,
                id_pedido INTEGER REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
                id_produto INTEGER REFERENCES produtos(id_produto),
                quantidade INTEGER NOT NULL,
                preco_aplicado NUMERIC NOT NULL
            )
        '''))
        
        print("A criar tabela: Utilizadores...")
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS utilizadores (
                id_utilizador SERIAL PRIMARY KEY,
                usuario VARCHAR UNIQUE NOT NULL,
                senha VARCHAR NOT NULL,
                perfil VARCHAR NOT NULL
            )
        '''))
        # Insere um utilizador administrador padrão inicial
        conn.execute(text('''
            INSERT INTO utilizadores (usuario, senha, perfil) 
            VALUES ('admin', 'limplex2026', 'admin')
            ON CONFLICT (usuario) DO NOTHING;
        '''))

        conn.commit()
        print("✅ SUCESSO! Base de dados criada e estruturada no Supabase!")

if __name__ == '__main__':
    criar_tabelas_nuvem()