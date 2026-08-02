# seguranca.py
import re
import bcrypt

def gerar_hash_senha(senha_limpa: str) -> str:
    """Gera um hash seguro usando bcrypt a partir de uma palavra-passe em texto limpo."""
    # O gensalt adiciona uma camada extra de aleatoriedade (salt)
    salt = bcrypt.gensalt()
    hash_senha = bcrypt.hashpw(senha_limpa.encode('utf-8'), salt)
    return hash_senha.decode('utf-8')

def verificar_senha(senha_limpa: str, senha_hash: str) -> bool:
    """Verifica se a palavra-passe limpa corresponde ao hash guardado na base de dados."""
    try:
        return bcrypt.checkpw(senha_limpa.encode('utf-8'), senha_hash.encode('utf-8'))
    except ValueError:
        # Previne erros caso o hash na base de dados seja inválido ou antigo
        return False

def validar_complexidade_senha(senha):
    """
    Verifica se a palavra-passe cumpre os requisitos mínimos de segurança do ERP:
    - Pelo menos 12 caracteres
    - Pelo menos 1 letra maiúscula
    - Pelo menos 1 letra minúscula
    - Pelo menos 1 número
    - Pelo menos 1 caractere especial
    """
    if len(senha) < 12:
        return False, "A palavra-passe deve ter pelo menos 12 caracteres."
    
    if not re.search(r"[A-Z]", senha):
        return False, "A palavra-passe deve conter pelo menos uma letra maiúscula."
        
    if not re.search(r"[a-z]", senha):
        return False, "A palavra-passe deve conter pelo menos uma letra minúscula."
        
    if not re.search(r"\d", senha):
        return False, "A palavra-passe deve conter pelo menos um número."
        
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
        return False, "A palavra-passe deve conter pelo menos um caractere especial (Ex: !@#$)."
        
    return True, "Palavra-passe forte e válida."
    
# Pequeno script auxiliar (pode apagar depois) para gerar o seu primeiro hash de Admin:
if __name__ == "__main__":
    senha_admin = "Pass4Limplex2026!"
    print(f"O Hash seguro para '{senha_admin}' é:")
    print(gerar_hash_senha(senha_admin))