"""
utils/planilha.py
Lê as planilhas Excel usando openpyxl/xlrd diretamente (sem pandas)
"""

import os
import logging

logger = logging.getLogger(__name__)


def _ler_excel(path: str) -> list[dict]:
    """Lê arquivo Excel e retorna lista de dicts com as linhas"""
    if str(path).endswith(".xls"):
        import xlrd
        wb = xlrd.open_workbook(path)
        sheet = wb.sheet_by_index(0)
        for name in wb.sheet_names():
            if any(p in name.lower() for p in ["carteira", "portfolio", "teto", "radar", "acoes", "ações"]):
                sheet = wb.sheet_by_name(name)
                break
        headers = [str(sheet.cell_value(0, c)).strip().lower() for c in range(sheet.ncols)]
        rows = []
        for r in range(1, sheet.nrows):
            row = {headers[c]: sheet.cell_value(r, c) for c in range(sheet.ncols)}
            if any(v not in (None, "") for v in row.values()):
                rows.append(row)
        return rows
    else:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        sheet = wb.active
        for name in wb.sheetnames:
            if any(p in name.lower() for p in ["carteira", "portfolio", "teto", "radar", "acoes", "ações"]):
                sheet = wb[name]
                break
        rows_raw = list(sheet.iter_rows(values_only=True))
        if not rows_raw:
            return []
        headers = [str(h).strip().lower() if h else f"col{i}" for i, h in enumerate(rows_raw[0])]
        rows = []
        for row_raw in rows_raw[1:]:
            if all(v is None for v in row_raw):
                continue
            rows.append({headers[i]: row_raw[i] for i in range(len(headers))})
        return rows


def _get(row: dict, alternativas: list, default=None):
    for alt in alternativas:
        if alt.lower() in row and row[alt.lower()] not in (None, ""):
            return row[alt.lower()]
    return default


def _float(val, default=0.0) -> float:
    try:
        return float(val) if val not in (None, "") else default
    except (ValueError, TypeError):
        return default


def _str(val, default="") -> str:
    return str(val).strip() if val is not None else default


def identificar_arquivo(path: str) -> str:
    nome = os.path.basename(path).lower()
    if any(p in nome for p in ["carteira", "portfolio", "posicao"]):
        return "carteira"
    if any(p in nome for p in ["teto", "radar", "acoes", "ações", "monitoramento"]):
        return "radar"
    return "desconhecido"


def carregar_carteira(path: str) -> list[dict]:
    try:
        rows = _ler_excel(path)
        ativos = []
        for row in rows:
            ticker = _str(_get(row, ["ticker", "ativo", "codigo", "código", "papel"])).upper()
            if not ticker or ticker in ("NAN", "NONE", ""):
                continue
            mercado = _str(_get(row, ["mercado", "bolsa", "market"], "")).upper()
            if not mercado:
                mercado = _detectar_mercado(ticker)
            classe = _str(_get(row, ["classe", "tipo", "categoria"], "")).upper()
            if not classe:
                classe = _detectar_classe(ticker)
            ativos.append({
                "ticker":      ticker,
                "quantidade":  _float(_get(row, ["quantidade", "qtd", "qtde", "cotas"])),
                "preco_medio": _float(_get(row, ["preco_medio", "preço_médio", "pm", "preco medio", "custo medio"])),
                "mercado":     mercado,
                "classe":      classe,
            })
        logger.info(f"Carteira carregada: {len(ativos)} ativos")
        return ativos
    except Exception as e:
        logger.error(f"Erro ao carregar carteira: {e}")
        return []


def carregar_radar(path: str) -> list[dict]:
    try:
        rows = _ler_excel(path)
        ativos = []
        for row in rows:
            ticker = _str(_get(row, ["ticker", "ativo", "codigo", "código", "papel"])).upper()
            if not ticker or ticker in ("NAN", "NONE", ""):
                continue
            ativos.append({
                "ticker":     ticker,
                "preco_teto": _float(_get(row, ["preco_teto", "preço_teto", "teto", "preco teto", "target"])),
                "dy_minimo":  _float(_get(row, ["dy_minimo", "dy mínimo", "dy_min", "dy minimo", "dy%"])),
                "pvp_maximo": _float(_get(row, ["pvp_maximo", "pvp máximo", "pvp_max", "p/vp", "pvp"])),
                "setor":      _str(_get(row, ["setor", "sector", "segmento"])),
                "notas":      _str(_get(row, ["notas", "observacoes", "observações", "obs"])),
            })
        logger.info(f"Radar carregado: {len(ativos)} ativos")
        return ativos
    except Exception as e:
        logger.error(f"Erro ao carregar radar: {e}")
        return []


def cruzar_carteira_com_teto(carteira: list[dict], radar: list[dict]) -> list[dict]:
    indice_radar = {a["ticker"]: a for a in radar}
    for ativo in carteira:
        dados = indice_radar.get(ativo["ticker"], {})
        ativo.update({
            "preco_teto": dados.get("preco_teto", 0),
            "dy_minimo":  dados.get("dy_minimo", 0),
            "pvp_maximo": dados.get("pvp_maximo", 0),
            "setor":      dados.get("setor", ""),
            "notas":      dados.get("notas", ""),
            "tem_teto":   dados.get("preco_teto", 0) > 0,
        })
    return carteira


def carregar_planilhas(paths: list[str]) -> tuple[list[dict], list[dict]]:
    carteira_path = None
    radar_path    = None
    for path in paths:
        tipo = identificar_arquivo(path)
        if tipo == "carteira":
            carteira_path = path
        elif tipo == "radar":
            radar_path = path

    carteira = carregar_carteira(carteira_path) if carteira_path else []
    radar    = carregar_radar(radar_path)       if radar_path    else []

    if carteira and radar:
        carteira = cruzar_carteira_com_teto(carteira, radar)
    elif carteira:
        for ativo in carteira:
            ativo.update({"preco_teto": 0, "dy_minimo": 0, "pvp_maximo": 0,
                          "setor": "", "notas": "", "tem_teto": False})
    return carteira, radar


def _detectar_mercado(ticker: str) -> str:
    import re
    return "B3" if re.match(r"^[A-Z]{3,4}\d{1,2}$", ticker) else "USA"


def _detectar_classe(ticker: str) -> str:
    import re
    if re.match(r"^[A-Z]{4}11$", ticker):
        return "FII"
    if re.match(r"^[A-Z]{3,4}\d$", ticker):
        return "AÇÃO"
    return "STOCK/ETF"
