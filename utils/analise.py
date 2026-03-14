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
    """
    Compara preços atuais com preços teto do radar.
    Se apenas_abaixo=True, retorna só os que estão abaixo do teto (oportunidades).
    Se False, retorna todos com status.
    """
    if not radar:
        return "⚠️ Radar vazio. Verifique a planilha."

    linhas_verde  = []
    linhas_amarelo = []
    linhas_vermelho = []

    for ativo in radar:
        ticker = ativo["ticker"]
        teto   = ativo["preco_teto"]
        if not teto or teto == 0:
            continue

        dados  = precos.get(ticker, {})
        preco  = dados.get("preco", 0)
        var    = dados.get("variacao", 0)
        dy     = dados.get("dy", 0)
        pvp    = dados.get("pvp", 0)

        if not preco:
            continue

        diff_pct = ((preco - teto) / teto) * 100  # negativo = abaixo do teto

        var_str = f"{var:+.1f}%" if var else "–"
        dy_str  = f"{dy:.1f}%" if dy else "–"
        pvp_str = f"{pvp:.2f}" if pvp else "–"

        linha = (
            f"*{ticker}*\n"
            f"  Preço: R$ {preco:.2f} | Teto: R$ {teto:.2f} | Diff: {diff_pct:+.1f}%\n"
            f"  Variação: {var_str} | DY: {dy_str} | P/VP: {pvp_str}"
        )

        if diff_pct <= 0:
            linhas_verde.append(f"🟢 {linha}")
        elif diff_pct <= 5:
            linhas_amarelo.append(f"🟡 {linha}")
        else:
            linhas_vermelho.append(f"🔴 {linha}")

    if apenas_abaixo:
        if not linhas_verde:
            return (
                f"📊 *ALERTA — PREÇO TETO* | {_agora()}\n\n"
                "Nenhum ativo do radar está abaixo do preço teto no momento."
            )
        msg = f"🚨 *ALERTA — OPORTUNIDADES NO RADAR* | {_agora()}\n\n"
        msg += "\n\n".join(linhas_verde)
        msg += f"\n\n_Total: {len(linhas_verde)} ativo(s) abaixo do teto_"
        return msg
    else:
        msg = f"📊 *RADAR COMPLETO* | {_agora()}\n\n"
        if linhas_verde:
            msg += "🟢 *ABAIXO DO TETO (oportunidade):*\n" + "\n\n".join(linhas_verde) + "\n\n"
        if linhas_amarelo:
            msg += "🟡 *PRÓXIMO DO TETO (monitorar):*\n" + "\n\n".join(linhas_amarelo) + "\n\n"
        if linhas_vermelho:
            msg += "🔴 *ACIMA DO TETO (aguardar):*\n" + "\n\n".join(linhas_vermelho)
        return msg.strip()


def verificar_variacao_forte(precos: dict, threshold: float = 3.0) -> str:
    """
    Alerta ativos com variação > threshold% ou < -threshold% no dia.
    """
    alertas_alta  = []
    alertas_baixa = []

    for ticker, dados in precos.items():
        var = dados.get("variacao", 0)
        preco = dados.get("preco", 0)
        if abs(var) >= threshold:
            linha = f"*{ticker}* — R$ {preco:.2f} ({var:+.1f}%)"
            if var > 0:
                alertas_alta.append(f"📈 {linha}")
            else:
                alertas_baixa.append(f"📉 {linha}")

    if not alertas_alta and not alertas_baixa:
        return (
            f"📊 *VARIAÇÃO DO DIA* | {_agora()}\n\n"
            f"Nenhum ativo da carteira com variação superior a {threshold}% hoje."
        )

    msg = f"⚡ *VARIAÇÕES FORTES DO DIA* | {_agora()}\n\n"
    if alertas_baixa:
        msg += "📉 *QUEDAS FORTES:*\n" + "\n".join(alertas_baixa) + "\n\n"
    if alertas_alta:
        msg += "📈 *ALTAS FORTES:*\n" + "\n".join(alertas_alta)

    return msg.strip()


def gerar_resumo_diario(
    carteira: list[dict],
    precos_br: dict,
    precos_usa: dict,
    dolar: float
) -> str:
    """
    Gera resumo completo da carteira após fechamento do mercado.
    """
    total_brl  = 0.0
    total_usa  = 0.0
    por_classe = {}
    linhas     = []

    for ativo in carteira:
        ticker = ativo["ticker"]
        qtd    = ativo["quantidade"]
        pm     = ativo["preco_medio"]
        mercado = ativo["mercado"]
        classe  = ativo["classe"]

        if mercado == "B3":
            dados = precos_br.get(ticker, {})
            preco = dados.get("preco", 0)
            var   = dados.get("variacao", 0)
            valor = preco * qtd
            total_brl += valor
            emoji_var = "📈" if var > 0 else "📉" if var < 0 else "➡️"
            rentab = ((preco - pm) / pm * 100) if pm else 0
            linha = (
                f"{emoji_var} *{ticker}* — R$ {preco:.2f} ({var:+.1f}%)\n"
                f"   Qtd: {qtd:.0f} | Valor: R$ {valor:,.2f} | Rentab: {rentab:+.1f}%"
            )
        else:  # USA
            dados = precos_usa.get(ticker, {})
            preco = dados.get("preco", 0)
            var   = dados.get("variacao", 0)
            valor_usd = preco * qtd
            valor_brl = valor_usd * dolar
            total_usa += valor_brl
            emoji_var = "📈" if var > 0 else "📉" if var < 0 else "➡️"
            rentab = ((preco - pm) / pm * 100) if pm else 0
            linha = (
                f"{emoji_var} *{ticker}* — US$ {preco:.2f} ({var:+.1f}%)\n"
                f"   Qtd: {qtd:.0f} | Valor: US$ {valor_usd:,.2f} ≈ R$ {valor_brl:,.2f} | Rentab: {rentab:+.1f}%"
            )

        linhas.append(linha)
        por_classe[classe] = por_classe.get(classe, 0) + (valor if mercado == "B3" else valor_usd * dolar)

    patrimonio_total = total_brl + total_usa

    msg = f"📊 *RESUMO DIÁRIO DA CARTEIRA* | {_agora()}\n"
    msg += f"💵 Dólar: R$ {dolar:.2f}\n\n"

    # Distribuição por classe
    msg += "*📂 Distribuição por classe:*\n"
    for classe, valor in sorted(por_classe.items(), key=lambda x: -x[1]):
        pct = (valor / patrimonio_total * 100) if patrimonio_total else 0
        msg += f"  • {classe}: R$ {valor:,.2f} ({pct:.1f}%)\n"

    msg += f"\n*💰 Patrimônio total: R$ {patrimonio_total:,.2f}*\n"
    msg += f"  🇧🇷 B3: R$ {total_brl:,.2f}\n"
    msg += f"  🇺🇸 USA: R$ {total_usa:,.2f}\n\n"

    msg += "*📋 Posições:*\n" + "\n\n".join(linhas)
    msg += "\n\n⚠️ _Valores estimados. Não constitui recomendação de investimento._"

    return msg


def gerar_alerta_matinal(
    carteira: list[dict],
    radar: list[dict],
    precos_br: dict,
    precos_usa: dict,
    dolar: float
) -> str:
    """
    Alerta matinal das 11h com 3 seções:
    1. Variações fortes do momento na carteira
    2. Oportunidades de swing trade no radar
    3. Posições da carteira em destaque (maiores altas/quedas)
    """
    agora = _agora()
    msg = f"☀️ *BOM DIA — ALERTA MATINAL* | {agora}\n"
    msg += f"💵 Dólar: R$ {dolar:.2f}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # ── SEÇÃO 1: Variações fortes do momento (carteira) ──────────────────────
    todos_precos = {**precos_br, **precos_usa}
    tickers_carteira = {a["ticker"] for a in carteira}

    altas   = []
    quedas  = []
    neutros = []

    for ativo in carteira:
        ticker = ativo["ticker"]
        dados  = todos_precos.get(ticker, {})
        preco  = dados.get("preco", 0)
        var    = dados.get("variacao", 0)
        mercado = ativo["mercado"]
        if not preco:
            continue
        moeda = "R$" if mercado == "B3" else "US$"
        linha = f"*{ticker}* {moeda} {preco:.2f} ({var:+.1f}%)"
        if var >= 2.0:
            altas.append(f"📈 {linha}")
        elif var <= -2.0:
            quedas.append(f"📉 {linha}")
        else:
            neutros.append(f"➡️ {linha}")

    msg += "⚡ *VARIAÇÕES DO MOMENTO (carteira):*\n"
    if not altas and not quedas:
        msg += "Mercado tranquilo, sem variações fortes acima de 2% ainda.\n"
    if quedas:
        msg += "\n".join(quedas) + "\n"
    if altas:
        msg += "\n".join(altas) + "\n"
    if neutros and not altas and not quedas:
        msg += "\n".join(neutros[:5]) + "\n"  # mostra até 5 neutros se não tiver fortes

    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # ── SEÇÃO 2: Oportunidades de swing trade no radar ────────────────────────
    swing_oport  = []
    swing_monit  = []

    for ativo in radar:
        ticker = ativo["ticker"]
        teto   = ativo["preco_teto"]
        if not teto:
            continue
        dados  = precos_br.get(ticker, {})
        preco  = dados.get("preco", 0)
        var    = dados.get("variacao", 0)
        dy     = dados.get("dy", 0)
        pvp    = dados.get("pvp", 0)
        if not preco:
            continue

        diff_pct = ((preco - teto) / teto) * 100
        var_str  = f"{var:+.1f}%" if var else "–"
        dy_str   = f"{dy:.1f}%" if dy else "–"

        linha = (
            f"*{ticker}* R$ {preco:.2f} | Teto: R$ {teto:.2f} | "
            f"Diff: {diff_pct:+.1f}% | Var: {var_str} | DY: {dy_str}"
        )

        if diff_pct <= 0:
            # Está abaixo do teto — oportunidade
            # Swing favorito: queda no dia + abaixo do teto = entrada técnica
            if var <= -1.5:
                swing_oport.insert(0, f"🔥 {linha} ← *queda + abaixo do teto!*")
            else:
                swing_oport.append(f"🟢 {linha}")
        elif diff_pct <= 5:
            swing_monit.append(f"🟡 {linha}")

    msg += "💡 *OPORTUNIDADES DE SWING TRADE (radar):*\n"
    if swing_oport:
        msg += "\n".join(swing_oport) + "\n"
    if swing_monit:
        msg += "\n🟡 *Próximos do teto (monitorar):*\n"
        msg += "\n".join(swing_monit) + "\n"
    if not swing_oport and not swing_monit:
        msg += "Nenhum ativo do radar abaixo ou próximo do preço teto no momento.\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # ── SEÇÃO 3: Destaques da carteira ────────────────────────────────────────
    posicoes = []
    for ativo in carteira:
        ticker = ativo["ticker"]
        qtd    = ativo["quantidade"]
        pm     = ativo["preco_medio"]
        mercado = ativo["mercado"]
        dados  = todos_precos.get(ticker, {})
        preco  = dados.get("preco", 0)
        var    = dados.get("variacao", 0)
        if not preco or not pm:
            continue
        rentab = ((preco - pm) / pm) * 100
        valor  = preco * qtd * (dolar if mercado == "USA" else 1)
        posicoes.append((ticker, preco, var, rentab, valor, mercado))

    # Ordena por variação do dia (maiores quedas e altas em destaque)
    posicoes.sort(key=lambda x: x[2])

    msg += "📊 *DESTAQUES DA CARTEIRA (maiores movimentos):*\n"
    destaques = posicoes[:3] + posicoes[-3:]  # 3 piores + 3 melhores
    destaques = list({d[0]: d for d in destaques}.values())  # remove duplicatas
    destaques.sort(key=lambda x: x[2])

    for ticker, preco, var, rentab, valor, mercado in destaques:
        moeda = "R$" if mercado == "B3" else "US$"
        emoji = "📈" if var > 0 else "📉" if var < 0 else "➡️"
        msg += (
            f"{emoji} *{ticker}* {moeda} {preco:.2f} | "
            f"Dia: {var:+.1f}% | Total: {rentab:+.1f}%\n"
        )

    msg += "\n⚠️ _Dados em tempo real. Não é recomendação de investimento._"
    return msg


def gerar_resumo_semanal(radar: list[dict], precos: dict) -> str:
    """
    Resumo semanal de oportunidades no radar (sextas-feiras).
    """
    oportunidades = []
    monitorar     = []
    caros         = []

    for ativo in radar:
        ticker = ativo["ticker"]
        teto   = ativo["preco_teto"]
        if not teto:
            continue

        dados = precos.get(ticker, {})
        preco = dados.get("preco", 0)
        dy    = dados.get("dy", 0)
        pvp   = dados.get("pvp", 0)
        if not preco:
            continue

        diff_pct = ((preco - teto) / teto) * 100
        dy_ok    = dy >= ativo.get("dy_minimo", 0) if ativo.get("dy_minimo") else True
        pvp_ok   = pvp <= ativo.get("pvp_maximo", 99) if ativo.get("pvp_maximo") else True

        status_dy  = "✅" if dy_ok else "⚠️"
        status_pvp = "✅" if pvp_ok else "⚠️"

        linha = (
            f"*{ticker}*: R$ {preco:.2f} | Teto: R$ {teto:.2f} | "
            f"Diff: {diff_pct:+.1f}% | DY: {dy:.1f}% {status_dy} | P/VP: {pvp:.2f} {status_pvp}"
        )

        if diff_pct <= 0:
            oportunidades.append(f"🟢 {linha}")
        elif diff_pct <= 5:
            monitorar.append(f"🟡 {linha}")
        else:
            caros.append(f"🔴 {linha}")

    data_hoje = datetime.now(BR_TZ).strftime("%d/%m/%Y")
    msg = f"📅 *RESUMO SEMANAL — {data_hoje}*\n\n"

    if oportunidades:
        msg += f"🟢 *OPORTUNIDADES ({len(oportunidades)} ativos abaixo do teto):*\n"
        msg += "\n".join(oportunidades) + "\n\n"

    if monitorar:
        msg += f"🟡 *MONITORAR ({len(monitorar)} ativos próximos do teto):*\n"
        msg += "\n".join(monitorar) + "\n\n"

    if caros:
        msg += f"🔴 *AGUARDAR ({len(caros)} ativos acima do teto):*\n"
        msg += "\n".join(caros) + "\n\n"

    if not oportunidades and not monitorar:
        msg += "Nenhuma oportunidade clara no radar esta semana. Paciência é parte da estratégia! 💪\n\n"

    msg += "⚠️ _Análise automatizada. Sempre valide antes de operar._"
    return msg
