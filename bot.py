"""
Bot Telegram — Analista Financeiro Pessoal
Monitora carteira B3 + USA e envia alertas automáticos
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz

from utils.precos import buscar_precos_b3, buscar_precos_usa, buscar_dolar
from utils.planilha import carregar_carteira, carregar_radar, carregar_planilhas
from utils.analise import (
    verificar_preco_teto,
    verificar_variacao_forte,
    gerar_resumo_diario,
    gerar_resumo_semanal,
    gerar_alerta_matinal
)

# ─── Configurações ────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN        = os.environ["TELEGRAM_TOKEN"]       # Token do seu bot
CHAT_ID      = os.environ["TELEGRAM_CHAT_ID"]     # Seu chat ID pessoal
CARTEIRA_PATH = os.environ.get("CARTEIRA_PATH", "carteira.xls")
RADAR_PATH    = os.environ.get("RADAR_PATH",    "acoes_preco_teto.xlsx")

BR_TZ = pytz.timezone("America/Sao_Paulo")

# ─── Comandos manuais ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Sou seu Analista Financeiro pessoal.\n\n"
        "Comandos disponíveis:\n"
        "/carteira — Resumo da sua carteira agora\n"
        "/radar — Oportunidades no radar\n"
        "/alerta — Verificar preços teto agora\n"
        "/status — Status do bot\n"
        "/ajuda — Ver todos os comandos"
    )

async def cmd_ajuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Comandos disponíveis:*\n\n"
        "*/matinal* — Alerta matinal: variações + swing + carteira\n"
        "*/carteira* — Resumo completo da carteira\n"
        "*/radar* — Ativos do radar abaixo do preço teto\n"
        "*/alerta* — Verificação manual de alertas\n"
        "*/variacao* — Ativos com variação forte hoje\n"
        "*/semanal* — Resumo semanal de oportunidades\n"
        "*/status* — Confirmar que o bot está rodando\n"
        "*/ajuda* — Esta mensagem",
        parse_mode="Markdown"
    )

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    agora = datetime.now(BR_TZ).strftime("%d/%m/%Y %H:%M")
    await update.message.reply_text(
        f"✅ Bot rodando normalmente\n"
        f"🕐 Horário atual (BRT): {agora}\n\n"
        f"📅 Alertas agendados:\n"
        f"• ☀️ Alerta matinal (swing + carteira): diário às 11h\n"
        f"• ⚡ Variação forte: diário às 17h30\n"
        f"• 🎯 Preço teto: diário às 18h\n"
        f"• 📊 Resumo diário: diário às 18h30\n"
        f"• 📅 Resumo semanal: sextas às 19h"
    )

async def cmd_carteira(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Buscando dados da carteira...")
    try:
        carteira, _ = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        dolar       = buscar_dolar()
        tickers_br  = [a["ticker"] for a in carteira if a["mercado"] == "B3"]
        tickers_usa = [a["ticker"] for a in carteira if a["mercado"] == "USA"]
        precos_br   = buscar_precos_b3(tickers_br)   if tickers_br  else {}
        precos_usa  = buscar_precos_usa(tickers_usa) if tickers_usa else {}
        msg = gerar_resumo_diario(carteira, precos_br, precos_usa, dolar)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro cmd_carteira: {e}")
        await update.message.reply_text(f"❌ Erro ao buscar carteira: {e}")

async def cmd_radar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Verificando radar de oportunidades...")
    try:
        _, radar = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        tickers  = [a["ticker"] for a in radar]
        precos   = buscar_precos_b3(tickers)
        msg      = verificar_preco_teto(radar, precos, apenas_abaixo=False)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro cmd_radar: {e}")
        await update.message.reply_text(f"❌ Erro ao verificar radar: {e}")

async def cmd_alerta(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Verificando preços teto...")
    try:
        _, radar = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        tickers  = [a["ticker"] for a in radar]
        precos   = buscar_precos_b3(tickers)
        msg      = verificar_preco_teto(radar, precos, apenas_abaixo=True)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro cmd_alerta: {e}")
        await update.message.reply_text(f"❌ Erro: {e}")

async def cmd_variacao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Verificando variações do dia...")
    try:
        carteira, _ = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        tickers_br  = [a["ticker"] for a in carteira if a["mercado"] == "B3"]
        tickers_usa = [a["ticker"] for a in carteira if a["mercado"] == "USA"]
        precos_br   = buscar_precos_b3(tickers_br)   if tickers_br  else {}
        precos_usa  = buscar_precos_usa(tickers_usa) if tickers_usa else {}
        msg = verificar_variacao_forte({**precos_br, **precos_usa}, threshold=3.0)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro cmd_variacao: {e}")
        await update.message.reply_text(f"❌ Erro: {e}")

async def cmd_matinal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Gerando alerta matinal...")
    try:
        carteira, radar = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        dolar           = buscar_dolar()
        tickers_br      = [a["ticker"] for a in carteira if a["mercado"] == "B3"]
        tickers_usa     = [a["ticker"] for a in carteira if a["mercado"] == "USA"]
        tickers_radar   = [a["ticker"] for a in radar if a["ticker"] not in tickers_br]
        todos_br        = list(set(tickers_br + tickers_radar))
        precos_br       = buscar_precos_b3(todos_br)          if todos_br     else {}
        precos_usa      = buscar_precos_usa(tickers_usa)      if tickers_usa  else {}
        msg = gerar_alerta_matinal(carteira, radar, precos_br, precos_usa, dolar)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro cmd_matinal: {e}")
        await update.message.reply_text(f"❌ Erro: {e}")

async def cmd_semanal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Gerando resumo semanal...")
    try:
        _, radar = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        tickers  = [a["ticker"] for a in radar]
        precos   = buscar_precos_b3(tickers)
        msg      = gerar_resumo_semanal(radar, precos)
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro cmd_semanal: {e}")
        await update.message.reply_text(f"❌ Erro: {e}")

# ─── Agendamentos automáticos ─────────────────────────────────────────────────

async def job_alerta_preco_teto(app: Application):
    """Diário às 18h — verifica ativos abaixo do preço teto"""
    try:
        carteira, radar = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        # Verifica radar completo + ativos da carteira que têm preço teto
        tickers = list(set(
            [a["ticker"] for a in radar] +
            [a["ticker"] for a in carteira if a.get("tem_teto")]
        ))
        precos = buscar_precos_b3(tickers)
        msg    = verificar_preco_teto(radar, precos, apenas_abaixo=True)
        if msg:
            await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro job_alerta_preco_teto: {e}")

async def job_variacao_forte(app: Application):
    """Diário às 17h30 — verifica variações fortes (>3% ou <-3%)"""
    try:
        carteira, _  = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        tickers_br   = [a["ticker"] for a in carteira if a["mercado"] == "B3"]
        tickers_usa  = [a["ticker"] for a in carteira if a["mercado"] == "USA"]
        precos_br    = buscar_precos_b3(tickers_br)   if tickers_br  else {}
        precos_usa   = buscar_precos_usa(tickers_usa) if tickers_usa else {}
        msg = verificar_variacao_forte({**precos_br, **precos_usa}, threshold=3.0)
        if msg:
            await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro job_variacao_forte: {e}")

async def job_resumo_diario(app: Application):
    """Diário às 18h30 — resumo completo da carteira"""
    try:
        carteira, _  = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        dolar        = buscar_dolar()
        tickers_br   = [a["ticker"] for a in carteira if a["mercado"] == "B3"]
        tickers_usa  = [a["ticker"] for a in carteira if a["mercado"] == "USA"]
        precos_br    = buscar_precos_b3(tickers_br)   if tickers_br  else {}
        precos_usa   = buscar_precos_usa(tickers_usa) if tickers_usa else {}
        msg = gerar_resumo_diario(carteira, precos_br, precos_usa, dolar)
        await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro job_resumo_diario: {e}")

async def job_alerta_matinal(app: Application):
    """Diário às 11h — alerta matinal: variações do momento + oportunidades swing + carteira"""
    try:
        carteira, radar = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        dolar           = buscar_dolar()
        tickers_br      = [a["ticker"] for a in carteira if a["mercado"] == "B3"]
        tickers_usa     = [a["ticker"] for a in carteira if a["mercado"] == "USA"]
        tickers_radar   = [a["ticker"] for a in radar if a["ticker"] not in tickers_br]
        todos_br        = list(set(tickers_br + tickers_radar))
        precos_br       = buscar_precos_b3(todos_br)          if todos_br     else {}
        precos_usa      = buscar_precos_usa(tickers_usa)      if tickers_usa  else {}
        msg = gerar_alerta_matinal(carteira, radar, precos_br, precos_usa, dolar)
        await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro job_alerta_matinal: {e}")

async def job_resumo_semanal(app: Application):
    """Sextas às 19h — resumo semanal de oportunidades"""
    try:
        _, radar = carregar_planilhas([CARTEIRA_PATH, RADAR_PATH])
        tickers  = [a["ticker"] for a in radar]
        precos   = buscar_precos_b3(tickers)
        msg      = gerar_resumo_semanal(radar, precos)
        await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Erro job_resumo_semanal: {e}")

# ─── Main ─────────────────────────────────────────────────────────────────────

import asyncio

async def post_init(app: Application) -> None:
    """Inicia o scheduler após o event loop estar pronto"""
    scheduler = AsyncIOScheduler(timezone=BR_TZ)
    scheduler.add_job(job_alerta_matinal,    "cron", hour=11, minute=0,  args=[app])
    scheduler.add_job(job_variacao_forte,    "cron", hour=17, minute=30, args=[app])
    scheduler.add_job(job_alerta_preco_teto, "cron", hour=18, minute=0,  args=[app])
    scheduler.add_job(job_resumo_diario,     "cron", hour=18, minute=30, args=[app])
    scheduler.add_job(job_resumo_semanal,    "cron", day_of_week="fri", hour=19, args=[app])
    scheduler.start()
    logger.info("✅ Agendamentos ativos!")

async def main_async():
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("ajuda",    cmd_ajuda))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CommandHandler("carteira", cmd_carteira))
    app.add_handler(CommandHandler("radar",    cmd_radar))
    app.add_handler(CommandHandler("alerta",   cmd_alerta))
    app.add_handler(CommandHandler("variacao", cmd_variacao))
    app.add_handler(CommandHandler("semanal",  cmd_semanal))
    app.add_handler(CommandHandler("matinal",  cmd_matinal))

    logger.info("✅ Bot iniciado!")
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()  # Mantém rodando indefinidamente

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
