"""
Passo 1: procura lojas de Nova Serrana na Shopee e salva em lojas_encontradas.csv.

Como funciona: pesquisa cada palavra de config.PALAVRAS_BUSCA, lê os dados que
a própria página da Shopee carrega (localização da loja de cada produto) e,
quando a localização não é clara, abre a página da loja para confirmar.

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

CHAVES_LOCAL = ("shop_location", "location", "place", "city", "cidade", "address")
ESTADOS = {normalizar(e) for e in [
    "Acre", "Alagoas", "Amapa", "Amazonas", "Bahia", "Ceara", "Distrito Federal",
    "Espirito Santo", "Goias", "Maranhao", "Mato Grosso", "Mato Grosso do Sul",
    "Minas Gerais", "Para", "Paraiba", "Parana", "Pernambuco", "Piaui",
    "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul", "Rondonia",
    "Roraima", "Santa Catarina", "Sao Paulo", "Sergipe", "Tocantins", "",
]}


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
    """Devolve {shopid: {"local": ..., "nome": ...}} de uma página de resultados."""
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
            info = lojas.setdefault(str(shopid), {"local": "", "nome": ""})
            info["local"] = info["local"] or local_de(d)
            info["nome"] = info["nome"] or d.get("shop_name") or ""
    return lojas


def detalhes_da_loja(pagina, shopid: str) -> dict | None:
    """Abre a página da loja e confirma se ela é da cidade alvo."""
    jsons = coletar_json(
        pagina, "/api/v4/shop/",
        lambda: pagina.goto(f"{SHOPEE}/shop/{shopid}", wait_until="domcontentloaded"),
    )
    usuario = nome = local = ""
    for j in jsons:
        for d in percorrer(j):
            local = local or local_de(d)
            if str(d.get("shopid")) == shopid:
                nome = nome or d.get("name") or ""
                conta = d.get("account") or {}
                usuario = usuario or conta.get("username") or ""

    if not usuario:  # a URL da loja costuma virar shopee.com.br/<usuario>
        caminho = pagina.url.replace(SHOPEE, "").strip("/").split("?")[0]
        if caminho and not caminho.startswith("shop/"):
            usuario = caminho

    texto = ""
    try:
        texto = pagina.inner_text("body", timeout=5000)
    except Exception:
        pass

    if eh_cidade_alvo(local) or eh_cidade_alvo(nome) or eh_cidade_alvo(texto):
        return {
            "usuario": usuario,
            "nome": nome or usuario,
            "localizacao": local or config.CIDADE_ALVO,
            "url": f"{SHOPEE}/{usuario}" if usuario else f"{SHOPEE}/shop/{shopid}",
        }
    return None


def main():
    ja_salvas = {l["shopid"] for l in ler_csv(config.ARQUIVO_LOJAS)}
    ja_verificadas = set(ja_salvas)
    novas = 0

    with sync_playwright() as p:
        contexto = abrir_navegador(p, perfil_dos_args())
        pagina = garantir_login(contexto)

        for palavra in config.PALAVRAS_BUSCA:
            for n in range(config.PAGINAS_POR_BUSCA):
                print(f"\n🔎 Buscando '{palavra}' (página {n + 1})...")
                candidatas = produtos_da_busca(pagina, palavra, n)
                print(f"   {len(candidatas)} lojas nos resultados")
                if not candidatas:
                    break

                for shopid, info in candidatas.items():
                    if shopid in ja_verificadas:
                        continue
                    ja_verificadas.add(shopid)
                    local = normalizar(info["local"])
                    # Localização é de outra cidade (não é só o estado) -> pula.
                    if local and local not in ESTADOS and not eh_cidade_alvo(local):
                        continue

                    pausa()
                    loja = detalhes_da_loja(pagina, shopid)
                    if not loja:
                        continue
                    loja.update(shopid=shopid, palavra_busca=palavra, encontrada_em=agora())
                    anexar_csv(config.ARQUIVO_LOJAS, CAMPOS_LOJA, loja)
                    novas += 1
                    print(f"   ✅ {loja['nome']} ({loja['url']})")
                pausa(3, 7)

        contexto.close()

    print(f"\nPronto! {novas} lojas novas salvas em {config.ARQUIVO_LOJAS.name}")


if __name__ == "__main__":
    main()
