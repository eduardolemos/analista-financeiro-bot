"""
utils/precos.py
Busca preços em tempo real — B3 via BRAPI, USA via yfinance, Crypto via yfinance
Sempre retorna o último preço disponível, mesmo com mercado fechado.
"""

import os
import requests
import yfinance as yf
import logging

logger = logging.getLogger(__name__)

BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN", "")
BRAPI_URL = "https://brapi.dev/api/quote/{tickers}?fundamental=true&token={token}"


def _yf_preco_com_fallback(yf_ticker: str) -> tuple[float, float]:
    """
    Busca preço via yfinance com fallback pra history().
    Retorna (preco_atual, preco_anterior).
    Sempre tenta history() se fast_info retornar 0.
    """
    # Tentativa 1: fast_info (mais rápido)
    try:
        t = yf.Ticker(yf_ticker)
        info = t.fast_info
        preco = float(info.last_price or 0)
        prev = float(info.previous_close or 0)
        if preco > 0:
            return preco, prev if prev > 0 else preco
    except Exception as e:
        logger.debug(f"fast_info falhou para {yf_ticker}: {e}")

    # Tentativa 2: history (sempre retorna último fechamento)
    try:
        t = yf.Ticker(yf_ticker)
        hist = t.history(period="5d")
        if not hist.empty:
            preco = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else preco
            if preco > 0:
                logger.info(f"{yf_ticker}: usando último fechamento via history()")
                return preco, prev
    except Exception as e:
        logger.debug(f"history() falhou para {yf_ticker}: {e}")

    return 0.0, 0.0


def buscar_precos_b3(tickers: list[str]) -> dict:
    """
    Retorna dict com dados dos ativos B3 via BRAPI.
    BRAPI retorna regularMarketPrice mesmo fora do horário (último preço do dia).
    Se BRAPI falhar, faz fallback via yfinance ({ticker}.SA).
    """
    if not tickers:
        return {}

    resultado = {}

    # Tentativa via BRAPI (batches de 20)
    tickers_sem_preco = []
    for i in range(0, len(tickers), 20):
        batch = tickers[i:i+20]
        url = BRAPI_URL.format(tickers=",".join(batch), token=BRAPI_TOKEN)
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            encontrados = set()
            for item in data.get("results", []):
                ticker = item.get("symbol", "")
                preco = item.get("regularMarketPrice", 0)
                if preco and preco > 0:
                    resultado[ticker] = {
                        "preco":    preco,
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
                    encontrados.add(ticker)
            # Tickers que não vieram ou vieram com preço 0
            for t in batch:
                if t not in encontrados:
                    tickers_sem_preco.append(t)
        except Exception as e:
            logger.error(f"Erro BRAPI batch {batch}: {e}")
            tickers_sem_preco.extend(batch)

    # Fallback via yfinance para tickers que não vieram da BRAPI
    for ticker in tickers_sem_preco:
        yf_ticker = f"{ticker}.SA"
        preco, prev = _yf_preco_com_fallback(yf_ticker)
        if preco > 0:
            variacao = ((preco - prev) / prev * 100) if prev > 0 else 0
            resultado[ticker] = {
                "preco":    preco,
                "variacao": round(variacao, 2),
                "abertura": 0,
                "max_dia":  0,
                "min_dia":  0,
                "volume":   0,
                "dy":       0,
                "pvp":      0,
                "pl":       0,
                "nome":     ticker,
                "mercado":  "B3",
            }
            logger.info(f"{ticker}: recuperado via yfinance fallback ({yf_ticker})")
        else:
            logger.warning(f"{ticker}: sem preço disponível (BRAPI + yfinance falharam)")

    return resultado


def buscar_precos_usa(tickers: list[str]) -> dict:
    """
    Retorna dict com dados dos ativos americanos via yfinance.
    Sempre retorna último preço disponível, mesmo fora do horário.
    """
    if not tickers:
        return {}

    resultado = {}
    for ticker in tickers:
        preco, prev = _yf_preco_com_fallback(ticker)
        if preco > 0:
            variacao = ((preco - prev) / prev * 100) if prev > 0 else 0
            resultado[ticker] = {
                "preco":    preco,
                "variacao": round(variacao, 2),
                "dy":       0,
                "pvp":      0,
                "pl":       0,
                "nome":     ticker,
                "mercado":  "USA",
            }
        else:
            logger.warning(f"{ticker}: sem preço disponível")

    return resultado


# Mapeamento de cripto ticker -> ticker yfinance
CRYPTO_YF_MAP = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "LINK": "LINK-USD",
    "ADA": "ADA-USD", "CHZ": "CHZ-USD", "SOL": "SOL-USD",
    "SOLV": "SOL-USD", "DOT": "DOT-USD", "AVAX": "AVAX-USD",
    "MATIC": "MATIC-USD", "XRP": "XRP-USD", "DOGE": "DOGE-USD",
    "SHIB": "SHIB-USD", "UNI": "UNI-USD", "AAVE": "AAVE-USD",
    "CRV": "CRV-USD", "NEAR": "NEAR-USD", "LTC": "LTC-USD",
}


def buscar_precos_crypto(tickers: list[str]) -> dict:
    """
    Busca preço de criptomoedas via yfinance (ticker-USD).
    Crypto opera 24/7, então sempre tem preço disponível.
    """
    if not tickers:
        return {}

    resultado = {}
    for ticker in tickers:
        yf_ticker = CRYPTO_YF_MAP.get(ticker.upper(), f"{ticker.upper()}-USD")
        preco, prev = _yf_preco_com_fallback(yf_ticker)
        if preco > 0:
            variacao = ((preco - prev) / prev * 100) if prev > 0 else 0
            resultado[ticker] = {
                "preco":    preco,
                "variacao": round(variacao, 2),
                "dy":       0,
                "pvp":      0,
                "pl":       0,
                "nome":     f"{ticker} (USD)",
                "mercado":  "CRYPTO",
            }
        else:
            logger.warning(f"Crypto {ticker} ({yf_ticker}): sem preço disponível")

    return resultado


def buscar_dolar() -> float:
    """Retorna cotação atual do dólar (USD/BRL) com múltiplos fallbacks"""
    # Tentativa 1: yfinance (fast_info + history)
    preco, _ = _yf_preco_com_fallback("USDBRL=X")
    if preco > 0:
        return preco

    # Tentativa 2: API pública AwesomeAPI
    try:
        resp = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL", timeout=10)
        data = resp.json()
        preco = float(data["USDBRL"]["bid"])
        if preco > 0:
            logger.info("Dólar obtido via AwesomeAPI")
            return preco
    except Exception as e:
        logger.warning(f"Erro AwesomeAPI dólar: {e}")

    # Tentativa 3: BRAPI
    try:
        resp = requests.get(
            f"https://brapi.dev/api/v2/currency?currency=USD-BRL&token={BRAPI_TOKEN}",
            timeout=10
        )
        data = resp.json()
        preco = float(data["currency"][0]["bidPrice"])
        if preco > 0:
            logger.info("Dólar obtido via BRAPI")
            return preco
    except Exception as e:
        logger.warning(f"Erro BRAPI dólar: {e}")

    logger.error("Todas as fontes de dólar falharam, usando fallback 5.80")
    return 5.80
