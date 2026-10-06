"""
Passo 1: procura lojas de Nova Serrana na Shopee e salva em lojas_encontradas.csv.

Como funciona: a Shopee só mostra o ESTADO da loja, não a cidade. Então o robô
pesquisa cada palavra de config.PALAVRAS_BUSCA (já filtrando Minas Gerais) e
classifica cada loja:
  - "confirmada": o nome da loja, a descrição ou o título de algum produto
    menciona Nova Serrana;
  - "provavel":   loja de Minas Gerais vendendo calçado, sem mencionar a cidade.

Uso:  python buscar_lojas.py [--perfil NOME]
"""
import random
import time
from urllib.parse import quote

import config
from comum import (CAMPOS_LOJA, SHOPEE, abrir_navegador, agora, anexar_csv,
                   eh_cidade_alvo, garantir_login, ler_csv, normalizar,
                   perfil_dos_args)
from playwright.sync_api import sync_playwright

CHAVES_LOCAL = ("shop_location", "location", "place", "city", "cidade", "address", "state")


def pausa(a=2.0, b=5.0):
    time.sleep(random.uniform(a, b))


def percorrer(obj):
    """Percorre um JSON inteiro devolvendo todos os dicionários."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from percorrer(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from percorrer(v)


def local_de(d: dict) -> str:
    return " ".join(str(d[k]) for k in CHAVES_LOCAL if isinstance(d.get(k), str))


def coletar_json(pagina, filtro_url: str, acao) -> list:
    """Executa `acao` e devolve os JSONs das respostas cuja URL contém filtro_url."""
    respostas = []

    def ao_responder(resp):
        if filtro_url in resp.url:
            try:
                respostas.append(resp.json())
            except Exception:
                pass

    pagina.on("response", ao_responder)
    try:
        acao()
        pagina.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    finally:
        pagina.remove_listener("response", ao_responder)
    return respostas


def produtos_da_busca(pagina, palavra: str, num_pagina: int) -> dict:
    """Devolve {shopid: {"local", "nome", "menciona"}} de uma página de resultados.

    "menciona" é True quando algum produto da loja cita a cidade no título.
    """
    url = f"{SHOPEE}/search?keyword={quote(palavra)}&page={num_pagina}"
    if config.FILTRO_ESTADO:
        url += f"&locations={quote(config.FILTRO_ESTADO)}"

    def abrir():
        pagina.goto(url, wait_until="domcontentloaded")
        for _ in range(6):  # rola a página para carregar todos os produtos
            pagina.mouse.wheel(0, 1500)
            pausa(0.8, 1.6)

    jsons = coletar_json(pagina, "/api/v4/search/", abrir)
    lojas = {}
    for j in jsons:
        for d in percorrer(j):
            shopid = d.get("shopid") or d.get("shop_id")
            if not shopid:
                continue
            info = lojas.setdefault(str(shopid), {"local": "", "nome": "", "menciona": False})
            info["local"] = info["local"] or local_de(d)
            info["nome"] = info["nome"] or d.get("shop_name") or ""
            if eh_cidade_alvo(d.get("name")) or eh_cidade_alvo(d.get("shop_name")):
                info["menciona"] = True
    return lojas


def detalhes_da_loja(pagina, shopid: str, info: dict) -> dict:
    """Abre a página da loja, pega nome/usuário e classifica a certeza."""
    jsons = coletar_json(
        pagina, "/api/v4/shop/",
        lambda: pagina.goto(f"{SHOPEE}/shop/{shopid}", wait_until="domcontentloaded"),
    )
    usuario = nome = local = ""
    menciona = info["menciona"]
    for j in jsons:
        for d in percorrer(j):
            local = local or local_de(d)
            if str(d.get("shopid")) == shopid:
                nome = nome or d.get("name") or ""
                conta = d.get("account") or {}
                usuario = usuario or conta.get("username") or ""
            # descrição da loja, títulos de produtos etc.
            if any(isinstance(v, str) and eh_cidade_alvo(v) for v in d.values()):
                menciona = True

    if not usuario:  # a URL da loja costuma virar shopee.com.br/<usuario>
        caminho = pagina.url.replace(SHOPEE, "").strip("/").split("?")[0]
        if caminho and not caminho.startswith("shop/"):
            usuario = caminho

    texto = ""
    try:
        texto = pagina.inner_text("body", timeout=5000)
    except Exception:
        pass

    local = local or info["local"]
    if any(eh_cidade_alvo(t) for t in (local, nome, texto)):
        menciona = True
    return {
        "usuario": usuario,
        "nome": nome or info["nome"] or usuario,
        "localizacao": local,
        "certeza": "confirmada" if menciona else "provavel",
        "url": f"{SHOPEE}/{usuario}" if usuario else f"{SHOPEE}/shop/{shopid}",
    }


def main():
    ja_salvas = {l["shopid"] for l in ler_csv(config.ARQUIVO_LOJAS)}
    ja_verificadas = set(ja_salvas)
    if config.ARQUIVO_VERIFICADAS.exists():  # lojas já conferidas em outras execuções
        ja_verificadas |= set(config.ARQUIVO_VERIFICADAS.read_text(encoding="utf-8").split())
    novas = 0

    with sync_playwright() as p:
        contexto = abrir_navegador(p, perfil_dos_args())
        pagina = garantir_login(contexto)

        for palavra in config.PALAVRAS_BUSCA:
            for n in range(config.PAGINAS_POR_BUSCA):
                print(f"\n🔎 Buscando '{palavra}' (página {n + 1})...")
                candidatas = produtos_da_busca(pagina, palavra, n)
                if not candidatas:  # às vezes a página carrega vazia; tenta de novo
                    pausa(5, 10)
                    candidatas = produtos_da_busca(pagina, palavra, n)
                print(f"   {len(candidatas)} lojas nos resultados")
                if not candidatas:
                    break

                for shopid, info in candidatas.items():
                    if shopid in ja_verificadas:
                        continue
                    ja_verificadas.add(shopid)
                    with config.ARQUIVO_VERIFICADAS.open("a", encoding="utf-8") as f:
                        f.write(shopid + "\n")
                    local = normalizar(info["local"])
                    # Fora de Minas Gerais e sem citar a cidade -> pula.
                    if local and "minas gerais" not in local and not eh_cidade_alvo(local) \
                            and not info["menciona"]:
                        print(f"   · {info['nome'] or shopid}: {info['local']}")
                        continue

                    pausa()
                    loja = detalhes_da_loja(pagina, shopid, info)
                    loja.update(shopid=shopid, palavra_busca=palavra, encontrada_em=agora())
                    anexar_csv(config.ARQUIVO_LOJAS, CAMPOS_LOJA, loja)
                    novas += 1
                    marca = "✅ confirmada" if loja["certeza"] == "confirmada" else "❔ provável "
                    print(f"   {marca} {loja['nome']} ({loja['url']})")
                pausa(3, 7)

        contexto.close()

    print(f"\nPronto! {novas} lojas novas salvas em {config.ARQUIVO_LOJAS.name}")


if __name__ == "__main__":
    main()
