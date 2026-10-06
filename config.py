"""
Configurações do robô. Edite este arquivo antes de rodar.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# TABELA DE PREÇOS
# ---------------------------------------------------------------------------
# Pasta no seu computador onde fica a tabela de preços dos saquinhos.
# O robô pega o arquivo MAIS RECENTE dessa pasta.
# Padrão: pasta "Tabela Saquinhos" dentro de Documentos.
# Para usar outra pasta: PASTA_TABELA = Path(r"C:\caminho\da\pasta")
PASTA_TABELA = Path.home() / "Documents" / "Tabela Saquinhos"

# O chat da Shopee só aceita IMAGEM (jpg/png). Se a sua tabela for PDF ou
# Excel, salve/exporte uma versão em imagem dentro da mesma pasta.
EXTENSOES_TABELA = [".jpg", ".jpeg", ".png", ".webp"]

# ---------------------------------------------------------------------------
# BUSCA DE LOJAS
# ---------------------------------------------------------------------------
# Cidade que a loja precisa ter na localização (sem acento já funciona).
CIDADE_ALVO = "Nova Serrana"

# Palavras pesquisadas na Shopee para achar lojas. Nova Serrana é polo
# calçadista, então começamos por calçados.
PALAVRAS_BUSCA = [
    "tenis nova serrana",
    "chinelo nova serrana",
    "sandalia nova serrana",
    "tenis masculino",
    "tenis feminino",
    "chinelo slide",
    "sapatenis",
    "bota feminina",
    "papete",
]

# Filtro de estado da própria Shopee (deixe "" para não filtrar).
FILTRO_ESTADO = "Minas Gerais"

# Quantas páginas de resultado ler por palavra.
PAGINAS_POR_BUSCA = 3

# ---------------------------------------------------------------------------
# ENVIO DE MENSAGENS
# ---------------------------------------------------------------------------
# {loja} é trocado pelo nome da loja.
MENSAGEM = (
    "Olá, {loja}! Tudo bem? 😊\n"
    "Somos representantes de saquinho preto para embalagem de e-commerce "
    "(envelope de segurança com lacre), ideal para envios da Shopee.\n"
    "Vi que vocês também são de Nova Serrana, assim como nós.\n"
    "Segue a nossa tabela de valores para vocês analisarem. "
    "Qualquer dúvida é só chamar aqui! 🙌"
)

# Mensagem para lojas "prováveis" (de MG, mas sem mencionar Nova Serrana).
MENSAGEM_PROVAVEL = (
    "Olá, {loja}! Tudo bem? 😊\n"
    "Somos representantes de saquinho preto para embalagem de e-commerce "
    "(envelope de segurança com lacre), ideal para envios da Shopee.\n"
    "Estamos aqui em Nova Serrana-MG.\n"
    "Segue a nossa tabela de valores para vocês analisarem. "
    "Qualquer dúvida é só chamar aqui! 🙌"
)

# True  = envia só para lojas que mencionam Nova Serrana (confirmadas).
# False = envia também para as prováveis (lojas de calçado de MG).
SOMENTE_CONFIRMADAS = False

# Limite de mensagens por dia (mantenha baixo para não ser bloqueado).
LIMITE_POR_DIA = 15

# Espera aleatória entre uma mensagem e outra (segundos).
ESPERA_MIN = 90
ESPERA_MAX = 240

# Se True, pergunta "Enviar? (s/n)" antes de cada loja.
CONFIRMAR_CADA_ENVIO = True

# ---------------------------------------------------------------------------
# NAVEGADOR
# ---------------------------------------------------------------------------
# False = usa o navegador baixado na instalação (mais confiável).
# True  = usa o Google Chrome instalado no computador.
USAR_CHROME_INSTALADO = False

# ---------------------------------------------------------------------------
# ARQUIVOS INTERNOS (normalmente não precisa mexer)
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
PERFIL_NAVEGADOR = BASE / "perfil_navegador"  # guarda o login da Shopee
ARQUIVO_LOJAS = BASE / "lojas_encontradas.csv"
ARQUIVO_ENVIADOS = BASE / "mensagens_enviadas.csv"
ARQUIVO_VERIFICADAS = BASE / "lojas_conferidas.txt"  # lojas já conferidas
ARQUIVO_BLOQUEADOS = BASE / "nao_contatar.txt"  # 1 shopid ou usuário por linha
