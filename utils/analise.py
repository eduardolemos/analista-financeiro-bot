"""
utils/analise.py
Gera as mensagens de alerta e resumo enviadas pelo bot.
"""

from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)
BR_TZ = pytz.timezone("America/Sao_Paulo")


def _agora() -> str:
    return datetime.now(BR_TZ).strftime("%d/%m/%Y %H:%M")


def verificar_preco_teto(radar: list[dict], precos: dict, apenas_abaixo: bool = True) -> str:
    if not radar:
        return "⚠️ Radar vazio."

    linhas_verde, linhas_amarelo, linhas_vermelho = [], [], []

    for ativo in radar:
        ticker = ativo["ticker"]
        teto   = ativo.get("preco_teto", 0)
        if not teto:
            continue
        dados  = precos.get(ticker, {})
        preco  = dados.get("preco", 0)
        var    = dados.get("variacao", 0)
        if not preco:
            continue
        diff_pct = ((preco - teto) / teto) * 100
        linha = f"*{ticker}* R${preco:.2f} | Teto:R${teto:.2f} | {diff_pct:+.1f}%"
        if diff_pct <= 0:
            linhas_verde.append(f"🟢 {linha}")
        elif diff_pct <= 5:
            linhas_amarelo.append(f"🟡 {linha}")
        else:
            linhas_vermelho.append(f"🔴 {linha}")

    if apenas_abaixo:
        if not linhas_verde:
            return f"📊 *PREÇO TETO* | {_agora()}\nNenhum ativo abaixo do teto."
        msg = f"🚨 *OPORTUNIDADES* | {_agora()}\n\n"
        msg += "\n".join(linhas_verde[:20])
        return msg
    else:
        msg = f"📊 *RADAR* | {_agora()}\n\n"
        if linhas_verde:
            msg += "🟢 *Abaixo do teto:*\n" + "\n".join(linhas_verde[:15]) + "\n\n"
        if linhas_amarelo:
            msg += "🟡 *Próximo:*\n" + "\n".join(linhas_amarelo[:10]) + "\n\n"
        if linhas_vermelho:
            msg += "🔴 *Acima:*\n" + "\n".join(linhas_vermelho[:10])
        return msg.strip()


def verificar_variacao_forte(precos: dict, threshold: float = 3.0) -> str:
    altas, quedas = [], []
    for ticker, dados in precos.items():
        var   = dados.get("variacao", 0)
        preco = dados.get("preco", 0)
        if abs(var) >= threshold:
            linha = f"*{ticker}* R${preco:.2f} ({var:+.1f}%)"
            if var > 0:
                altas.append(f"📈 {linha}")
            else:
                quedas.append(f"📉 {linha}")

    if not altas and not quedas:
        return f"📊 *VARIAÇÃO* | {_agora()}\nNenhuma variação acima de {threshold}%."

    msg = f"⚡ *VARIAÇÕES FORTES* | {_agora()}\n\n"
    if quedas:
        msg += "📉 *Quedas:*\n" + "\n".join(quedas[:10]) + "\n\n"
    if altas:
        msg += "📈 *Altas:*\n" + "\n".join(altas[:10])
    return msg.strip()


def gerar_resumo_diario(carteira, precos_br, precos_usa, dolar) -> list[str]:
    total_brl, total_usa = 0.0, 0.0
    por_classe = {}
    altas, quedas = [], []

    for ativo in carteira:
        ticker  = ativo["ticker"]
        qtd     = float(ativo.get("quantidade", 0) or 0)
        mercado = ativo.get("mercado", "B3")
        classe  = ativo.get("classe", "OUTRO")
        if qtd <= 0:
            continue
        if mercado == "B3":
            dados = precos_br.get(ticker, {})
            preco = float(dados.get("preco", 0) or 0)
            var   = float(dados.get("variacao", 0) or 0)
            valor = preco * qtd
            total_brl += valor
        else:
            dados = precos_usa.get(ticker, {})
            preco = float(dados.get("preco", 0) or 0)
            var   = float(dados.get("variacao", 0) or 0)
            valor = preco * qtd * dolar
            total_usa += valor
        por_classe[classe] = por_classe.get(classe, 0) + valor
        if var >= 3.0:
            altas.append(f"📈 {ticker} {var:+.1f}%")
        elif var <= -3.0:
            quedas.append(f"📉 {ticker} {var:+.1f}%")

    patrimonio = total_brl + total_usa
    msg = f"📊 *CARTEIRA* | {_agora()}\n"
    msg += f"💵 Dólar: R$ {dolar:.2f}\n"
    msg += f"💰 *Total: R$ {patrimonio:,.0f}*\n"
    msg += f"🇧🇷 B3: R$ {total_brl:,.0f} | 🇺🇸 USA: R$ {total_usa:,.0f}\n\n"
    msg += "*Por classe:*\n"
    for classe, valor in sorted(por_classe.items(), key=lambda x: -x[1]):
        pct = (valor / patrimonio * 100) if patrimonio else 0
        msg += f"• {classe}: R$ {valor:,.0f} ({pct:.1f}%)\n"
    if altas or quedas:
        msg += "\n*Destaques (+/-3%):*\n"
        for x in (quedas + altas)[:8]:
            msg += x + "\n"
    msg += "\n⚠️ _Valores estimados._"
    return [msg]


def gerar_resumo_semanal(radar: list[dict], precos: dict) -> str:
    oportunidades, monitorar, caros = [], [], []
    for ativo in radar:
        ticker = ativo["ticker"]
        teto   = ativo.get("preco_teto", 0)
        if not teto:
            continue
        dados = precos.get(ticker, {})
        preco = dados.get("preco", 0)
        if not preco:
            continue
        diff_pct = ((preco - teto) / teto) * 100
        linha = f"*{ticker}* R${preco:.2f} | Teto:R${teto:.2f} | {diff_pct:+.1f}%"
        if diff_pct <= 0:
            oportunidades.append(f"🟢 {linha}")
        elif diff_pct <= 5:
            monitorar.append(f"🟡 {linha}")
        else:
            caros.append(f"🔴 {linha}")

    msg = f"📅 *RESUMO SEMANAL* | {_agora()}\n\n"
    if oportunidades:
        msg += f"🟢 *Oportunidades ({len(oportunidades)}):*\n" + "\n".join(oportunidades[:15]) + "\n\n"
    if monitorar:
        msg += f"🟡 *Monitorar ({len(monitorar)}):*\n" + "\n".join(monitorar[:10]) + "\n\n"
    if not oportunidades:
        msg += "Nenhuma oportunidade no radar esta semana.\n\n"
    msg += "⚠️ _Análise automatizada._"
    return msg


def gerar_alerta_matinal(carteira, radar, precos_br, precos_usa, dolar) -> str:
    msg = f"☀️ *BOM DIA* | {_agora()}\n"
    msg += f"💵 Dólar: R$ {dolar:.2f}\n"
    msg += "━━━━━━━━━━━━━━━\n\n"

    # Variações da carteira
    altas, quedas = [], []
    for ativo in carteira:
        ticker  = ativo["ticker"]
        mercado = ativo.get("mercado", "B3")
        dados   = precos_br.get(ticker, {}) if mercado == "B3" else precos_usa.get(ticker, {})
        var     = float(dados.get("variacao", 0) or 0)
        preco   = float(dados.get("preco", 0) or 0)
        if not preco:
            continue
        moeda = "R$" if mercado == "B3" else "US$"
        linha = f"*{ticker}* {moeda}{preco:.2f} ({var:+.1f}%)"
        if var >= 2.0:
            altas.append(f"📈 {linha}")
        elif var <= -2.0:
            quedas.append(f"📉 {linha}")

    msg += "⚡ *Variações da carteira:*\n"
    if not altas and not quedas:
        msg += "Mercado tranquilo.\n"
    for x in (quedas + altas)[:8]:
        msg += x + "\n"

    msg += "\n━━━━━━━━━━━━━━━\n\n"

    # Oportunidades no radar
    swing = []
    for ativo in radar:
        ticker = ativo["ticker"]
        teto   = ativo.get("preco_teto", 0)
        if not teto:
            continue
        dados  = precos_br.get(ticker, {})
        preco  = float(dados.get("preco", 0) or 0)
        var    = float(dados.get("variacao", 0) or 0)
        if not preco:
            continue
        diff_pct = ((preco - teto) / teto) * 100
        if diff_pct <= 0:
            emoji = "🔥" if var <= -1.5 else "🟢"
            swing.append(f"{emoji} *{ticker}* R${preco:.2f} | Teto:R${teto:.2f} | {diff_pct:+.1f}%")

    msg += "💡 *Oportunidades no radar:*\n"
    if swing:
        msg += "\n".join(swing[:10]) + "\n"
    else:
        msg += "Nenhum ativo abaixo do teto.\n"

    msg += "\n⚠️ _Não é recomendação de investimento._"
    return msg
