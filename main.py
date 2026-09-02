import asyncio
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Yangi ma'lumotlar to'g'ridan-to'g mezonlashtirildi
ADMIN_ID = 8642809489
TOKEN = "8887391193:AAHI4esMFTuaHo4mHFtRG1T2ThhtCE2Emc4"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def init_db():
    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            total_score INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER,
            question_text TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_option TEXT
        )
    """)
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, full_name) VALUES (?, ?)", (user.id, user.full_name))
    conn.commit()
    conn.close()

    keyboard = [[InlineKeyboardButton("📝 Test yechish", callback_data="start_quiz")]]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("➕ Yangi test yaratish (Admin)", callback_data="create_quiz")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}!\nQuiz botga xush kelibsiz.",
        reply_markup=reply_markup
    )

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("Bot muvaffaqiyatli ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
