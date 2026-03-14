"""
utils/precos.py
Busca preços em tempo real — B3 via BRAPI, USA via yfinance
"""

import requests
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

BRAPI_URL = "https://brapi.dev/api/quote/{tickers}?fundamental=true"


def buscar_precos_b3(tickers: list[str]) -> dict:
    """
    Retorna dict com dados dos ativos B3:
    { "PETR4": { "preco": 34.5, "variacao": -1.2, "dy": 8.5, "pvp": 0.9 } }
    """
    if not tickers:
        return {}

    resultado = {}
    # BRAPI aceita até 50 tickers por vez
    for i in range(0, len(tickers), 50):
        batch = tickers[i:i+50]
        url   = BRAPI_URL.format(tickers=",".join(batch))
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("results", []):
                ticker = item.get("symbol", "")
                resultado[ticker] = {
                    "preco":    item.get("regularMarketPrice", 0),
                    "variacao": item.get("regularMarketChangePercent", 0),
                    "abertura": item.get("regularMarketOpen", 0),
                    "max_dia":  item.get("regularMarketDayHigh", 0),
                    "min_dia":  item.get("regularMarketDayLow", 0),
                    "volume":   item.get("regularMarketVolume", 0),
                    "dy":       item.get("dividendYield", 0),
                    "pvp":      item.get("priceToBook", 0),
                    "pl":       item.get("priceEarnings", 0),
                    "nome":     item.get("longName", ticker),
                    "mercado":  "B3",
                }
        except Exception as e:
            logger.error(f"Erro BRAPI batch {batch}: {e}")

    return resultado


def buscar_precos_usa(tickers: list[str]) -> dict:
    """
    Retorna dict com dados dos ativos americanos via yfinance:
    { "AAPL": { "preco": 195.0, "variacao": 1.5, ... } }
    """
    if not tickers:
        return {}

    resultado = {}
    try:
        dados = yf.download(
            tickers,
            period="2d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False
        )

        for ticker in tickers:
            try:
                info = yf.Ticker(ticker).fast_info
                preco_atual = float(info.last_price or 0)
                preco_ant   = float(info.previous_close or preco_atual)
                variacao    = ((preco_atual - preco_ant) / preco_ant * 100) if preco_ant else 0

                resultado[ticker] = {
                    "preco":    preco_atual,
                    "variacao": round(variacao, 2),
                    "dy":       0,   # buscar separadamente se necessário
                    "pvp":      0,
                    "pl":       0,
                    "nome":     ticker,
                    "mercado":  "USA",
                }
            except Exception as e:
                logger.warning(f"Erro ticker USA {ticker}: {e}")

    except Exception as e:
        logger.error(f"Erro yfinance geral: {e}")

    return resultado


def buscar_dolar() -> float:
    """Retorna cotação atual do dólar (USD/BRL)"""
    try:
        ticker = yf.Ticker("USDBRL=X")
        info   = ticker.fast_info
        return float(info.last_price or 5.0)
    except Exception as e:
        logger.warning(f"Erro ao buscar dólar: {e}")
        return 5.0  # fallback
