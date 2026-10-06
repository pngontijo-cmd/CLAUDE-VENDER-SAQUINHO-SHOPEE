"""
Passo 2: envia a mensagem + a tabela de preços para as lojas encontradas.

- Pega o arquivo mais recente de config.PASTA_TABELA.
- Nunca manda duas vezes para a mesma loja (registro em mensagens_enviadas.csv),
  nem a partir de perfis diferentes: o histórico é o mesmo para todos.
- Respeita o limite diário (contado separado para cada perfil) e espera um
  tempo aleatório entre envios.
- Lojas em nao_contatar.txt são ignoradas.

Uso:
    python enviar_mensagens.py            # pergunta antes de cada envio
    python enviar_mensagens.py --teste    # só mostra o que faria, não envia
    python enviar_mensagens.py --perfil loja2   # usa outro perfil/conta
"""
import random
import sys
import time
from datetime import date
from pathlib import Path

import config
from comum import (CAMPOS_ENVIO, abrir_navegador, agora, anexar_csv,
                   garantir_login, ler_csv, lista_nao_contatar, normalizar,
                   perfil_dos_args)
from playwright.sync_api import Page, sync_playwright

PASTA_ERROS = config.BASE / "erros"

BOTOES_CHAT = [
    "button:has-text('Conversar')",
    "button:has-text('Chat agora')",
    "button:has-text('Chat')",
    "text=Conversar agora",
]
CAIXA_TEXTO = ".shopee-chat-root textarea, textarea[placeholder*='mensagem' i]"
# Depois de anexar, a Shopee deixa a imagem selecionada esperando o envio.
BOTOES_CONFIRMAR_ANEXO = [
    ".shopee-chat-root button:has-text('Enviar')",
    ".shopee-chat-root [role=button]:has-text('Enviar')",
    ".shopee-chat-root button:has-text('Send')",
    ".shopee-chat-root [class*='send' i]",
]


def achar_tabela() -> Path:
    pasta = config.PASTA_TABELA
    if not pasta.is_dir():
        sys.exit(f"❌ Pasta da tabela não existe: {pasta}\n   Ajuste PASTA_TABELA no config.py")
    arquivos = [a for a in pasta.iterdir() if a.suffix.lower() in config.EXTENSOES_TABELA]
    if not arquivos:
        outros = ", ".join(a.name for a in pasta.iterdir() if a.is_file()) or "nenhum"
        sys.exit(
            f"❌ Nenhuma imagem ({', '.join(config.EXTENSOES_TABELA)}) em {pasta}\n"
            f"   Arquivos na pasta: {outros}\n"
            "   O chat da Shopee só aceita imagem: exporte a tabela como JPG/PNG."
        )
    return max(arquivos, key=lambda a: a.stat().st_mtime)


def clicar_primeiro(pagina: Page, seletores: list[str], timeout=4000) -> bool:
    for s in seletores:
        try:
            pagina.locator(s).first.click(timeout=timeout)
            return True
        except Exception:
            continue
    return False


def enviar_para_loja(pagina: Page, loja: dict, tabela: Path):
    pagina.goto(loja["url"], wait_until="domcontentloaded")
    time.sleep(random.uniform(3, 6))

    if not clicar_primeiro(pagina, BOTOES_CHAT):
        raise RuntimeError("botão de chat não encontrado")

    caixa = pagina.locator(CAIXA_TEXTO).first
    caixa.wait_for(state="visible", timeout=15000)
    time.sleep(random.uniform(1, 2))

    # 1) texto: digita linha a linha (Shift+Enter quebra linha sem enviar)
    confirmada = loja.get("certeza", "confirmada") == "confirmada"
    modelo = config.MENSAGEM if confirmada else config.MENSAGEM_PROVAVEL
    texto = modelo.format(loja=loja["nome"] or "tudo bem")
    caixa.click()
    for i, linha in enumerate(texto.split("\n")):
        if i:
            caixa.press("Shift+Enter")
        caixa.type(linha, delay=random.randint(25, 60))
    time.sleep(random.uniform(0.5, 1.5))
    caixa.press("Enter")
    time.sleep(random.uniform(2, 4))

    # 2) imagem da tabela
    entrada = pagina.locator(".shopee-chat-root input[type=file]").first
    if entrada.count() == 0:
        entrada = pagina.locator("input[type=file][accept*='image']").first
    entrada.set_input_files(str(tabela))
    time.sleep(random.uniform(3, 5))
    # Envia a imagem selecionada: clica no botão de enviar e, por garantia,
    # aperta Enter na caixa de texto (com a caixa vazia, o Enter não manda nada a mais).
    clicar_primeiro(pagina, BOTOES_CONFIRMAR_ANEXO, timeout=2500)
    time.sleep(random.uniform(1, 2))
    try:
        caixa.click(timeout=3000)
        caixa.press("Enter")
    except Exception:
        pass
    time.sleep(random.uniform(4, 6))


def main():
    teste = "--teste" in sys.argv
    perfil = perfil_dos_args()
    print(f"👤 Perfil: {perfil}")
    tabela = achar_tabela()
    print(f"📄 Tabela que será enviada: {tabela}")

    enviados = ler_csv(config.ARQUIVO_ENVIADOS)
    ja_enviadas = {e["shopid"] for e in enviados if e["status"] == "enviado"}
    hoje = date.today().isoformat()
    enviados_hoje = sum(
        1 for e in enviados
        if e["status"] == "enviado" and e["enviado_em"].startswith(hoje)
        and (e.get("perfil") or "principal") == perfil
    )
    bloqueadas = lista_nao_contatar()

    fila = [
        l for l in ler_csv(config.ARQUIVO_LOJAS)
        if l["shopid"] not in ja_enviadas
        and normalizar(l["shopid"]) not in bloqueadas
        and normalizar(l["usuario"]) not in bloqueadas
        and (not config.SOMENTE_CONFIRMADAS or l.get("certeza", "confirmada") == "confirmada")
    ]
    fila.sort(key=lambda l: l.get("certeza") == "provavel")  # confirmadas primeiro
    restante = config.LIMITE_POR_DIA - enviados_hoje
    print(f"🏪 {len(fila)} lojas ainda não contatadas | hoje já foram {enviados_hoje}, faltam {max(restante, 0)}")
    if not fila or restante <= 0:
        return
    fila = fila[:restante]

    if teste:
        for l in fila:
            print(f"  [TESTE] enviaria para {l['nome']} - {l['url']}")
        return

    PASTA_ERROS.mkdir(exist_ok=True)
    with sync_playwright() as p:
        contexto = abrir_navegador(p, perfil)
        pagina = garantir_login(contexto)

        for i, loja in enumerate(fila, 1):
            print(f"\n[{i}/{len(fila)}] {loja['nome']} ({loja.get('certeza') or 'confirmada'}) - {loja['url']}")
            if config.CONFIRMAR_CADA_ENVIO:
                r = input("   Enviar? (s = sim / n = pular / x = nunca contatar / q = sair): ").strip().lower()
                if r == "q":
                    break
                if r == "x":
                    with config.ARQUIVO_BLOQUEADOS.open("a", encoding="utf-8") as f:
                        f.write(loja["shopid"] + "\n")
                    continue
                if r != "s":
                    continue

            registro = {**loja, "perfil": perfil, "arquivo_tabela": tabela.name, "enviado_em": agora()}
            try:
                enviar_para_loja(pagina, loja, tabela)
                registro["status"] = "enviado"
                print("   ✅ enviado")
            except Exception as e:
                registro["status"] = f"falhou: {str(e)[:120]}"
                print(f"   ⚠️  {registro['status']}")
                try:
                    pagina.screenshot(path=str(PASTA_ERROS / f"{loja['shopid']}.png"))
                except Exception:
                    pass
            anexar_csv(config.ARQUIVO_ENVIADOS, CAMPOS_ENVIO, registro)

            if i < len(fila):
                espera = random.randint(config.ESPERA_MIN, config.ESPERA_MAX)
                print(f"   ⏳ aguardando {espera}s antes da próxima...")
                time.sleep(espera)

        contexto.close()


if __name__ == "__main__":
    main()
