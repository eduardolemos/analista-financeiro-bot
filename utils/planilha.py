"""
utils/planilha.py
Lê as planilhas Excel do usuário de forma flexível,
adaptando-se aos nomes das colunas disponíveis.
"""

import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Mapeamento flexível de nomes de colunas aceitos
MAPA_CARTEIRA = {
    "ticker":    ["ticker", "ativo", "codigo", "código", "symbol", "papel"],
    "quantidade":["quantidade", "qtd", "qtde", "cotas", "shares", "qnt"],
    "preco_medio":["preco_medio", "preço_médio", "pm", "preco medio", "preço médio", "custo medio", "custo médio"],
    "mercado":   ["mercado", "bolsa", "market", "pais", "país"],
    "classe":    ["classe", "tipo", "type", "categoria", "class"],
}

MAPA_RADAR = {
    "ticker":     ["ticker", "ativo", "codigo", "código", "symbol", "papel"],
    "preco_teto": ["preco_teto", "preço_teto", "teto", "preco teto", "preço teto", "target"],
    "dy_minimo":  ["dy_minimo", "dy mínimo", "dy_min", "dy minimo", "dividend yield minimo", "dy%"],
    "pvp_maximo": ["pvp_maximo", "pvp máximo", "pvp_max", "p/vp", "pvp"],
    "setor":      ["setor", "sector", "segmento"],
    "notas":      ["notas", "observacoes", "observações", "obs", "notas/observações", "comentarios"],
}


def _encontrar_coluna(df: pd.DataFrame, alternativas: list[str]) -> str | None:
    """Retorna o nome da coluna no DataFrame que bate com alguma alternativa."""
    colunas_lower = {c.lower().strip(): c for c in df.columns}
    for alt in alternativas:
        if alt.lower() in colunas_lower:
            return colunas_lower[alt.lower()]
    return None


def _mapear_df(df: pd.DataFrame, mapa: dict) -> pd.DataFrame:
    """Renomeia colunas do DataFrame conforme o mapa de alternativas."""
    renomear = {}
    for campo, alternativas in mapa.items():
        col = _encontrar_coluna(df, alternativas)
        if col and col != campo:
            renomear[col] = campo
    return df.rename(columns=renomear)


def identificar_arquivo(path: str) -> str:
    """
    Identifica o tipo de planilha pelo nome do arquivo.
    Retorna 'carteira' ou 'radar'.
    """
    nome = os.path.basename(path).lower()
    if any(p in nome for p in ["carteira", "portfolio", "posicao", "posição"]):
        return "carteira"
    if any(p in nome for p in ["teto", "radar", "acoes", "ações", "monitoramento", "watchlist"]):
        return "radar"
    return "desconhecido"


def cruzar_carteira_com_teto(carteira: list[dict], radar: list[dict]) -> list[dict]:
    """
    Para cada ativo da carteira, busca o preço teto correspondente
    na planilha de radar/preço teto pelo ticker.
    Retorna a carteira enriquecida com preço teto quando disponível.
    """
    # Monta índice do radar por ticker para busca rápida
    indice_radar = {a["ticker"]: a for a in radar}

    for ativo in carteira:
        ticker = ativo["ticker"]
        dados_radar = indice_radar.get(ticker, {})
        # Enriquece com dados do radar se existir
        ativo["preco_teto"]  = dados_radar.get("preco_teto", 0)
        ativo["dy_minimo"]   = dados_radar.get("dy_minimo", 0)
        ativo["pvp_maximo"]  = dados_radar.get("pvp_maximo", 0)
        ativo["setor"]       = dados_radar.get("setor", "")
        ativo["notas"]       = dados_radar.get("notas", "")
        ativo["tem_teto"]    = ativo["preco_teto"] > 0

    return carteira


def carregar_planilhas(paths: list[str]) -> tuple[list[dict], list[dict]]:
    """
    Recebe uma lista de caminhos de arquivos (carteira + radar),
    identifica cada um pelo nome e retorna (carteira, radar) já cruzados.

    Aceita arquivos com nomes como:
    - 'carteira.xlsx', 'minha_carteira.xlsx'
    - 'acoes_preco_teto.xlsx', 'radar.xlsx', 'teto.xlsx'
    """
    import os
    carteira_path = None
    radar_path    = None

    for path in paths:
        tipo = identificar_arquivo(path)
        if tipo == "carteira":
            carteira_path = path
        elif tipo == "radar":
            radar_path = path
        else:
            # Tenta adivinhar pelo conteúdo se o nome não ajudou
            logger.warning(f"Arquivo não identificado pelo nome: {path} — tentando pelo conteúdo")
            try:
                df = pd.read_excel(path, nrows=2)
                colunas = [c.lower() for c in df.columns]
                if any(c in colunas for c in ["preco_teto", "teto", "preço_teto"]):
                    radar_path = path
                elif any(c in colunas for c in ["quantidade", "qtd", "preco_medio"]):
                    carteira_path = path
            except Exception:
                pass

    carteira = carregar_carteira(carteira_path) if carteira_path else []
    radar    = carregar_radar(radar_path)    if radar_path    else []

    # Cruza carteira com preços teto do radar
    if carteira and radar:
        carteira = cruzar_carteira_com_teto(carteira, radar)
    elif carteira and not radar:
        logger.warning("Planilha de preço teto não encontrada — análise sem preço teto")
        for ativo in carteira:
            ativo.update({"preco_teto": 0, "dy_minimo": 0, "pvp_maximo": 0,
                          "setor": "", "notas": "", "tem_teto": False})

    return carteira, radar


def carregar_carteira(path: str) -> list[dict]:
    """
    Lê a planilha de carteira e retorna lista de ativos.
    Detecta automaticamente a aba correta e as colunas.
    """
    try:
        xl = pd.ExcelFile(path)
        # Tenta encontrar aba com nome relevante
        aba = xl.sheet_names[0]
        for nome in xl.sheet_names:
            if any(p in nome.lower() for p in ["carteira", "portfolio", "posicao", "posição"]):
                aba = nome
                break

        df = pd.read_excel(path, sheet_name=aba)
        df = df.dropna(how="all")  # remove linhas totalmente vazias
        df = _mapear_df(df, MAPA_CARTEIRA)

        # Garante coluna mercado — detecta pelo ticker
        if "mercado" not in df.columns:
            df["mercado"] = df["ticker"].apply(_detectar_mercado)

        # Garante coluna classe
        if "classe" not in df.columns:
            df["classe"] = df["ticker"].apply(_detectar_classe)

        ativos = []
        for _, row in df.iterrows():
            ticker = str(row.get("ticker", "")).strip().upper()
            if not ticker or ticker == "NAN":
                continue
            ativos.append({
                "ticker":      ticker,
                "quantidade":  float(row.get("quantidade", 0) or 0),
                "preco_medio": float(row.get("preco_medio", 0) or 0),  # custo de compra, não preço atual
                "mercado":     str(row.get("mercado", "B3")).upper().strip(),
                "classe":      str(row.get("classe", "AÇÃO")).upper().strip(),
                # IMPORTANTE: preço atual NUNCA vem da planilha.
                # Sempre buscado em tempo real via buscar_precos_b3() ou buscar_precos_usa()
            })

        logger.info(f"Carteira carregada: {len(ativos)} ativos")
        return ativos

    except Exception as e:
        logger.error(f"Erro ao carregar carteira: {e}")
        return []


def carregar_radar(path: str) -> list[dict]:
    """
    Lê a planilha de radar/preço teto e retorna lista de ativos monitorados.
    """
    try:
        xl = pd.ExcelFile(path)
        aba = xl.sheet_names[0]
        for nome in xl.sheet_names:
            if any(p in nome.lower() for p in ["radar", "teto", "monitoramento", "watchlist"]):
                aba = nome
                break

        df = pd.read_excel(path, sheet_name=aba)
        df = df.dropna(how="all")
        df = _mapear_df(df, MAPA_RADAR)

        ativos = []
        for _, row in df.iterrows():
            ticker = str(row.get("ticker", "")).strip().upper()
            if not ticker or ticker == "NAN":
                continue
            ativos.append({
                "ticker":     ticker,
                "preco_teto": float(row.get("preco_teto", 0) or 0),   # seu alvo — estático, você define
                "dy_minimo":  float(row.get("dy_minimo", 0) or 0),    # seu critério mínimo — estático
                "pvp_maximo": float(row.get("pvp_maximo", 0) or 0),   # seu critério máximo — estático
                "setor":      str(row.get("setor", "")).strip(),
                "notas":      str(row.get("notas", "")).strip(),
                # IMPORTANTE: DY atual, P/VP atual e preço atual NUNCA vêm da planilha.
                # São sempre buscados em tempo real via buscar_precos_b3()
            })

        logger.info(f"Radar carregado: {len(ativos)} ativos")
        return ativos

    except Exception as e:
        logger.error(f"Erro ao carregar radar: {e}")
        return []


def _detectar_mercado(ticker: str) -> str:
    """Detecta se o ativo é B3 ou USA pelo formato do ticker."""
    ticker = str(ticker).strip().upper()
    # B3: geralmente 4 letras + 1-2 números (PETR4, MXRF11, BOVA11)
    import re
    if re.match(r"^[A-Z]{3,4}\d{1,2}$", ticker):
        return "B3"
    return "USA"


def _detectar_classe(ticker: str) -> str:
    """Detecta classe do ativo pelo ticker."""
    ticker = str(ticker).strip().upper()
    import re
    if re.match(r"^[A-Z]{4}11$", ticker):
        return "FII"
    if re.match(r"^[A-Z]{3,4}\d$", ticker):
        return "AÇÃO"
    return "STOCK/ETF"
