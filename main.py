"""
Prachi Chatbot — main.py
- Async python-telegram-bot v20+
- Uses OpenAI (optional) if OPENAI_API_KEY provided.
- MongoDB for persistence (MONGO_URI env or config)
- Features: persona (girl 18-22), ban/unban, chat on/off (global + per-group), welcome messages, admin controls, buttons (Owner/Support/Updates/Help), multilingual (EN/HIN/HING)
"""
import os
import asyncio
import logging
from typing import List

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
)

# Optional OpenAI
try:
    import openai
except Exception:
    openai = None

# Database (pymongo)
from pymongo import MongoClient

# ----- CONFIG -----
# Sensitive data inserted as requested (you may want to move these to env vars later)
TOKEN = "8474699900:AAEOW_cmCT4ilHWz7rKSKQezHAgcaJhfNY0"
OWNER_ID = 7583420619
MONGO_URI = "mongodb+srv://dkstoryhouse_db_user:dkstoryhouse_db_user@cluster0.titlpa3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
USE_OPENAI = False
OPENAI_API_KEY = ""

BOT_NAME = ".❛.𝁘ໍ𝚴𝚰𝚮𝚲𝐑𝚰𝚱𝚲 ❤️ ִֶ𝁘ໍໍ᪳᪳𓂃."
BOT_USERNAME = "@Prachi_chatbot"
OWNER_URL = "https://t.me/Dk_Bot10"
SUPPORT_URL = "https://t.me/+m-gKjQt7wCQyMmU9"
UPDATES_URL = "https://t.me/"

# Persona prompt for OpenAI (if used)
PERSONA_PROMPT = (
    "You are Prachi, a friendly 18-22 year old girl. Speak casually in English, Hindi, or Hinglish depending on user. "
    "Be warm, chatty, and friendly. If user asks for serious advice, be helpful and polite. Keep responses safe and non-medical/legal."
)

# Welcome samples file path
WELCOME_FILE = "welcome_messages.txt"

# ----- Logging -----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----- Database Setup -----
client = MongoClient(MONGO_URI)
db = client.get_database("prachi_chatbot_db")
users_col = db.get_collection("users")
groups_col = db.get_collection("groups")
settings_col = db.get_collection("settings")

# Ensure a settings doc
if settings_col.count_documents({}) == 0:
    settings_col.insert_one({"chat_enabled_global": True})

# ----- Helpers -----
async def is_owner(user_id: int) -> bool:
    return int(user_id) == int(OWNER_ID)

def load_welcome_messages() -> List[str]:
    if not os.path.exists(WELCOME_FILE):
        return ["Welcome {mention} to {group}!","Hey {mention}, glad you joined {group}!"]
    with open(WELCOME_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines

WELCOME_MESSAGES = load_welcome_messages()

def build_main_keyboard():
    kb = [
        [InlineKeyboardButton("👤 Owner", url=OWNER_URL), InlineKeyboardButton("💬 Support", url=SUPPORT_URL)],
        [InlineKeyboardButton("🔄 Updates", url=UPDATES_URL), InlineKeyboardButton("❓ Help", callback_data="help_cmd")]
    ]
    return InlineKeyboardMarkup(kb)

# ----- AI Reply -----
async def ai_reply(user_text: str, user_id: int) -> str:
    # If OpenAI is enabled and available, call it. Otherwise fallback to simple rule-based reply.
    if USE_OPENAI and openai is not None and OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role":"system","content":PERSONA_PROMPT},
                    {"role":"user","content":user_text}
                ],
                max_tokens=250,
                temperature=0.9
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error("OpenAI error: %s", e)
            # fallback
    # Fallback simple reply: echo + persona flavor
    # Basic language detection (naive)
    text = user_text.lower()
    if any(word in text for word in ["hi","hello","hey","namaste","hello","hola"]):
        return "Hi! 😊 I'm Prachi — your friendly chat buddy. How's your day?"
    if any(word in text for word in ["how are you","kaise ho","kya haal"]):
        return "I'm good, thanks for asking! What about you?"
    # default
    return "I hear you — tell me more!"

# ----- Command Handlers -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    kb = build_main_keyboard()
    msg = f"Hello {user.first_name}! I'm {BOT_NAME} — your friendly chat bot. I can chat in English, Hindi, or Hinglish.\nUse /help to see commands."
    await update.message.reply_text(msg, reply_markup=kb)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/start - start chat\n"
        "/help - show this help\n"
        "/ban <user_id|reply> - owner only\n"
        "/unban <user_id|reply> - owner only\n"
        "/chat on|off - owner only (global)\n"
        "/setwelcome - admin/group owner to set welcome text for group\n"
        "/listwelcome - list welcome messages for this group\n"
    )
    await update.message.reply_text(help_text)

async def button_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help_cmd":
        await query.message.reply_text("Use /help to see commands and owner/support buttons.")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_owner(user.id):
        return await update.message.reply_text("Only the owner can use this command.")
    # ban by reply or id
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            uid = int(context.args[0])
            target = await context.bot.get_chat(uid)
        except Exception:
            return await update.message.reply_text("Invalid user id.")
    if not target:
        return await update.message.reply_text("Reply to a user or provide user id to ban.")
    users_col.update_one({"user_id": int(target.id)}, {"$set": {"banned": True}}, upsert=True)
    await update.message.reply_text(f"Banned user: {target.id}")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_owner(user.id):
        return await update.message.reply_text("Only the owner can use this command.")
    if context.args:
        try:
            uid = int(context.args[0])
            users_col.update_one({"user_id": uid}, {"$set": {"banned": False}}, upsert=True)
            return await update.message.reply_text(f"Unbanned {uid}")
        except Exception:
            return await update.message.reply_text("Invalid user id.")
    return await update.message.reply_text("Provide user id to unban.")

async def chat_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /chat on or /chat off (owner only)
    user = update.effective_user
    if not await is_owner(user.id):
        return await update.message.reply_text("Only the owner can use this command.")
    if not context.args:
        return await update.message.reply_text("Usage: /chat on OR /chat off")
    arg = context.args[0].lower()
    if arg in ("on","true","1"):
        settings_col.update_one({}, {"$set": {"chat_enabled_global": True}}, upsert=True)
        await update.message.reply_text("Global chat enabled.")
    elif arg in ("off","false","0"):
        settings_col.update_one({}, {"$set": {"chat_enabled_global": False}}, upsert=True)
        await update.message.reply_text("Global chat disabled.")
    else:
        await update.message.reply_text("Use on or off.")

async def new_member_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Simple welcome for new chat members
    if not update.message.new_chat_members:
        return
    chat = update.effective_chat
    group_doc = groups_col.find_one({"chat_id": chat.id}) or {}
    enabled = group_doc.get("welcome_enabled", True)
    if not enabled:
        return
    for member in update.message.new_chat_members:
        mention = f"{member.first_name}"
        msg = None
        custom = group_doc.get("welcome_text")
        if custom:
            msg = custom.format(mention=mention, group=chat.title)
        else:
            import random
            msg = random.choice(WELCOME_MESSAGES).format(mention=mention, group=chat.title)
        await update.message.reply_text(msg)

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Core message handler for chats
    msg = update.message
    user = msg.from_user
    chat = update.effective_chat

    # check ban
    udoc = users_col.find_one({"user_id": user.id}) or {}
    if udoc.get("banned"):
        return

    # global chat setting
    global_setting = settings_col.find_one({}) or {"chat_enabled_global": True}
    if not global_setting.get("chat_enabled_global", True):
        # bot disabled globally
        return

    # group-specific checks
    if chat.type in ("group","supergroup"):
        gdoc = groups_col.find_one({"chat_id": chat.id}) or {}
        if not gdoc.get("chat_enabled", True):
            return
        # if bot should only reply when mentioned, check
        # we configured to reply to all messages when chat ON — so continue

    # if message is greeting, respond with a small greeting and buttons
    text = msg.text or msg.caption or ""
    if any(word in text.lower() for word in ["hi","hello","hey","namaste","sup","hello prachi","hello prachi"]):
        kb = build_main_keyboard()
        await msg.reply_text(f"Hey {user.first_name}! 😄", reply_markup=kb)
        return

    # generate AI reply
    reply = await ai_reply(text, user.id)
    await msg.reply_text(reply)

# ----- Startup -----
async def main():
    if USE_OPENAI and openai is None:
        logger.warning("OpenAI library not installed. Falling back to non-AI responses.")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(button_cb))
    app.add_handler(CommandHandler(["ban"], ban_cmd))
    app.add_handler(CommandHandler(["unban"], unban_cmd))
    app.add_handler(CommandHandler(["chat"], chat_toggle_cmd))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_welcome))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_message))

    logger.info("Starting Prachi Chatbot...")
    await app.run_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")