"""
GlowScalePro Store Bot
======================
Bot de vendas no Telegram para o Notion Elite Starter Kit 2026
Pagamento: USDT BEP-20 (BNB Smart Chain)
Autor: Gabriel Sapalo — GlowScalePro

CONFIGURAÇÃO NECESSÁRIA (linhas marcadas com CONFIG):
1. BOT_TOKEN        — token do @BotFather
2. ADMIN_CHAT_ID    — o teu Chat ID pessoal (para receber alertas)
3. WALLET_ADDRESS   — a tua carteira BEP-20
4. EMAIL_SENDER     — o teu email (Gmail)
5. EMAIL_PASSWORD   — App Password do Gmail (não a password normal)
6. PDF_PATH         — caminho para o ficheiro PDF do ebook
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────
# CONFIG — lido das variáveis de ambiente do Railway
# ─────────────────────────────────────────────

BOT_TOKEN       = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID   = int(os.environ.get("ADMIN_CHAT_ID", "8654527617"))
WALLET_ADDRESS  = os.environ.get("WALLET_ADDRESS", "0xed170267879a7ebb374134ea9b385bc7114856b6")
EMAIL_SENDER    = os.environ.get("EMAIL_SENDER", "glowscalepro@gmail.com")
EMAIL_PASSWORD  = os.environ.get("EMAIL_PASSWORD", "ggtvamuyatpmrasz")
PDF_PATH        = os.environ.get("PDF_PATH", "notion_elite_starter_kit_2026.pdf")

PRODUCT_NAME    = "Notion Elite Starter Kit 2026"
PRODUCT_PRICE   = 49  # USD
MOCKUP_PATH     = "notion_mockup.png"
NETWORK_NAME    = "BEP-20 (BNB Smart Chain)"
BSC_SCAN_URL    = "https://bscscan.com/address/" + WALLET_ADDRESS

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Textos das mensagens
# ─────────────────────────────────────────────

MSG_START = """👋 Bem-vindo à *GlowScalePro Store*!

Aqui podes adquirir os nossos produtos digitais com pagamento seguro em USDT.

Usa /comprar para ver os produtos disponíveis.
Usa /ajuda para saber como funciona o pagamento.
Usa /suporte para falar connosco."""

MSG_PRODUTOS = """🛒 *Produtos Disponíveis*

━━━━━━━━━━━━━━━━━━━━
📘 *Notion Elite Starter Kit 2026*
_O sistema definitivo de produtividade para estudantes_

✅ 9 capítulos + 2 bónus exclusivos
✅ 10 templates prontos para usar
✅ Método 24H para sair do caos
✅ 20 prompts de IA prontos
✅ Garantia de 7 dias

💰 *Preço: $49 USD*
━━━━━━━━━━━━━━━━━━━━

Clica no botão abaixo para comprar 👇"""

MSG_PAGAMENTO = f"""💳 *Instruções de Pagamento*

Produto: *{PRODUCT_NAME}*
Valor: *${PRODUCT_PRICE} USDT*
Rede: *{NETWORK_NAME}*

━━━━━━━━━━━━━━━━━━━━
📋 *Endereço da carteira:*
`{WALLET_ADDRESS}`
_(clica para copiar)_
━━━━━━━━━━━━━━━━━━━━

*Como pagar:*
1️⃣ Abre a tua carteira (Binance, Trust Wallet, MetaMask)
2️⃣ Selecciona USDT na rede *BSC / BEP-20*
3️⃣ Envia exactamente *${PRODUCT_PRICE} USDT* para o endereço acima
4️⃣ Após enviar, copia o *TX Hash* (ID da transacção)
5️⃣ Envia o TX Hash aqui neste chat

⏱ Prazo: 30 minutos após iniciar o processo

❓ Dúvidas? Usa /suporte"""

MSG_PEDE_EMAIL = """✅ *TX Hash recebido!*

Estamos a verificar o teu pagamento.

Enquanto isso, *envia o teu email* para recebermos o ebook:

_(ex: gabriel@gmail.com)_"""

MSG_CONFIRMACAO_ADMIN = """🔔 *NOVA VENDA — GlowScalePro Store*

📦 Produto: {product}
💰 Valor: ${price} USDT
👤 Cliente: @{username} (ID: {user_id})
📧 Email: {email}
🔗 TX Hash: `{tx_hash}`

Verifica em: https://bscscan.com/tx/{tx_hash}

Para confirmar e enviar o ebook, usa:
/confirmar_{user_id}"""

MSG_AGUARDA = """⏳ *Pagamento em verificação*

Recebemos o teu TX Hash e o teu email.

A nossa equipa vai verificar o pagamento e enviar o ebook para *{email}* em breve (normalmente menos de 15 minutos).

Obrigado pela confiança! 🙏"""

MSG_ENVIADO = """🎉 *Ebook enviado com sucesso!*

O *{product}* foi enviado para o email *{email}*.

Verifica também a pasta de spam caso não encontres na caixa principal.

Boas leituras! 📚
— Gabriel Sapalo · GlowScalePro"""

MSG_AJUDA = """❓ *Como funciona o pagamento?*

1. Escolhes o produto e clicas em Comprar
2. Enviamos o endereço da carteira USDT (rede BEP-20)
3. Fazes a transferência na tua carteira
4. Copias o TX Hash (ID da transacção) e envias aqui
5. Dás-nos o teu email
6. Verificamos e enviamos o ebook automaticamente

*O que é o TX Hash?*
É o comprovativo da transacção — um código longo que começa por 0x. Encontras-o no histórico da tua carteira após o envio.

*Quanto tempo demora?*
Normalmente menos de 15 minutos após confirmação.

*E se algo correr mal?*
Usa /suporte — respondemos rapidamente."""

MSG_SUPORTE = """🆘 *Suporte GlowScalePro*

Para qualquer problema ou dúvida, contacta-nos directamente:

📧 Email: sac@glowscalepro.com
🌐 Site: glowscalepro.com

Ou envia uma mensagem aqui e respondemos o mais rápido possível."""

# ─────────────────────────────────────────────
# Estado temporário dos utilizadores
# ─────────────────────────────────────────────
# Guarda o estado da conversa de cada utilizador
# { user_id: { "step": "aguarda_tx" | "aguarda_email", "tx_hash": "...", "email": "..." } }

user_states = {}

# ─────────────────────────────────────────────
# Handlers de comandos
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG_START, parse_mode="Markdown")


async def produtos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛒 Comprar — $49 USDT", callback_data="comprar_notion")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        with open(MOCKUP_PATH, "rb") as foto:
            await update.message.reply_photo(
                photo=foto,
                caption=MSG_PRODUTOS,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    except FileNotFoundError:
        await update.message.reply_text(MSG_PRODUTOS, parse_mode="Markdown", reply_markup=reply_markup)


async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG_AJUDA, parse_mode="Markdown")


async def suporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG_SUPORTE, parse_mode="Markdown")


# ─────────────────────────────────────────────
# Handler do botão inline "Comprar"
# ─────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "comprar_notion":
        user_id = query.from_user.id
        user_states[user_id] = {"step": "aguarda_tx", "tx_hash": None, "email": None}
        await query.message.reply_text(MSG_PAGAMENTO, parse_mode="Markdown")


# ─────────────────────────────────────────────
# Handler de mensagens de texto (TX hash + email)
# ─────────────────────────────────────────────

async def mensagem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    texto = update.message.text.strip()
    username = update.message.from_user.username or "sem_username"

    # Se o utilizador não tem estado activo, ignora
    if user_id not in user_states:
        await update.message.reply_text(
            "Usa /comprar para ver os produtos disponíveis.",
            parse_mode="Markdown"
        )
        return

    estado = user_states[user_id]

    # ── Passo 1: aguarda TX hash
    if estado["step"] == "aguarda_tx":
        # TX hash BEP-20 começa por 0x e tem 66 caracteres
        if texto.startswith("0x") and len(texto) == 66:
            user_states[user_id]["tx_hash"] = texto
            user_states[user_id]["step"] = "aguarda_email"
            await update.message.reply_text(MSG_PEDE_EMAIL, parse_mode="Markdown")
        else:
            await update.message.reply_text(
                "⚠️ TX Hash inválido.\n\nO TX Hash deve começar por `0x` e ter 66 caracteres.\nEncontra-o no histórico da tua carteira após o envio.",
                parse_mode="Markdown"
            )

    # ── Passo 2: aguarda email
    elif estado["step"] == "aguarda_email":
        if "@" in texto and "." in texto:
            email = texto.lower()
            tx_hash = user_states[user_id]["tx_hash"]

            user_states[user_id]["email"] = email
            user_states[user_id]["step"] = "aguarda_confirmacao"

            # Confirma ao cliente
            await update.message.reply_text(
                MSG_AGUARDA.format(email=email),
                parse_mode="Markdown"
            )

            # Alerta o admin
            msg_admin = MSG_CONFIRMACAO_ADMIN.format(
                product=PRODUCT_NAME,
                price=PRODUCT_PRICE,
                username=username,
                user_id=user_id,
                email=email,
                tx_hash=tx_hash,
            )
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=msg_admin,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "⚠️ Email inválido. Envia um endereço de email válido, por exemplo: gabriel@gmail.com"
            )


# ─────────────────────────────────────────────
# Comando admin: /confirmar_USERID
# Tu envias este comando após verificar o TX na BSCScan
# ─────────────────────────────────────────────

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Só o admin pode usar este comando
    if update.message.from_user.id != ADMIN_CHAT_ID:
        return

    # Extrai o user_id do comando (/confirmar_123456789)
    try:
        partes = update.message.text.split("_")
        target_user_id = int(partes[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Formato inválido. Usa: /confirmar_123456789")
        return

    if target_user_id not in user_states:
        await update.message.reply_text(f"Utilizador {target_user_id} não encontrado ou já processado.")
        return

    email = user_states[target_user_id].get("email")

    if not email:
        await update.message.reply_text("Email do cliente não encontrado.")
        return

    # Envia o PDF por email
    sucesso = enviar_pdf_email(email)

    if sucesso:
        # Notifica o cliente
        await context.bot.send_message(
            chat_id=target_user_id,
            text=MSG_ENVIADO.format(product=PRODUCT_NAME, email=email),
            parse_mode="Markdown"
        )
        # Confirma ao admin
        await update.message.reply_text(f"✅ PDF enviado com sucesso para {email}!")
        # Limpa o estado
        del user_states[target_user_id]
    else:
        await update.message.reply_text(
            f"❌ Erro ao enviar o email para {email}. Verifica as configurações do Gmail."
        )


# ─────────────────────────────────────────────
# Função de envio de email com PDF em anexo
# ─────────────────────────────────────────────

def enviar_pdf_email(destinatario: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = destinatario
        msg["Subject"] = f"O teu {PRODUCT_NAME} — GlowScalePro"

        corpo = f"""Olá!

Obrigado pela tua compra do {PRODUCT_NAME}.

Encontras o teu ebook em anexo neste email.

Qualquer dúvida, responde a este email ou contacta-nos em sac@glowscalepro.com

Boas leituras!
Gabriel Sapalo
GlowScalePro — glowscalepro.com
"""
        msg.attach(MIMEText(corpo, "plain"))

        # Anexar o PDF
        with open(PDF_PATH, "rb") as f:
            parte = MIMEBase("application", "octet-stream")
            parte.set_payload(f.read())
            encoders.encode_base64(parte)
            parte.add_header(
                "Content-Disposition",
                f"attachment; filename=Notion_Elite_Starter_Kit_2026.pdf"
            )
            msg.attach(parte)

        # Enviar via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(EMAIL_SENDER, EMAIL_PASSWORD)
            servidor.sendmail(EMAIL_SENDER, destinatario, msg.as_string())

        logger.info(f"PDF enviado com sucesso para {destinatario}")
        return True

    except Exception as e:
        logger.error(f"Erro ao enviar email para {destinatario}: {e}")
        return False


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    token_limpo = BOT_TOKEN.strip().replace("\n", "").replace("\r", "").replace(" ", "")
    logger.info(f"TOKEN DEBUG: {repr(token_limpo)}")
    app = Application.builder().token(token_limpo).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("comprar", produtos))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("suporte", suporte))

    # Comando admin (começa por /confirmar_)
    app.add_handler(MessageHandler(filters.Regex(r"^/confirmar_\d+$"), confirmar))

    # Botões inline
    app.add_handler(CallbackQueryHandler(button_handler))

    # Mensagens de texto (TX hash + email)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem_handler))

    logger.info("Bot GlowScalePro iniciado...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
