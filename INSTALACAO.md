# 🤖 Bot Telegram — Analista Financeiro Pessoal
## Guia Completo de Instalação

---

## PASSO 1 — Criar o bot no Telegram (2 minutos)

1. Abra o Telegram e procure por **@BotFather**
2. Mande `/newbot`
3. Escolha um nome: ex. `Meu Analista Financeiro`
4. Escolha um username: ex. `meu_analista_fin_bot`
5. O BotFather vai te dar um **TOKEN** — guarde esse token!
6. Agora mande `/start` para o seu novo bot
7. Acesse: `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
8. Você vai ver seu **chat_id** — anote!

---

## PASSO 2 — Preparar suas planilhas

Coloque suas planilhas na pasta `data/`:

**data/carteira.xlsx** — sua carteira atual:
| ticker | quantidade | preco_medio | mercado | classe |
|--------|-----------|-------------|---------|--------|
| PETR4  | 100       | 32.50       | B3      | AÇÃO   |
| MXRF11 | 200       | 10.20       | B3      | FII    |
| AAPL   | 5         | 150.00      | USA     | STOCK  |

**data/radar.xlsx** — seus ativos monitorados:
| ticker | preco_teto | dy_minimo | pvp_maximo | setor      | notas         |
|--------|-----------|-----------|------------|------------|---------------|
| PETR4  | 36.00     | 8.0       |            | Energia    | Aguardar queda|
| MXRF11 | 11.00     | 9.0       | 1.05       | FII Papel  |               |

> ⚠️ Os nomes das colunas são flexíveis — o bot detecta automaticamente variações como
> "Preço Teto", "preco teto", "teto", "target", etc.

---

## PASSO 3 — Deploy no Render.com (gratuito)

### 3.1 — Subir o código no GitHub

1. Crie uma conta em [github.com](https://github.com) se não tiver
2. Crie um repositório novo (privado!)
3. Faça upload de todos os arquivos deste projeto
4. **IMPORTANTE**: coloque as planilhas na pasta `data/` do repositório

### 3.2 — Criar o serviço no Render

1. Acesse [render.com](https://render.com) e crie uma conta gratuita
2. Clique em **New → Web Service**
3. Conecte seu repositório do GitHub
4. Configure:
   - **Name**: `analista-financeiro-bot`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Plan**: `Free`

### 3.3 — Configurar variáveis de ambiente

No Render, vá em **Environment** e adicione:

| Variável | Valor |
|----------|-------|
| `TELEGRAM_TOKEN` | (token do BotFather) |
| `TELEGRAM_CHAT_ID` | (seu chat_id pessoal) |
| `CARTEIRA_PATH` | `data/carteira.xlsx` |
| `RADAR_PATH` | `data/radar.xlsx` |

5. Clique em **Deploy** — pronto! 🎉

---

## PASSO 4 — Testar o bot

No Telegram, mande para o seu bot:
- `/start` — deve responder com a lista de comandos
- `/status` — confirma que está rodando
- `/radar` — verifica oportunidades no radar
- `/carteira` — resumo da carteira

---

## Comandos disponíveis

| Comando | O que faz |
|---------|-----------|
| `/start` | Apresentação e lista de comandos |
| `/carteira` | Resumo completo da carteira agora |
| `/radar` | Todos os ativos do radar com status |
| `/alerta` | Só os ativos abaixo do preço teto |
| `/variacao` | Ativos com variação forte hoje |
| `/semanal` | Resumo semanal de oportunidades |
| `/status` | Confirma que o bot está rodando |

---

## Alertas automáticos

| Horário | Alerta |
|---------|--------|
| 17h30 (seg-sex) | Variações fortes do dia (>3%) |
| 18h00 (seg-sex) | Ativos abaixo do preço teto |
| 18h30 (seg-sex) | Resumo diário da carteira |
| 19h00 (sextas)  | Resumo semanal de oportunidades |

---

## Como atualizar suas planilhas

1. Edite seu Excel normalmente
2. Faça upload do arquivo atualizado no GitHub (substituindo o anterior)
3. O Render detecta a mudança e reinicia o bot automaticamente
4. Na próxima verificação, o bot já usa os dados novos

---

## Personalizar os alertas

Para mudar horários ou threshold de variação, edite `bot.py`:

```python
# Mudar horários dos agendamentos:
scheduler.add_job(job_variacao_forte,    "cron", hour=17, minute=30, ...)  # mude aqui
scheduler.add_job(job_alerta_preco_teto, "cron", hour=18, minute=0,  ...)  # mude aqui
scheduler.add_job(job_resumo_diario,     "cron", hour=18, minute=30, ...)  # mude aqui

# Mudar threshold de variação (padrão 3%):
msg = verificar_variacao_forte({...}, threshold=3.0)  # mude para 5.0 se quiser só alertas maiores
```

---

## Suporte

Em caso de problemas, verifique os logs no painel do Render em **Logs**.
Erros comuns:
- `TELEGRAM_TOKEN inválido` → verifique a variável de ambiente
- `Arquivo não encontrado` → verifique o caminho das planilhas
- `Ticker não encontrado` → verifique se o ticker está correto (ex: PETR4, não PETR4.SA)
