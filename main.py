import sqlite3
import asyncio
import os
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

ADMIN_ID = int(os.environ.get("ADMIN_ID", "8642809489"))
TOKEN = os.environ.get("TOKEN", "")

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_tests (
            user_id INTEGER,
            test_id INTEGER,
            score INTEGER,
            PRIMARY KEY (user_id, test_id)
        )
    """)
    conn.commit()
    conn.close()

def get_active_test():
    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM tests WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    active_test = cursor.fetchone()
    conn.close()
    return active_test

ADD_TITLE, ADD_QUESTION, ADD_A, ADD_B, ADD_C, ADD_D, ADD_CORRECT = range(7)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, full_name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET full_name=excluded.full_name",
        (user.id, user.full_name)
    )
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("📝 Testni boshlash", callback_data="start_quiz")],
        [InlineKeyboardButton("📊 Reyting", callback_data="show_leaderboard")]
    ]
    
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("➕ Yangi test yaratish (Admin)", callback_data="create_quiz")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Xush kelibsiz, {user.first_name}!\nQuyidagi tugmalardan birini tanlang:",
        reply_markup=reply_markup
    )

async def admin_start_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ Bu bo'lim faqat admin uchun!")
        return ConversationHandler.END

    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tests SET is_active = 0")
    conn.commit()
    conn.close()

    await query.message.reply_text("Yangi test nomini kiriting (Masalan: 1-Hafta testi):")
    return ADD_TITLE

async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tests (title, is_active) VALUES (?, 1)", (title,))
    test_id = cursor.lastrowid
    conn.commit()
    conn.close()

    context.user_data['current_test_id'] = test_id
    context.user_data['questions_count'] = 0
    
    await update.message.reply_text("Test yaratildi!\n\n1-savol matnini kiriting (Tugatish uchun /done bosing):")
    return ADD_QUESTION

async def add_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "/done":
        count = context.user_data.get('questions_count', 0)
        await update.message.reply_text(f"✅ Test muvaffaqiyatli saqlandi! Jami {count} ta savol qo'shildi.")
        return ConversationHandler.END

    context.user_data['temp_q'] = {'text': text}
    await update.message.reply_text("A variantini kiriting:")
    return ADD_A

async def add_a(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_q']['a'] = update.message.text
    await update.message.reply_text("B variantini kiriting:")
    return ADD_B

async def add_b(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_q']['b'] = update.message.text
    await update.message.reply_text("C variantini kiriting:")
    return ADD_C

async def add_c(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_q']['c'] = update.message.text
    await update.message.reply_text("D variantini kiriting:")
    return ADD_D

async def add_d(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_q']['d'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("A", callback_data="A"), InlineKeyboardButton("B", callback_data="B")],
        [InlineKeyboardButton("C", callback_data="C"), InlineKeyboardButton("D", callback_data="D")]
    ]
    await update.message.reply_text("To'g'ri variantni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_CORRECT

async def add_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    correct = query.data
    q_data = context.user_data['temp_q']
    test_id = context.user_data['current_test_id']

    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO questions (test_id, question_text, option_a, option_b, option_c, option_d, correct_option)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (test_id, q_data['text'], q_data['a'], q_data['b'], q_data['c'], q_data['d'], correct))
    conn.commit()
    conn.close()

    context.user_data['questions_count'] += 1
    next_num = context.user_data['questions_count'] + 1
    
    await query.edit_message_text(f"✅ Savol saqlandi!\n\n{next_num}-savol matnini kiriting (Tugatish uchun /done bosing):")
    return ADD_QUESTION

async def start_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    active_test = get_active_test()
    if not active_test:
        await query.message.reply_text("❌ Hozircha faol test mavjud emas.")
        return

    test_id, title = active_test

    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT score FROM user_tests WHERE user_id = ? AND test_id = ?", (user_id, test_id))
    already_taken = cursor.fetchone()

    if already_taken:
        await query.message.reply_text(f"🚫 Siz bu testni ({title}) allaqachon topshirgansiz!")
        conn.close()
        return

    cursor.execute("SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option FROM questions WHERE test_id = ?", (test_id,))
    questions = cursor.fetchall()
    conn.close()

    if not questions:
        await query.message.reply_text("❌ Ushbu testda savollar topilmadi.")
        return

    context.user_data['quiz'] = {
        'test_id': test_id,
        'questions': questions,
        'current_index': 0,
        'score': 0,
        'timer_task': None
    }
    
    await send_next_question(query.message, context, user_id)

async def send_next_question(message, context, user_id):
    quiz = context.user_data.get('quiz')
    if not quiz:
        return

    index = quiz['current_index']
    
    if index >= len(quiz['questions']):
        await finish_quiz(message, context, user_id)
        return

    q = quiz['questions'][index]
    q_id, text, a, b, c, d, correct = q

    keyboard = [
        [InlineKeyboardButton(f"A) {a}", callback_data=f"ans_A_{index}")],
        [InlineKeyboardButton(f"B) {b}", callback_data=f"ans_B_{index}")],
        [InlineKeyboardButton(f"C) {c}", callback_data=f"ans_C_{index}")],
        [InlineKeyboardButton(f"D) {d}", callback_data=f"ans_D_{index}")]
    ]
    
    sent_msg = await message.reply_text(
        f"❓ **{index + 1}-savol:**\n{text}\n\n⏱️ **Vaqt: 30 soniya!**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    async def timer():
        await asyncio.sleep(30)
        try:
            await sent_msg.edit_text("⏱️ **Vaqt tugadi!** Savol o'tkazib yuborildi.", parse_mode="Markdown")
        except Exception:
            pass
        quiz['current_index'] += 1
        await send_next_question(sent_msg, context, user_id)

    if quiz.get('timer_task'):
        quiz['timer_task'].cancel()
    quiz['timer_task'] = asyncio.create_task(timer())

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    quiz = context.user_data.get('quiz')
    if not quiz:
        return

    if quiz.get('timer_task'):
        quiz['timer_task'].cancel()

    data = query.data.split('_')
    selected_ans = data[1]
    q_index = int(data[2])

    if q_index != quiz['current_index']:
        return

    correct_ans = quiz['questions'][q_index][6]
    if selected_ans == correct_ans:
        quiz['score'] += 1

    quiz['current_index'] += 1
    
    try:
        await query.message.delete()
    except Exception:
        pass
        
    await send_next_question(query.message, context, query.from_user.id)

async def finish_quiz(message, context, user_id):
    quiz = context.user_data['quiz']
    if quiz.get('timer_task'):
        quiz['timer_task'].cancel()

    test_id = quiz['test_id']
    score = quiz['score']
    total_q = len(quiz['questions'])

    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("INSERT OR REPLACE INTO user_tests (user_id, test_id, score) VALUES (?, ?, ?)", (user_id, test_id, score))
    cursor.execute("UPDATE users SET total_score = total_score + ? WHERE user_id = ?", (score, user_id))
    cursor.execute("SELECT total_score FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    total_score = res[0] if res else score
    
    conn.commit()
    conn.close()

    await message.reply_text(
        f"🎉 **Test yakunlandi!**\n\n"
        f"📊 Ushbu test natijasi: **{score}/{total_q}** ball\n"
        f"🏆 Umumiy ballingiz: **{total_score}** ball",
        parse_mode="Markdown"
    )
    context.user_data['quiz'] = None

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    conn = sqlite3.connect("quiz_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, total_score FROM users ORDER BY total_score DESC LIMIT 10")
    top_users = cursor.fetchall()
    conn.close()

    if not top_users:
        await query.message.reply_text("Hozircha reyting mavjud emas.")
        return

    text = "🏆 **Umumiy Reyting (Top 10):**\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for idx, (name, score) in enumerate(top_users, start=1):
        icon = medals[idx-1] if idx <= 3 else f"{idx}."
        text += f"{icon} **{name}** — {score} ball\n"

    await query.message.reply_text(text, parse_mode="Markdown")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_start_create, pattern="^create_quiz$")],
        states={
            ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            ADD_QUESTION: [MessageHandler(filters.TEXT, add_question)],
            ADD_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_a)],
            ADD_B: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_b)],
            ADD_C: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_c)],
            ADD_D: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_d)],
            ADD_CORRECT: [CallbackQueryHandler(add_correct, pattern="^(A|B|C|D)$")],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(start_quiz_callback, pattern="^start_quiz$"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern="^ans_"))
    app.add_handler(CallbackQueryHandler(show_leaderboard, pattern="^show_leaderboard$"))

    app.run_polling()

if __name__ == "__main__":
    main()
