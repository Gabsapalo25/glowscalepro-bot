"""
GlowScalePro Store Bot
======================
Bot de vendas no Telegram — GlowScalePro
Pagamento: USDT BEP-20 (BNB Smart Chain)
Autor: Gabriel Sapalo — GlowScalePro

VARIÁVEIS DE AMBIENTE (configurar no Railway):
- BOT_TOKEN
- ADMIN_CHAT_ID
- WALLET_ADDRESS
- EMAIL_SENDER
- EMAIL_PASSWORD
- BSCSCAN_API_KEY  (NOVA: para validação automática)
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

# NOVA dependência para chamadas API
import aiohttp

# ─────────────────────────────────────────────
# VARIÁVEIS DE AMBIENTE
# ─────────────────────────────────────────────

BOT_TOKEN      = os.environ.get("BOT_TOKEN", "").strip().replace("\n","").replace("\r","").replace(" ","")
ADMIN_CHAT_ID  = int(os.environ.get("ADMIN_CHAT_ID", "8654527617"))
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS", "0xed170267879a7ebb374134ea9b385bc7114856b6").strip()
EMAIL_SENDER   = os.environ.get("EMAIL_SENDER", "glowscalepro@gmail.com").strip()
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "ggtvamuyatpmrasz").strip()
BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY", "").strip()  # NOVA: API Key da BSCScan
NETWORK_NAME   = "BEP-20 (BNB Smart Chain)"

# ─────────────────────────────────────────────
# CATÁLOGO DE PRODUTOS
# Para adicionar novo produto: copia o bloco abaixo e preenche
# ─────────────────────────────────────────────

PRODUTOS = {
    "notion_2026": {
        "id":        "notion_2026",
        "nome":      "Notion Elite Starter Kit 2026",
        "descricao": "O sistema definitivo de produtividade para estudantes",
        "preco":     49,
        "pdf":       "notion_elite_starter_kit_2026.pdf",
        "mockup":    "notion_mockup.png",
        "destaques": [
            "9 capítulos + 2 bónus exclusivos",
            "10 templates prontos para usar",
            "Método 24H para sair do caos",
            "20 prompts de IA prontos",
            "Garantia de 7 dias",
        ],
    },
    # ── NOVO PRODUTO (descomenta e preenche) ────────────────────────
    # "chave_produto": {
    #     "id":        "chave_produto",
    #     "nome":      "Nome do Produto",
    #     "descricao": "Descrição curta do produto",
    #     "preco":     27,
    #     "pdf":       "ficheiro_produto.pdf",
    #     "mockup":    "imagem_produto.png",
    #     "destaques": [
    #         "Benefício 1",
    #         "Benefício 2",
    #         "Benefício 3",
    #     ],
    # },
    # ────────────────────────────────────────────────────────────────
}

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# ESTADO DOS UTILIZADORES
# ─────────────────────────────────────────────

user_states = {}

# ─────────────────────────────────────────────
# MENSAGENS ESTÁTICAS
# ─────────────────────────────────────────────

MSG_AJUDA = (
    "❓ *Como funciona o pagamento?*\n\n"
    "1. Escolhes o produto e clicas em Comprar\n"
    "2. Enviamos o endereço da carteira USDT (rede BEP-20)\n"
    "3. Fazes a transferência na tua carteira\n"
    "4. Copias o TX Hash e envias aqui\n"
    "5. Dás-nos o teu email\n"
    "6. Verificamos e enviamos o produto em menos de 15 minutos\n\n"
    "*O que é o TX Hash?*\n"
    "É o comprovativo da transacção — começa por `0x`.\n"
    "Encontras-o no histórico da tua carteira após o envio.\n\n"
    "*E se algo correr mal?*\n"
    "Usa /suporte — respondemos rapidamente."
)

MSG_SUPORTE = (
    "🆘 *Suporte GlowScalePro*\n\n"
    "Para qualquer problema ou dúvida:\n\n"
    "📧 Email: sac@glowscalepro.com\n"
    "🌐 Site: glowscalepro.com\n\n"
    "Ou envia uma mensagem aqui e respondemos rapidamente."
)

# ─────────────────────────────────────────────
# HELPERS — construtores de mensagens
# ─────────────────────────────────────────────

def construir_menu_produtos():
    linhas = ["🛍 *Loja GlowScalePro*\n\nEscolhe o produto que queres adquirir:\n━━━━━━━━━━━━━━━━━━━━"]
    keyboard = []
    for pid, p in PRODUTOS.items():
        linhas.append(f"\n📦 *{p['nome']}*\n_{p['descricao']}_\n💰 *${p['preco']} USDT*")
        keyboard.append([InlineKeyboardButton(
            f"🛒 {p['nome']} — ${p['preco']} USDT",
            callback_data=f"produto_{pid}"
        )])
    linhas.append("\n━━━━━━━━━━━━━━━━━━━━")
    keyboard.append([InlineKeyboardButton("❓ Como funciona?", callback_data="ajuda_inline")])
    return "\n".join(linhas), InlineKeyboardMarkup(keyboard)


def construir_detalhe_produto(pid):
    p = PRODUTOS[pid]
    destaques = "\n".join([f"✅ {d}" for d in p["destaques"]])
    texto = (
        f"📦 *{p['nome']}*\n"
        f"_{p['descricao']}_\n\n"
        f"{destaques}\n\n"
        f"💰 *Preço: ${p['preco']} USDT*\n\n"
        f"Clica no botão abaixo para comprar 👇"
    )
    keyboard = [
        [InlineKeyboardButton(f"💳 Comprar — ${p['preco']} USDT", callback_data=f"comprar_{pid}")],
        [InlineKeyboardButton("⬅️ Ver todos os produtos", callback_data="ver_produtos")],
    ]
    return texto, InlineKeyboardMarkup(keyboard)


def construir_instrucoes_pagamento(pid):
    p = PRODUTOS[pid]
    return (
        f"💳 *Instruções de Pagamento*\n\n"
        f"Produto: *{p['nome']}*\n"
        f"Valor: *${p['preco']} USDT*\n"
        f"Rede: *{NETWORK_NAME}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Endereço da carteira:*\n"
        f"`{WALLET_ADDRESS}`\n"
        f"_(clica para copiar)_\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*Como pagar:*\n"
        f"1️⃣ Abre a tua carteira (Binance, Trust Wallet, MetaMask)\n"
        f"2️⃣ Selecciona USDT na rede *BSC / BEP-20*\n"
        f"3️⃣ Envia exactamente *${p['preco']} USDT* para o endereço acima\n"
        f"4️⃣ Após enviar, copia o *TX Hash* (ID da transacção)\n"
        f"5️⃣ Envia o TX Hash aqui neste chat\n\n"
        f"⏱ Prazo: 30 minutos após iniciar o processo\n\n"
        f"❓ Dúvidas? Usa /suporte"
    )

# ─────────────────────────────────────────────
# VALIDAÇÃO AUTOMÁTICA DE PAGAMENTO (NOVA)
# ─────────────────────────────────────────────

async def verificar_pagamento_bscscan(tx_hash: str, valor_esperado_usdt: float) -> dict:
    """
    Verifica se uma transação BSC é válida e se o valor está correcto.
    Retorna: {'success': bool, 'message': str, 'valor': float (opcional)}
    """
    if not BSCSCAN_API_KEY:
        return {'success': False, 'message': '❌ API não configurada. Contacta o suporte.'}
    
    try:
        # 1. Verifica se a transação existe e está confirmada
        url_tx = f"https://api.bscscan.com/api?module=transaction&action=gettxreceiptstatus&txhash={tx_hash}&apikey={BSCSCAN_API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url_tx) as resp:
                dados = await resp.json()
                
                if dados.get('result', {}).get('status') != '1':
                    return {'success': False, 'message': '❌ Transacção não encontrada ou ainda não confirmada. Aguarda 1-2 minutos e tenta novamente.'}
        
        # 2. Obtém detalhes da transacção (valor, de, para)
        url_details = f"https://api.bscscan.com/api?module=account&action=tokentx&txhash={tx_hash}&apikey={BSCSCAN_API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url_details) as resp:
                dados = await resp.json()
                
                if dados.get('status') != '1' or not dados.get('result'):
                    return {'success': False, 'message': '❌ Não foi possível obter detalhes da transacção. Tenta novamente em 30 segundos.'}
                
                # Pega a primeira transferência de token
                tx = dados['result'][0]
                
                # Verifica se o destinatário é a nossa wallet
                if tx.get('to', '').lower() != WALLET_ADDRESS.lower():
                    return {'success': False, 'message': f'⚠️ A transacção foi enviada para outra carteira.\nVerifica o endereço e tenta novamente.'}
                
                # O valor vem em wei (18 decimais para USDT/BSC)
                valor_raw = int(tx.get('value', '0'))
                valor_recebido = valor_raw / 10**18
                
                # Verifica se o valor é suficiente (margem de 0.01 USDT)
                if valor_recebido >= (valor_esperado_usdt - 0.01):
                    return {
                        'success': True, 
                        'message': f'✅ Pagamento confirmado! Recebido: {valor_recebido:.2f} USDT',
                        'valor': valor_recebido,
                        'de': tx.get('from'),
                        'para': tx.get('to')
                    }
                else:
                    return {
                        'success': False, 
                        'message': f'⚠️ Valor incorrecto. Esperado: {valor_esperado_usdt} USDT | Enviado: {valor_recebido:.4f} USDT'
                    }
                    
    except Exception as e:
        logger.error(f"Erro ao verificar BSCScan: {e}")
        return {'success': False, 'message': '❌ Erro ao verificar pagamento. Tenta novamente ou usa /suporte.'}

# ─────────────────────────────────────────────
# HANDLERS DE COMANDOS
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛍 Ver Produtos", callback_data="ver_produtos")],
        [InlineKeyboardButton("❓ Como Funciona", callback_data="ajuda_inline")],
        [InlineKeyboardButton("🆘 Suporte", callback_data="suporte_inline")],
    ]
    await update.message.reply_text(
        "👋 Bem-vindo à *GlowScalePro Store*!\n\n"
        "Aqui podes adquirir os nossos produtos digitais com pagamento seguro em USDT.\n\n"
        "O que queres fazer?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto, teclado = construir_menu_produtos()
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=teclado)


async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG_AJUDA, parse_mode="Markdown")


async def cmd_suporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG_SUPORTE, parse_mode="Markdown")


# ─────────────────────────────────────────────
# HANDLER DE BOTÕES INLINE
# ─────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "ver_produtos":
        texto, teclado = construir_menu_produtos()
        await query.message.reply_text(texto, parse_mode="Markdown", reply_markup=teclado)

    elif data.startswith("produto_"):
        pid = data.replace("produto_", "")
        if pid not in PRODUTOS:
            await query.message.reply_text("❌ Produto não encontrado.")
            return
        p = PRODUTOS[pid]
        texto, teclado = construir_detalhe_produto(pid)
        try:
            with open(p.get("mockup", ""), "rb") as foto:
                await query.message.reply_photo(
                    photo=foto,
                    caption=texto,
                    parse_mode="Markdown",
                    reply_markup=teclado
                )
        except (FileNotFoundError, TypeError):
            await query.message.reply_text(texto, parse_mode="Markdown", reply_markup=teclado)

    elif data.startswith("comprar_"):
        pid = data.replace("comprar_", "")
        if pid not in PRODUTOS:
            await query.message.reply_text("❌ Produto não encontrado.")
            return
        user_id = query.from_user.id
        user_states[user_id] = {
            "step":    "aguarda_tx",
            "produto": pid,
            "tx_hash": None,
            "email":   None,
        }
        await query.message.reply_text(
            construir_instrucoes_pagamento(pid),
            parse_mode="Markdown"
        )

    elif data == "ajuda_inline":
        await query.message.reply_text(MSG_AJUDA, parse_mode="Markdown")

    elif data == "suporte_inline":
        await query.message.reply_text(MSG_SUPORTE, parse_mode="Markdown")


# ─────────────────────────────────────────────
# HANDLER DE MENSAGENS (TX hash + email) - ACTUALIZADO
# ─────────────────────────────────────────────

async def mensagem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id  = update.message.from_user.id
    texto    = update.message.text.strip()
    username = update.message.from_user.username or "sem_username"

    if user_id not in user_states:
        keyboard = [[InlineKeyboardButton("🛍 Ver Produtos", callback_data="ver_produtos")]]
        await update.message.reply_text(
            "Usa o menu abaixo para ver os nossos produtos 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    estado = user_states[user_id]
    pid    = estado.get("produto", "notion_2026")
    p      = PRODUTOS.get(pid, {})

    # Passo 1: aguarda TX hash (COM VERIFICAÇÃO AUTOMÁTICA)
    if estado["step"] == "aguarda_tx":
        tx = texto.replace(" ", "").replace("\n", "")
        
        if tx.startswith("0x") and len(tx) >= 60:
            valor_esperado = p.get("preco", 0)
            
            # Mensagem de "a verificar"
            msg_verificando = await update.message.reply_text(
                "🔍 *A verificar o teu pagamento na blockchain...*\n\n"
                f"💰 Valor esperado: *${valor_esperado} USDT*\n"
                f"🆔 TX Hash: `{tx[:20]}...`\n\n"
                "_Isto demora apenas alguns segundos._",
                parse_mode="Markdown"
            )
            
            # VERIFICAÇÃO AUTOMÁTICA via BSCScan
            resultado = await verificar_pagamento_bscscan(tx, valor_esperado)
            
            if resultado['success']:
                # Pagamento confirmado!
                await msg_verificando.edit_text(
                    f"{resultado['message']}\n\n"
                    f"✅ *Pagamento confirmado com sucesso!*\n\n"
                    f"Agora envia o teu *email* para receberes o produto:\n"
                    f"_(ex: cliente@gmail.com)_",
                    parse_mode="Markdown"
                )
                
                user_states[user_id]["tx_hash"] = tx
                user_states[user_id]["step"] = "aguarda_email"
                
                # Notifica o admin (opcional, apenas para acompanhamento)
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=(
                        f"💰 *PAGAMENTO VERIFICADO AUTOMATICAMENTE*\n"
                        f"✅ {p.get('nome')} - ${valor_esperado} USDT\n"
                        f"👤 @{username} (ID: `{user_id}`)\n"
                        f"🔗 TX: `{tx[:30]}...`\n\n"
                        f"_O produto será enviado automaticamente após o cliente enviar o email._"
                    ),
                    parse_mode="Markdown"
                )
            else:
                await msg_verificando.edit_text(
                    f"{resultado['message']}\n\n"
                    f"Se tens a certeza que fizeste o pagamento correctamente, contacta o suporte: /suporte\n\n"
                    f"_Podes tentar enviar o TX Hash novamente._",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "⚠️ *TX Hash inválido.*\n\n"
                "O TX Hash deve começar por `0x` e ter pelo menos 60 caracteres.\n"
                "Exemplo: `0x1234567890abcdef...`\n\n"
                "Encontra-o no histórico da tua carteira após o envio.",
                parse_mode="Markdown"
            )

    # Passo 2: aguarda email (ENVIO AUTOMÁTICO DO PRODUTO)
    elif estado["step"] == "aguarda_email":
        if "@" in texto and "." in texto:
            email   = texto.lower().strip()
            tx_hash = user_states[user_id]["tx_hash"]

            user_states[user_id]["email"] = email
            
            # ENVIA O PRODUTO AUTOMATICAMENTE (sem precisar de confirmação manual)
            sucesso = enviar_pdf_email(
                destinatario=email,
                produto_nome=p.get("nome", "Produto GlowScalePro"),
                pdf_path=p.get("pdf", "")
            )

            if sucesso:
                await update.message.reply_text(
                    f"🎉 *Produto enviado com sucesso!*\n\n"
                    f"O *{p.get('nome', 'produto')}* foi enviado para *{email}*.\n\n"
                    f"Verifica também a pasta de spam.\n\n"
                    f"Boas leituras! 📚\n"
                    f"— Gabriel Sapalo · GlowScalePro",
                    parse_mode="Markdown"
                )
                
                # Notifica o admin que o produto foi enviado
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=(
                        f"📧 *PRODUTO ENVIADO AUTOMATICAMENTE*\n"
                        f"📦 {p.get('nome')} - ${p.get('preco')} USDT\n"
                        f"👤 @{username} (ID: `{user_id}`)\n"
                        f"📧 Email: {email}\n"
                        f"🔗 TX: `{tx_hash[:30]}...`\n\n"
                        f"_Venda concluída com sucesso!_"
                    ),
                    parse_mode="Markdown"
                )
                
                # Limpa o estado do utilizador
                del user_states[user_id]
            else:
                await update.message.reply_text(
                    "❌ *Erro ao enviar o produto.*\n\n"
                    "Contacta imediatamente o suporte: /suporte\n"
                    "Já fomos notificados e vamos resolver o problema.",
                    parse_mode="Markdown"
                )
                
                # Notifica o admin do erro
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=(
                        f"⚠️ *ERRO NO ENVIO AUTOMÁTICO*\n"
                        f"📦 {p.get('nome')}\n"
                        f"👤 @{username} (ID: `{user_id}`)\n"
                        f"📧 Email: {email}\n"
                        f"🔗 TX: `{tx_hash}`\n\n"
                        f"_Verificar configurações de email e enviar manualmente._"
                    ),
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "⚠️ Email inválido. Envia um endereço válido, ex: cliente@gmail.com"
            )


# ─────────────────────────────────────────────
# COMANDO ADMIN: /confirmar_USERID (MANTIDO PARA FALHAS)
# ─────────────────────────────────────────────

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        return

    try:
        target_user_id = int(update.message.text.split("_")[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Formato inválido. Usa: /confirmar_123456789")
        return

    if target_user_id not in user_states:
        await update.message.reply_text(f"Utilizador {target_user_id} não encontrado ou já processado.")
        return

    estado = user_states[target_user_id]
    email  = estado.get("email")
    pid    = estado.get("produto", "notion_2026")
    p      = PRODUTOS.get(pid, {})

    if not email:
        await update.message.reply_text("Email do cliente não encontrado.")
        return

    sucesso = enviar_pdf_email(
        destinatario=email,
        produto_nome=p.get("nome", "Produto GlowScalePro"),
        pdf_path=p.get("pdf", "")
    )

    if sucesso:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                f"🎉 *Produto enviado com sucesso!*\n\n"
                f"O *{p.get('nome', 'produto')}* foi enviado para *{email}*.\n\n"
                f"Verifica também a pasta de spam.\n\n"
                f"Boas leituras! 📚\n"
                f"— Gabriel Sapalo · GlowScalePro"
            ),
            parse_mode="Markdown"
        )
        await update.message.reply_text(f"✅ Produto enviado com sucesso para {email}!")
        del user_states[target_user_id]
    else:
        await update.message.reply_text(
            f"❌ Erro ao enviar para {email}. Verifica as configurações do Gmail."
        )


# ─────────────────────────────────────────────
# ENVIO DE EMAIL COM PDF
# ─────────────────────────────────────────────

def enviar_pdf_email(destinatario: str, produto_nome: str, pdf_path: str) -> bool:
    try:
        msg            = MIMEMultipart()
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = destinatario
        msg["Subject"] = f"O teu {produto_nome} — GlowScalePro"

        corpo = (
            f"Olá!\n\n"
            f"Obrigado pela tua compra do {produto_nome}.\n\n"
            f"Encontras o teu produto em anexo neste email.\n\n"
            f"Qualquer dúvida, contacta-nos em sac@glowscalepro.com\n\n"
            f"Boas leituras!\n"
            f"Gabriel Sapalo\n"
            f"GlowScalePro — glowscalepro.com"
        )
        msg.attach(MIMEText(corpo, "plain"))

        with open(pdf_path, "rb") as f:
            parte = MIMEBase("application", "octet-stream")
            parte.set_payload(f.read())
            encoders.encode_base64(parte)
            parte.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(pdf_path)}"'
            )
            msg.attach(parte)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(EMAIL_SENDER, EMAIL_PASSWORD)
            servidor.sendmail(EMAIL_SENDER, destinatario, msg.as_string())

        logger.info(f"PDF enviado com sucesso para {destinatario}")
        return True

    except Exception as e:
        logger.error(f"Erro ao enviar email para {destinatario}: {e}")
        return False


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    token = BOT_TOKEN.strip().replace("\n","").replace("\r","").replace(" ","")
    logger.info(f"TOKEN DEBUG: {repr(token[:20])}...")
    logger.info("Bot GlowScalePro iniciado com validação automática BSCScan...")
    
    if BSCSCAN_API_KEY:
        logger.info("✅ BSCScan API configurada - validação automática activa")
    else:
        logger.warning("⚠️ BSCScan API NÃO configurada - modo manual apenas")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("comprar", cmd_comprar))
    app.add_handler(CommandHandler("ajuda",   cmd_ajuda))
    app.add_handler(CommandHandler("suporte", cmd_suporte))
    app.add_handler(MessageHandler(filters.Regex(r"^/confirmar_\d+$"), confirmar))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem_handler))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
