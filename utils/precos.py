"""
utils/precos.py
Busca preços em tempo real — B3 via BRAPI, USA via yfinance
"""

import os
import requests
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN", "")
BRAPI_URL = "https://brapi.dev/api/quote/{tickers}?fundamental=true&token={token}"


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
        url = BRAPI_URL.format(tickers=",".join(batch), token=BRAPI_TOKEN)
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
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            preco_atual = float(info.last_price or 0)
            preco_ant   = float(info.previous_close or preco_atual)
            variacao    = ((preco_atual - preco_ant) / preco_ant * 100) if preco_ant else 0

            resultado[ticker] = {
                "preco":    preco_atual,
                "variacao": round(variacao, 2),
                "dy":       0,
                "pvp":      0,
                "pl":       0,
                "nome":     ticker,
                "mercado":  "USA",
            }
        except Exception as e:
            logger.warning(f"Erro ticker USA {ticker}: {e}")
            # Tenta fallback com history()
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="5d")
                if not hist.empty:
                    preco_atual = float(hist["Close"].iloc[-1])
                    preco_ant   = float(hist["Close"].iloc[-2]) if len(hist) > 1 else preco_atual
                    variacao    = ((preco_atual - preco_ant) / preco_ant * 100) if preco_ant else 0
                    resultado[ticker] = {
                        "preco":    preco_atual,
                        "variacao": round(variacao, 2),
                        "dy":       0,
                        "pvp":      0,
                        "pl":       0,
                        "nome":     ticker,
                        "mercado":  "USA",
                    }
                    logger.info(f"Ticker {ticker} recuperado via fallback history()")
                else:
                    logger.error(f"{ticker}: possibly delisted; No price data found")
            except Exception as e2:
                logger.error(f"{ticker}: fallback also failed: {e2}")

    return resultado


# Mapeamento de cripto ticker -> ticker yfinance
CRYPTO_YF_MAP = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "LINK": "LINK-USD",
    "ADA": "ADA-USD", "CHZ": "CHZ-USD", "SOL": "SOL-USD",
    "SOLV": "SOL-USD", "DOT": "DOT-USD", "AVAX": "AVAX-USD",
    "MATIC": "MATIC-USD", "XRP": "XRP-USD", "DOGE": "DOGE-USD",
    "SHIB": "SHIB-USD", "UNI": "UNI-USD", "AAVE": "AAVE-USD",
    "CRV": "CRV-USD", "NEAR": "NEAR-USD",
}


def buscar_precos_crypto(tickers: list[str]) -> dict:
    """Busca preço de criptomoedas via yfinance (ticker-USD)"""
    if not tickers:
        return {}

    resultado = {}
    for ticker in tickers:
        yf_ticker = CRYPTO_YF_MAP.get(ticker.upper(), f"{ticker.upper()}-USD")
        try:
            t = yf.Ticker(yf_ticker)
            info = t.fast_info
            preco_usd = float(info.last_price or 0)
            preco_ant = float(info.previous_close or preco_usd)
            variacao = ((preco_usd - preco_ant) / preco_ant * 100) if preco_ant else 0

            resultado[ticker] = {
                "preco":    preco_usd,
                "variacao": round(variacao, 2),
                "dy":       0,
                "pvp":      0,
                "pl":       0,
                "nome":     f"{ticker} (USD)",
                "mercado":  "CRYPTO",
            }
        except Exception as e:
            logger.warning(f"Erro crypto {ticker} ({yf_ticker}): {e}")

    return resultado() -> float:
    """Retorna cotação atual do dólar (USD/BRL)"""
    try:
        ticker = yf.Ticker("USDBRL=X")
        info   = ticker.fast_info
        return float(info.last_price or 5.0)
    except Exception as e:
        logger.warning(f"Erro ao buscar dólar: {e}")
        return 5.0  # fallback
-e 

def buscar_dolar() -> float:
    """Retorna cotação atual do dólar (USD/BRL)"""
    try:
        ticker = yf.Ticker("USDBRL=X")
        info   = ticker.fast_info
        return float(info.last_price or 5.0)
    except Exception as e:
        logger.warning(f"Erro ao buscar dólar: {e}")
        return 5.0  # fallback
