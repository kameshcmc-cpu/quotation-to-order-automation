"""
Telegram Bot for AI Quotation-to-Order Automation
Handles customer conversations, quote requests, and approvals.
"""
import asyncio
import io
import logging
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from backend.config import settings
from backend.database import SessionLocal
from backend import crud, schemas
from backend.ai_engine import extract_quote_from_conversation, generate_negotiation_response
from backend.pdf_generator import generate_quotation_pdf, generate_invoice_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OWNER_CHAT_ID = settings.OWNER_TELEGRAM_CHAT_ID


async def notify_owner(bot: Bot, message: str, keyboard: InlineKeyboardMarkup = None):
    """Send a notification to the business owner."""
    if not OWNER_CHAT_ID:
        return
    try:
        await bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=message,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Owner notification failed: {e}")


def get_or_create_customer(db, telegram_user) -> object:
    """Get existing customer or create new one from Telegram user."""
    telegram_id = str(telegram_user.id)
    customer = crud.get_customer_by_telegram_id(db, telegram_id)
    if not customer:
        name = f"{telegram_user.first_name or ''} {telegram_user.last_name or ''}".strip()
        customer = crud.create_customer(db, schemas.CustomerCreate(
            name=name or f"Customer_{telegram_id}",
            telegram_id=telegram_id,
            phone=telegram_user.username and f"@{telegram_user.username}",
        ))
    return customer


# ── Command Handlers ──────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        customer = get_or_create_customer(db, update.effective_user)
        products = crud.get_products(db)
        available = [p for p in products if p.available_quantity > 0]

        product_lines = ""
        if available:
            lines = []
            for p in available:
                lines.append(
                    f"  • <b>{p.name}</b> — {p.available_quantity:g} {p.unit} available"
                    f" @ Rs.{p.base_price:.2f}/{p.unit}"
                )
            product_lines = "\n\n<b>Available Products:</b>\n" + "\n".join(lines)

        welcome = (
            f"Namaste <b>{customer.name}</b>!\n\n"
            f"Welcome to <b>{settings.BUSINESS_NAME}</b>."
            f"{product_lines}\n\n"
            f"Just tell me what you need with quantity and I will generate a quote instantly.\n\n"
            f"<i>Example: I need 200 kg Basmati Rice and 100 kg Toor Dal</i>\n\n"
            f"/status — Check your quote status\n"
            f"/myquotes — View all your quotes"
        )
        await update.message.reply_text(welcome, parse_mode="HTML")
    finally:
        db.close()


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        customer = get_or_create_customer(db, update.effective_user)
        quotes = crud.get_quotations(db, customer_id=customer.id)
        if not quotes:
            await update.message.reply_text("You have no quotes yet. Tell me what products you need!")
            return

        lines = ["<b>Your Recent Quotes:</b>\n"]
        for q in quotes[:5]:
            status_emoji = {
                "draft": "📝", "pending_approval": "⏳", "approved": "✅",
                "sent": "📤", "accepted": "🤝", "converted": "📦",
                "rejected": "❌"
            }.get(q.status, "•")
            lines.append(
                f"{status_emoji} <b>{q.quote_number}</b> — ₹{q.total:,.2f} — {q.status.replace('_', ' ').title()}"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    finally:
        db.close()


async def myquotes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await status_command(update, context)


async def products_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        products = crud.get_products(db)
        available = [p for p in products if p.available_quantity > 0]
        if not available:
            await update.message.reply_text("No products available at the moment. Please check back later.")
            return
        lines = ["<b>Available Products:</b>\n"]
        for p in available:
            lines.append(
                f"• <b>{p.name}</b>\n"
                f"  Stock: {p.available_quantity:g} {p.unit}  |  Price: Rs.{p.base_price:.2f}/{p.unit}"
            )
        lines.append("\nReply with your requirement to get a quote instantly.")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
    finally:
        db.close()


# ── Message Handler (Core AI Flow) ────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()

    try:
        customer = get_or_create_customer(db, update.effective_user)
        crud.save_message(db, customer.id, chat_id, text, is_from_customer=True)

        upper_text = text.upper().strip()

        # Check for quote acceptance
        if upper_text.startswith("ACCEPT "):
            await handle_quote_acceptance(update, context, text, customer, db, chat_id)
            return

        # Check for quote rejection/cancel
        if upper_text.startswith("REJECT ") or upper_text.startswith("CANCEL "):
            await handle_quote_rejection(update, context, text, customer, db)
            return

        # Any other message — treat as a quote request or negotiation
        await update.message.reply_text(
            "📋 Let me analyze your request and prepare a quotation...",
        )

        # Get recent conversation context
        history = crud.get_conversation_history(db, chat_id, limit=10)
        conversation_context = "\n".join([
            f"{'Customer' if h.is_from_customer else 'Business'}: {h.message}"
            for h in reversed(history)
        ])

        products = crud.get_products(db)

        # Check if customer has an active sent quote (negotiation mode)
        active_quotes = crud.get_quotations(db, status="sent", customer_id=customer.id)
        if active_quotes:
            latest_quote = active_quotes[0]
            neg_response = await generate_negotiation_response(
                {"total": latest_quote.total, "discount_percent": latest_quote.discount_percent},
                text
            )
            await update.message.reply_text(neg_response)
            crud.set_quote_status(db, latest_quote.id, "negotiating")
            crud.save_message(db, customer.id, chat_id, neg_response, is_from_customer=False)

            await notify_owner(
                context.bot,
                f"🔄 <b>Negotiation</b> from {customer.name}\n"
                f"Quote: {latest_quote.quote_number} (₹{latest_quote.total:,.2f})\n"
                f"Message: {text}\n\n"
                f"Suggested response sent. Review at /app",
                InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Update Quote", callback_data=f"edit_quote_{latest_quote.id}"),
                    InlineKeyboardButton("📋 View", callback_data=f"view_quote_{latest_quote.id}"),
                ]])
            )
            return

        # Generate new quote from conversation
        result = await extract_quote_from_conversation(
            conversation_text=conversation_context,
            products=products,
            business_context=settings.BUSINESS_NAME
        )

        if not result.get("items"):
            await update.message.reply_text(
                "I didn't quite catch what products you need. Could you please specify:\n"
                "• Product name\n• Quantity\n• Any special requirements\n\n"
                "Example: 'I need 500 kg of basmati rice and 200 litres of sunflower oil'"
            )
            return

        items = []
        for item in result["items"]:
            matched_product = None
            for p in products:
                if p.name.lower() in item["description"].lower() or item["description"].lower() in p.name.lower():
                    matched_product = p
                    break
            items.append(schemas.QuotationItemCreate(
                description=item["description"],
                quantity=item["quantity"],
                unit=item["unit"],
                unit_price=item.get("unit_price", 0),
                product_id=matched_product.id if matched_product else None,
                hsn_code=item.get("hsn_code") or (matched_product.hsn_code if matched_product else None),
            ))

        quote_data = schemas.QuotationCreate(
            customer_id=customer.id,
            items=items,
            payment_terms=result.get("payment_terms", "100% advance"),
            delivery_terms=result.get("delivery_terms", "Ex-works"),
            notes=result.get("notes", ""),
            source_conversation=conversation_context,
        )
        quote = crud.create_quotation(db, quote_data, ai_notes=result.get("ai_suggestions", ""))
        crud.set_quote_status(db, quote.id, "pending_approval")

        items_summary = "\n".join([
            f"  • {i.description}: {i.quantity} {i.unit} @ ₹{i.unit_price:,.2f}"
            for i in quote.items
        ])
        await update.message.reply_text(
            f"✅ Quote generated: <b>{quote.quote_number}</b>\n\n"
            f"<b>Items:</b>\n{items_summary}\n\n"
            f"<b>Estimated Total:</b> ₹{quote.total:,.2f}\n\n"
            f"⏳ Pending owner review. You'll receive the final quote shortly.",
            parse_mode="HTML"
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve & Send", callback_data=f"approve_{quote.id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{quote.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{quote.id}"),
        ]])
        await notify_owner(
            context.bot,
            f"🆕 <b>New Quote Request</b>\n"
            f"Customer: {customer.name} ({customer.phone or 'no phone'})\n"
            f"Quote: {quote.quote_number}\n"
            f"Items: {len(quote.items)} item(s)\n"
            f"Total: ₹{quote.total:,.2f}",
            keyboard
        )

    except Exception as e:
        logger.error(f"Message handler error: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, something went wrong. Please try again or contact us directly."
        )
    finally:
        db.close()


async def handle_quote_acceptance(update, context, text, customer, db, chat_id):
    parts = text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text("Please specify the quote number. Example: ACCEPT QT-26-0001")
        return

    quote_number = parts[1].upper()
    quotes = crud.get_quotations(db, customer_id=customer.id)
    target_quote = next((q for q in quotes if q.quote_number == quote_number), None)

    if not target_quote:
        await update.message.reply_text(f"Quote {quote_number} not found.")
        return

    if target_quote.status not in ("sent", "negotiating"):
        await update.message.reply_text(f"Quote {quote_number} cannot be accepted (status: {target_quote.status})")
        return

    crud.set_quote_status(db, target_quote.id, "accepted")
    crud.save_message(db, customer.id, chat_id, f"ACCEPTED: {quote_number}", is_from_customer=True)

    await update.message.reply_text(
        f"🎉 Thank you! Quote <b>{quote_number}</b> has been accepted.\n\n"
        f"We'll process your order and send the invoice shortly.\n"
        f"Total Amount: ₹{target_quote.total:,.2f}",
        parse_mode="HTML"
    )

    await notify_owner(
        context.bot,
        f"🤝 <b>Quote Accepted!</b>\n"
        f"Customer: {customer.name}\n"
        f"Quote: {quote_number}\n"
        f"Amount: ₹{target_quote.total:,.2f}",
        InlineKeyboardMarkup([[
            InlineKeyboardButton("📦 Convert to Order", callback_data=f"convert_{target_quote.id}"),
        ]])
    )


async def handle_quote_rejection(update, context, text, customer, db):
    parts = text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text("Please specify the quote number. Example: REJECT QT-26-0001")
        return

    quote_number = parts[1].upper()
    quotes = crud.get_quotations(db, customer_id=customer.id)
    target_quote = next((q for q in quotes if q.quote_number == quote_number), None)

    if target_quote:
        crud.set_quote_status(db, target_quote.id, "rejected")

    await update.message.reply_text(
        f"Quote {quote_number} has been rejected. Feel free to send a new requirement anytime!"
    )


# ── Callback Query Handler (Owner Actions) ────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    db = SessionLocal()

    try:
        if data.startswith("approve_"):
            quote_id = int(data.split("_")[1])
            quote = crud.set_quote_status(db, quote_id, "approved")
            if not quote:
                await query.edit_message_text("Quote not found.")
                return

            pdf_bytes = generate_quotation_pdf(quote)
            await context.bot.send_document(
                chat_id=quote.customer.telegram_id,
                document=io.BytesIO(pdf_bytes),
                filename=f"{quote.quote_number}.pdf",
                caption=(
                    f"Dear {quote.customer.name},\n\n"
                    f"Please find your quotation {quote.quote_number} attached.\n"
                    f"Total: ₹{quote.total:,.2f}\n"
                    f"Valid until: {quote.valid_until.strftime('%d-%b-%Y')}\n\n"
                    f"Reply 'ACCEPT {quote.quote_number}' to confirm."
                )
            )
            crud.set_quote_status(db, quote_id, "sent")
            await query.edit_message_text(
                f"✅ Quote {quote.quote_number} approved and sent to {quote.customer.name}"
            )

        elif data.startswith("reject_"):
            quote_id = int(data.split("_")[1])
            crud.set_quote_status(db, quote_id, "rejected")
            await query.edit_message_text(f"❌ Quote rejected.")

        elif data.startswith("convert_"):
            quote_id = int(data.split("_")[1])
            order = crud.convert_quote_to_order(db, quote_id)
            if not order:
                await query.edit_message_text("Could not convert to order. Check quote status.")
                return

            invoice_pdf = generate_invoice_pdf(order)
            quote = order.quotation
            await context.bot.send_document(
                chat_id=quote.customer.telegram_id,
                document=io.BytesIO(invoice_pdf),
                filename=f"{order.invoice_number}.pdf",
                caption=(
                    f"Dear {quote.customer.name},\n\n"
                    f"Your order has been confirmed! 🎉\n"
                    f"Invoice: {order.invoice_number}\n"
                    f"Amount: ₹{quote.total:,.2f}\n"
                    f"{f'Payment Link: {order.payment_link}' if order.payment_link else ''}"
                )
            )
            await query.edit_message_text(
                f"📦 Order {order.order_number} created. Invoice sent to customer."
            )

        elif data.startswith("view_quote_"):
            quote_id = int(data.split("_")[2])
            quote = crud.get_quotation(db, quote_id)
            if quote:
                items_text = "\n".join([f"  • {i.description}: {i.quantity} {i.unit} @ ₹{i.unit_price:,.2f}"
                                        for i in quote.items])
                await query.message.reply_text(
                    f"<b>{quote.quote_number}</b>\n"
                    f"Customer: {quote.customer.name}\n"
                    f"Status: {quote.status}\n\n"
                    f"Items:\n{items_text}\n\n"
                    f"Total: ₹{quote.total:,.2f}",
                    parse_mode="HTML"
                )

    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        await query.edit_message_text("An error occurred. Please use the web dashboard.")
    finally:
        db.close()


async def process_update(update_data: dict):
    """Process a single update (for webhook mode)."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    _register_handlers(app)
    update = Update.de_json(update_data, app.bot)
    await app.process_update(update)


def build_app() -> Application:
    """Build and return the configured Telegram Application."""
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("myquotes", myquotes_command))
    app.add_handler(CommandHandler("products", products_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


def run_bot():
    """Run the bot in polling mode (legacy / standalone use)."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Bot will not start.")
        return
    app = build_app()
    logger.info("Starting Telegram bot in polling mode...")
    app.run_polling(drop_pending_updates=True)
