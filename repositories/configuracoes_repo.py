import pandas as pd
from core.database import conectar_bd

def garantir_tabela_configuracoes():
    """Garante a existência da tabela configuracoes e adiciona os campos de boleto/financeiro."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracoes (
                id SERIAL PRIMARY KEY,
                razao_social VARCHAR(255),
                cnpj VARCHAR(30),
                inscricao_estadual VARCHAR(50),
                endereco VARCHAR(255),
                telefone VARCHAR(50),
                email VARCHAR(100),
                multa_percentual NUMERIC(5,2) DEFAULT 2.00,
                juros_mensal_percentual NUMERIC(5,2) DEFAULT 1.00,
                dias_vencimento_padrao INTEGER DEFAULT 15
            )
        ''')
        
        # Garante a existência das novas colunas caso a tabela já existisse
        cursor.execute("ALTER TABLE configuracoes ADD COLUMN IF NOT EXISTS multa_percentual NUMERIC(5,2) DEFAULT 2.00")
        cursor.execute("ALTER TABLE configuracoes ADD COLUMN IF NOT EXISTS juros_mensal_percentual NUMERIC(5,2) DEFAULT 1.00")
        cursor.execute("ALTER TABLE configuracoes ADD COLUMN IF NOT EXISTS dias_vencimento_padrao INTEGER DEFAULT 15")
        
        # Garante que pelo menos 1 registo existe
        cursor.execute("SELECT COUNT(*) FROM configuracoes")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO configuracoes (razao_social, cnpj, multa_percentual, juros_mensal_percentual, dias_vencimento_padrao)
                VALUES ('LIMPLEX DISTRIBUIDORA LTDA', '00.000.000/0001-00', 2.00, 1.00, 15)
            ''')
            
        conn.commit()
    except Exception as e:
        print(f"Erro ao garantir tabela configuracoes: {e}")
    finally:
        cursor.close()
        conn.close()

def obter_configuracoes():
    """Retorna um dicionário com os dados das configurações globais."""
    garantir_tabela_configuracoes()
    conn = conectar_bd()
    try:
        df = pd.read_sql_query("SELECT * FROM configuracoes LIMIT 1", conn)
        return df.iloc[0].to_dict() if not df.empty else {}
    finally:
        conn.close()

def salvar_configuracoes(dados):
    """Atualiza as configurações da empresa e regras financeiras de boleto."""
    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE configuracoes SET
                razao_social = %s,
                cnpj = %s,
                inscricao_estadual = %s,
                endereco = %s,
                telefone = %s,
                email = %s,
                multa_percentual = %s,
                juros_mensal_percentual = %s,
                dias_vencimento_padrao = %s
            WHERE id = (SELECT id FROM configuracoes LIMIT 1)
        ''', (
            dados.get('razao_social', ''),
            dados.get('cnpj', ''),
            dados.get('inscricao_estadual', ''),
            dados.get('endereco', ''),
            dados.get('telefone', ''),
            dados.get('email', ''),
            float(dados.get('multa_percentual', 2.00)),
            float(dados.get('juros_mensal_percentual', 1.00)),
            int(dados.get('dias_vencimento_padrao', 15))
        ))
        conn.commit()
        return True, "Configurações salvas com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro ao salvar: {str(e)}"
    finally:
        cursor.close()
        conn.close()