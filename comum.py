"""Funções compartilhadas: navegador, CSVs e texto."""
import csv
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright

import config

SHOPEE = "https://shopee.com.br"

CAMPOS_LOJA = ["shopid", "usuario", "nome", "localizacao", "certeza", "url", "palavra_busca", "encontrada_em"]
CAMPOS_ENVIO = ["shopid", "usuario", "nome", "perfil", "arquivo_tabela", "status", "enviado_em"]


def normalizar(texto) -> str:
    """Minúsculo e sem acento, para comparar 'Nova Serrana' com 'nova serrana'."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def eh_cidade_alvo(texto) -> bool:
    return normalizar(config.CIDADE_ALVO) in normalizar(texto)


def perfil_dos_args() -> str:
    """Lê `--perfil NOME` da linha de comando (padrão: "principal")."""
    if "--perfil" in sys.argv:
        i = sys.argv.index("--perfil")
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        sys.exit("Use: --perfil NOME")
    return "principal"


def abrir_navegador(p: Playwright, perfil: str = "principal") -> BrowserContext:
    """Abre o Chrome com um perfil próprio, que mantém o login da Shopee.

    Cada perfil tem a sua pasta (perfil_navegador/<perfil>) e o seu login.
    """
    opcoes = dict(
        user_data_dir=str(config.PERFIL_NAVEGADOR / perfil),
        headless=False,
        locale="pt-BR",
        viewport={"width": 1366, "height": 850},
        args=["--disable-blink-features=AutomationControlled"],
        timeout=60000,
    )
    print(f"🌐 Abrindo o navegador (perfil '{perfil}')...", flush=True)
    if config.USAR_CHROME_INSTALADO:
        try:
            return p.chromium.launch_persistent_context(channel="chrome", **opcoes)
        except Exception as e:
            print(f"   Não deu para abrir o Chrome instalado ({str(e)[:80]}). Usando o navegador do robô.")
    return p.chromium.launch_persistent_context(**opcoes)


def garantir_login(contexto: BrowserContext):
    pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
    print("🛒 Abrindo a Shopee...", flush=True)
    try:
        pagina.goto(SHOPEE, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        print("   A Shopee demorou para carregar; confira a janela do navegador.")
    if not any(c["name"] == "SPC_U" and c["value"] not in ("", "-") for c in contexto.cookies()):
        input(
            "\n>>> Faça login na Shopee na janela do navegador (só precisa na 1ª vez).\n"
            ">>> Depois de logado, volte aqui e aperte ENTER..."
        )
    return pagina


def ler_csv(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def anexar_csv(caminho: Path, campos: list[str], linha: dict):
    novo = not caminho.exists()
    with caminho.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        if novo:
            w.writeheader()
        w.writerow(linha)


def agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def lista_nao_contatar() -> set[str]:
    if not config.ARQUIVO_BLOQUEADOS.exists():
        return set()
    linhas = config.ARQUIVO_BLOQUEADOS.read_text(encoding="utf-8").splitlines()
    return {normalizar(l) for l in linhas if l.strip() and not l.startswith("#")}
