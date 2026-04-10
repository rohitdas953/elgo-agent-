from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from activity_log import log_event
from telegram_bot.models import ProductInfo
from telegram_bot.orders.placer import place_order
from telegram_bot.payment.pay import execute_payment
from telegram_bot.payment.wallet import get_balance, get_or_create_wallet, top_up_instructions
from telegram_bot.search.aggregator import search_all_platforms
from telegram_bot.search.models import PlatformResult
from telegram_bot.session import UserState, session_manager
from telegram_bot.vision import recognize_product

logger = logging.getLogger("agentscore.handlers")

_PLATFORM_EMOJI = {
    "amazon": "🟠",
    "flipkart": "🔵",
    "zepto": "🟢",
    "instamart": "🟡",
}

_PLATFORM_LABEL = {
    "amazon": "Amazon",
    "flipkart": "Flipkart",
    "zepto": "Zepto",
    "instamart": "Instamart",
}


def _format_price(val: float) -> str:
    """Format as ₹1,299."""
    return f"₹{val:,.0f}"


def _format_results_message(
    product_name: str, results: list[PlatformResult]
) -> str:
    """Build the Telegram results message with emojis and alignment."""
    lines = [f"🛍 *{product_name}*\n", "Here are the best prices I found:\n"]

    for idx, r in enumerate(results, 1):
        emoji = _PLATFORM_EMOJI.get(r.platform, "⚪")
        label = _PLATFORM_LABEL.get(r.platform, r.platform.title())
        price_str = _format_price(r.price)
        delivery_icon = "🚀" if "min" in r.delivery_time.lower() else "📦"

        line = f"{idx}. {emoji} *{label}*     {price_str}   {delivery_icon} {r.delivery_time}"
        if r.delivery_fee > 0:
            line += f" (+{_format_price(r.delivery_fee)} delivery)"
        lines.append(line)

    # Best deal comparison
    if len(results) >= 2:
        cheapest = results[0]
        most_expensive = results[-1]
        savings = most_expensive.total_cost - cheapest.total_cost
        if savings > 0:
            best_label = _PLATFORM_LABEL.get(cheapest.platform, cheapest.platform)
            worst_label = _PLATFORM_LABEL.get(most_expensive.platform, most_expensive.platform)
            lines.append(
                f"\n💡 *Best deal: {best_label} saves you {_format_price(savings)} vs {worst_label}*"
            )

    lines.append(
        "\nReply with *1*, *2*, or *3* to place your order."
        "\nType *cancel* to search again."
    )
    return "\n".join(lines)


# ─────────────────────────── /start ───────────────────────────


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — greet user, create wallet."""
    user = update.effective_user
    if not user or not update.effective_chat:
        return

    user_id = user.id
    logger.info("cmd_start user=%d username=%s", user_id, user.username)
    log_event("bot_cmd", f"/start by {user.first_name}", f"user_id={user_id}", source="telegram", user_id=user_id)

    # Ensure wallet exists
    wallet = await get_or_create_wallet(user_id)

    session = await session_manager.get(user_id)
    session.reset()

    await update.effective_chat.send_message(
        f"👋 Hey *{user.first_name}*! Welcome to *AgentScore Shopping Bot*.\n\n"
        f"📸 Send me a photo of any product and I'll find the cheapest price "
        f"across *Amazon, Flipkart, Zepto & Instamart* and place the order for you.\n\n"
        f"💰 Your ALGO wallet: `{wallet['address'][:12]}...{wallet['address'][-6:]}`\n\n"
        f"Type /help for more info.",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─────────────────────────── /help ────────────────────────────


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — explain features and platforms."""
    if not update.effective_chat:
        return

    logger.info("cmd_help user=%d", update.effective_user.id if update.effective_user else 0)

    await update.effective_chat.send_message(
        "ℹ️ *AgentScore Shopping Bot — Help*\n\n"
        "*Supported Platforms:*\n"
        "🟠 Amazon — Fast Prime delivery\n"
        "🔵 Flipkart — Great deals & selection\n"
        "🟢 Zepto — 10-min grocery delivery\n"
        "🟡 Instamart — 15-20 min grocery delivery\n\n"
        "*How it works:*\n"
        "1️⃣ Send a product photo\n"
        "2️⃣ AI identifies the product\n"
        "3️⃣ We search all platforms for the best price\n"
        "4️⃣ Pick your preferred option\n"
        "5️⃣ Pay with ALGO via your wallet\n\n"
        "*Commands:*\n"
        "/start — Start fresh\n"
        "/help — This message\n"
        "/wallet — View wallet & balance\n"
        "/cancel — Cancel current order",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─────────────────────── /wallet ────────────────────────────


async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wallet — show wallet address and balance."""
    user = update.effective_user
    if not user or not update.effective_chat:
        return

    user_id = user.id
    logger.info("cmd_wallet user=%d", user_id)

    try:
        wallet = await get_or_create_wallet(user_id)
        balance = await get_balance(user_id)

        await update.effective_chat.send_message(
            f"💳 *Your AgentScore Wallet*\n\n"
            f"Address:\n`{wallet['address']}`\n\n"
            f"Balance: *{balance:.4f} ALGO*\n"
            f"Created: {wallet['created_at']}\n\n"
            f"Send ALGO to this address on Algorand Testnet to top up.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        logger.error("wallet_handler_error user=%d error=%s", user_id, str(exc)[:200])
        await update.effective_chat.send_message(
            "❌ Error loading wallet. Please try again.",
        )


# ─────────────────────── /cancel ───────────────────────────


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel — reset session."""
    user = update.effective_user
    if not user or not update.effective_chat:
        return

    session = await session_manager.get(user.id)
    session.reset()

    logger.info("cmd_cancel user=%d", user.id)
    await update.effective_chat.send_message(
        "🔄 Cancelled. Send me a new product photo to search again!",
    )


# ──────────────────── Photo handler ───────────────────────


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages — the core product recognition + search flow."""
    user = update.effective_user
    message = update.message
    if not user or not message or not update.effective_chat:
        return

    user_id = user.id
    chat = update.effective_chat
    logger.info("photo_received user=%d", user_id)
    log_event("vision", "📷 Photo received", f"User {user_id} sent a product photo", source="telegram", user_id=user_id)

    session = await session_manager.get(user_id)

    # Step 1 — Download highest resolution photo
    photos = message.photo
    if not photos:
        await chat.send_message("📸 Please send a clear photo of the product.")
        return

    photo = photos[-1]  # highest resolution
    status_msg = await chat.send_message("📷 Analyzing your photo...")

    try:
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
    except Exception as exc:
        logger.error("photo_download_error user=%d error=%s", user_id, str(exc)[:200])
        await status_msg.edit_text("❌ Failed to download photo. Please try again.")
        return

    # Step 2 — AI Vision recognition
    try:
        await status_msg.edit_text("🧠 Identifying product with AI...")
        product = await recognize_product(bytes(image_bytes))
    except Exception as exc:
        logger.error("vision_error user=%d error=%s", user_id, str(exc)[:200])
        product = None

    if not product:
        await status_msg.edit_text(
            "🤔 I couldn't identify the product clearly.\n"
            "Please send a clearer photo or try a different angle."
        )
        return

    # Step 3 — Confirm identification
    session.identified_product = product
    brand_str = f" by *{product.brand}*" if product.brand else ""
    log_event("vision", f"✅ Identified: {product.product_name}", f"Category: {product.category}, Brand: {product.brand}", level="success", source="vision", product=product.product_name, category=product.category)
    await status_msg.edit_text(
        f"🔍 Identified: *{product.product_name}*{brand_str}\n"
        f"Category: {product.category}\n\n"
        f"Searching for best prices...",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Step 4 — Search all platforms
    try:
        results = await search_all_platforms(
            search_query=product.search_query,
            category=product.category,
            is_grocery=product.is_grocery,
        )
    except Exception as exc:
        logger.error("search_error user=%d error=%s", user_id, str(exc)[:200])
        await status_msg.edit_text("❌ Search failed. Please try again.")
        session.reset()
        return

    if not results:
        await status_msg.edit_text(
            "😕 No results found for this product. Try a different photo?"
        )
        session.reset()
        return

    # Step 5 — Display results
    session.search_results = results
    session.state = UserState.AWAITING_SELECTION
    session.touch()

    results_text = _format_results_message(product.product_name, results)
    await status_msg.edit_text(results_text, parse_mode=ParseMode.MARKDOWN)

    log_event("search", f"🔍 Search complete: {len(results)} results", f"Product: {product.product_name}", level="success", source="search", results_count=len(results), platforms=[r.platform for r in results])
    logger.info(
        "search_complete user=%d product=%s results=%d",
        user_id,
        product.product_name,
        len(results),
    )


# ──────────────────── Text message handler ────────────────────


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages — numbers for selection, YES for confirmation, cancel."""
    user = update.effective_user
    message = update.message
    if not user or not message or not message.text or not update.effective_chat:
        return

    user_id = user.id
    text = message.text.strip()
    chat = update.effective_chat

    session = await session_manager.get(user_id)

    # --- Handle "cancel" at any point ---
    if text.lower() == "cancel":
        session.reset()
        await chat.send_message("🔄 Cancelled. Send me a new product photo!")
        return

    # --- Number selection (1, 2, 3) ---
    if session.state == UserState.AWAITING_SELECTION:
        if text.isdigit():
            choice = int(text)
            if 1 <= choice <= len(session.search_results):
                selected = session.search_results[choice - 1]
                session.selected_option = selected
                session.state = UserState.AWAITING_CONFIRMATION
                session.touch()

                platform_label = _PLATFORM_LABEL.get(selected.platform, selected.platform)
                total = selected.total_cost

                await chat.send_message(
                    f"🛒 *Confirm Order*\n\n"
                    f"Product: *{selected.product_name}*\n"
                    f"Platform: *{platform_label}*\n"
                    f"Price: *{_format_price(selected.price)}*\n"
                    f"Delivery: {selected.delivery_time}"
                    + (f" (+{_format_price(selected.delivery_fee)} fee)" if selected.delivery_fee > 0 else "")
                    + f"\n*Total: {_format_price(total)}*\n\n"
                    f"Reply *YES* to confirm or *cancel* to go back.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                log_event("order", f"🛒 Selected {selected.platform.title()}", f"{selected.product_name} at ₹{selected.price}", source="order", platform=selected.platform, price=selected.price)
                logger.info("selection_made user=%d choice=%d platform=%s", user_id, choice, selected.platform)
                return
            else:
                await chat.send_message(
                    f"Please reply with a number between 1 and {len(session.search_results)}."
                )
                return
        else:
            await chat.send_message(
                "Please reply with a number (1/2/3) to select, or *cancel*.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

    # --- YES confirmation ---
    if session.state == UserState.AWAITING_CONFIRMATION:
        if text.upper() == "YES":
            selected = session.selected_option
            if not selected:
                await chat.send_message("❌ Session expired. Send a new photo!")
                session.reset()
                return

            await chat.send_message("⏳ Placing your order...")

            # Place order
            try:
                order_result = await place_order(
                    user_id=user_id,
                    result=selected,
                )
            except Exception as exc:
                logger.error("order_error user=%d error=%s", user_id, str(exc)[:200])
                await chat.send_message("❌ Order placement failed. Please try again.")
                session.reset()
                return

            if order_result.success:
                # Execute payment
                payment_result = await execute_payment(
                    user_id=user_id,
                    amount_inr=selected.total_cost,
                    platform=selected.platform,
                    order_id=order_result.order_id or "UNKNOWN",
                )

                if payment_result.success:
                    log_event("payment", f"💰 Payment confirmed: {payment_result.amount_algo:.4f} ALGO", f"Txn: {payment_result.txn_id}", level="success", source="algorand", txn_id=payment_result.txn_id, amount_algo=payment_result.amount_algo)
                    log_event("order", f"✅ Order placed: {order_result.order_id}", f"{selected.platform.title()} — {selected.product_name}", level="success", source="order", order_id=order_result.order_id, platform=selected.platform)
                    tracking = (
                        f"\n🔗 Track: {order_result.tracking_url}"
                        if order_result.tracking_url
                        else ""
                    )
                    await chat.send_message(
                        f"✅ *Order Placed Successfully!*\n\n"
                        f"📦 Order ID: `{order_result.order_id}`\n"
                        f"🕐 Delivery: {order_result.estimated_delivery}\n"
                        f"💰 Paid: {payment_result.amount_algo:.4f} ALGO "
                        f"(~{_format_price(payment_result.amount_inr)})\n"
                        f"{tracking}\n\n"
                        f"🔗 Txn: `{payment_result.txn_id}`\n\n"
                        f"Send another photo to shop more! 🛍",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                else:
                    # Payment failed — show top-up instructions
                    instructions = await top_up_instructions(user_id)
                    await chat.send_message(
                        f"⚠️ *Payment Required*\n\n"
                        f"{payment_result.error}\n\n"
                        f"{instructions}\n\n"
                        f"I'll place your order once your wallet is funded.",
                        parse_mode=ParseMode.MARKDOWN,
                    )

                logger.info(
                    "order_complete user=%d order_id=%s payment=%s",
                    user_id,
                    order_result.order_id,
                    "OK" if payment_result.success else "PENDING",
                )
            else:
                await chat.send_message(
                    f"❌ Order failed: {order_result.error}\nPlease try again."
                )

            session.reset()
            return
        else:
            await chat.send_message(
                "Reply *YES* to confirm or *cancel* to go back.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

    # --- Default: treat text as a product search query (3+ chars) ---
    if len(text) >= 3:
        logger.info("text_search user=%d query=%s", user_id, text[:50])
        log_event("search", f"🔍 Text search: {text}", f"User {user_id} typed a product name", source="telegram", user_id=user_id)

        status_msg = await chat.send_message("🔍 Searching all platforms...")

        try:
            # Detect if it's likely a grocery item
            grocery_keywords = {"chips", "biscuit", "rice", "dal", "oil", "soap", "shampoo", "milk", "bread", "sugar", "tea", "coffee", "noodles", "atta", "ghee", "masala"}
            is_grocery = any(kw in text.lower() for kw in grocery_keywords)
            category = "grocery" if is_grocery else "general"

            results = await search_all_platforms(
                search_query=text,
                category=category,
                is_grocery=is_grocery,
            )
        except Exception as exc:
            logger.error("text_search_error user=%d error=%s", user_id, str(exc)[:200])
            await status_msg.edit_text("❌ Search failed. Please try again.")
            return

        if not results:
            await status_msg.edit_text("😕 No results found. Try a different product name?")
            return

        # Build a synthetic ProductInfo for the session
        session.identified_product = ProductInfo(
            product_name=text,
            category=category,
            brand=None,
            search_query=text,
            is_grocery=is_grocery,
        )
        session.search_results = results
        session.state = UserState.AWAITING_SELECTION
        session.touch()

        results_text = _format_results_message(text, results)
        await status_msg.edit_text(results_text, parse_mode=ParseMode.MARKDOWN)

        log_event("search", f"✅ Search complete: {len(results)} results", f"Query: {text}", level="success", source="search", results_count=len(results))
        return

    await chat.send_message(
        "📸 Send me a product photo or type a product name!\n"
        "Examples: *iPhone 15*, *Lays chips*, *JBL speaker*\n"
        "Or type /help for more info.",
        parse_mode=ParseMode.MARKDOWN,
    )
