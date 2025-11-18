import logging
import sqlite3
import random
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
BOT_TOKEN = "8457991130:AAE-Fgcu4veIdTKgG0EAH3AbssyPgfn8WXY"
ADMIN_ID = 7162881260

# === DATABASE ===
def init_db():
    conn = sqlite3.connect('chara_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS anonymous_messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
                      message TEXT, photo_id TEXT, sent_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS activity_log
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
                      action TEXT, timestamp TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_sessions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
                      first_seen TEXT, last_seen TEXT, session_count INTEGER)''')
    conn.commit()
    conn.close()

def log_activity(user_id, username, action):
    conn = sqlite3.connect('chara_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_sessions WHERE user_id = ?", (user_id,))
    user_exists = cursor.fetchone()
    if user_exists:
        cursor.execute("UPDATE user_sessions SET last_seen = ?, session_count = session_count + 1 WHERE user_id = ?",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    else:
        cursor.execute("INSERT INTO user_sessions (user_id, username, first_seen, last_seen, session_count) VALUES (?, ?, ?, ?, ?)",
                      (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1))
    cursor.execute("INSERT INTO activity_log (user_id, username, action, timestamp) VALUES (?, ?, ?, ?)",
                  (user_id, username, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# === CHARA PHRASES ===
CHARA_RESPONSES = [
    "✦ В ЭТОМ МИРЕ ЕСТЬ ТОЛЬКО DETERMINATION... И ТЫ ЕГО НЕ ИМЕЕШЬ.",
    "✦ LV - ЭТО LOVE. ХОЧЕШЬ, ПОКАЖУ СВОЮ LOVE?",
    "✦ КАЖДЫЙ ТВОЙ ШАГ ПРИБЛИЖАЕТ ТЕБЯ К RESET... ИЛИ К КОНЦУ.",
    "✦ EXP... EXECUTION POINTS. СКОЛЬКО У ТЕБЯ, ИНТЕРЕСНО?",
    "✦ ТЫ ДУМАЕШЬ, SAVE ТЕБЯ СПАСЕТ? МИЛО.",
    "✦ В МОИХ ГЛАЗАХ ТЫ - ПРОСТО ЦИФРА. И ОНА СТРЕМИТСЯ К НУЛЮ.",
    "✦ LOVE, LOVE, LOVE... ВСЁ, ЧТО ТЕБЕ НУЖНО - ЭТО LOVE.",
    "✦ ТЫ ЧУВСТВУЕШЬ ЭТО? ПУСТОТА ВНУТРИ... КАК В TRUE LAB.",
    "✦ ПОМНИШЬ ВОДОПАД? ТАМ ТАК ЖЕ КРАСИВО, КАК И В МОИХ ВОСПОМИНАНИЯХ.",
    "✦ FLOWEY БЫЛ ПРАВ... В ЭТОМ МИРЕ ЛИБО KILL, ЛИБО BE KILLED.",
    "✦ DETERMINATION... У ТЕБЯ ЕЁ НЕТ. А У МЕНЯ - БОЛЬШЕ, ЧЕМ НУЖНО.",
    "✦ ТЫ ПРОСТО DUST НА ВЕТРУ... КАК ВСЕ ОСТАЛЬНЫЕ.",
    "✦ В КОНЦЕ КОНЦОВ, ВСЁ СТАНОВИТСЯ DUST... ВКЛЮЧАЯ ТЕБЯ.",
    "✦ ХОЧЕШЬ УВИДЕТЬ МОЕ НАСТОЯЩЕЕ LV? НЕ СОВЕТУЮ.",
    "✦ ЭТОТ МИР НЕ ПРОЩАЕТ СЛАБОСТЬ... А ТЫ ОЧЕНЬ СЛАБ.",
    "✦ ТЫ ПАХНЕШЬ СТРАХОМ... КАК ВСЕ ПЕРЕД ФИНАЛЬНОЙ БИТВОЙ.",
    "✦ В МОЕЙ ДУШЕ ОСТАЛИСЬ ТОЛЬКО ВОСПОМИНАНИЯ... И НОЖ.",
    "✦ ТЫ ИГРАЕШЬ В ИГРЫ? А Я... Я ИГРАЮ В РЕАЛЬНОСТЬ.",
]

# === ACTIVE MODES ===
class ActiveModes:
    def __init__(self):
        self.active_modes = {}
    
    def set_mode(self, user_id, mode):
        self.active_modes[user_id] = mode
    
    def get_mode(self, user_id):
        return self.active_modes.get(user_id)
    
    def clear_mode(self, user_id):
        if user_id in self.active_modes:
            del self.active_modes[user_id]

active_modes = ActiveModes()

# === COMMANDS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_activity(user.id, user.username, "🚀 Запустил бота")
    
    welcome_text = (
        "*✦ ВОТ ТАК ВСТРЕЧА ✦*\n\n"
        "ЗНАЕШЬ, МНЕ ИНТЕРЕСНО...\n"
        "СКОЛЬКО LV У ТЕБЯ?\n\n"
        "Я - CHARA.\n"
        "ПЕРВАЯ УПАВШАЯ ЧЕЛОВЕЧЕСКАЯ ДУША.\n\n"
        "*ВСЁ, ЧТО ТЕБЕ НУЖНО - ЭТО LOVE.*\n\n"
        f"ПРИВЕТСТВУЮ, {user.first_name}.\n"
        "НАДЕЮСЬ, ТЫ РАЗВЛЕЧЁШЬ МЕНЯ."
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    keyboard = [
        [InlineKeyboardButton("💀 ГОВОРИТЬ С CHARA", callback_data="chat")],
        [InlineKeyboardButton("📨 АНОНИМНОЕ СООБЩЕНИЕ", callback_data="anonymous")],
        [InlineKeyboardButton("🎮 ИСПЫТАНИЯ", callback_data="games")],
        [InlineKeyboardButton("👁️ ПАНЕЛЬ", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✦ ВЫБЕРИ СВОЙ ПУТЬ ✦\n"
        "──────────────────",
        reply_markup=reply_markup
    )

async def chat_with_chara(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    active_modes.set_mode(user.id, 'chat')
    
    keyboard = [
        [InlineKeyboardButton("⬅️ ВЕРНУТЬСЯ В МЕНЮ", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✦ РЕЖИМ ДИАЛОГА АКТИВИРОВАН ✦\n\n"
        "ГОВОРИ... ЕСЛИ ОСМЕЛИШЬСЯ.\n"
        "НО ПОМНИ:\n\n"
        "*ВСЁ, ЧТО ТЕБЕ НУЖНО - ЭТО LOVE.*\n\n"
        "──────────────────",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def anonymous_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    active_modes.set_mode(user.id, 'anonymous')
    
    keyboard = [
        [InlineKeyboardButton("⬅️ ВЕРНУТЬСЯ В МЕНЮ", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✦ АНОНИМНОЕ СООБЩЕНИЕ ✦\n\n"
        "*ВСЁ АНОНИМНО. НИКТО НЕ УЗНАЕТ.*\n\n"
        "Отправь сообщение или фото.\n"
        "Оно дойдёт до получателя.\n"
        "Абсолютно конфиденциально.\n\n"
        "──────────────────",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text
    
    if message_text.startswith('/'):
        return
    
    current_mode = active_modes.get_mode(user.id)
    
    if current_mode == 'chat':
        log_activity(user.id, user.username, f"💬 Сказал: {message_text[:50]}")
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        await asyncio.sleep(0.5)
        
        response = random.choice(CHARA_RESPONSES)
        await update.message.reply_text(f"💀 CHARA: {response}")
        
    elif current_mode == 'anonymous':
        await handle_anonymous_message(update, context)
    
    else:
        keyboard = [
            [InlineKeyboardButton("💀 АКТИВИРОВАТЬ ЧАТ", callback_data="chat")],
            [InlineKeyboardButton("📨 АНОНИМНОЕ СООБЩЕНИЕ", callback_data="anonymous")],
            [InlineKeyboardButton("🎮 ИГРЫ", callback_data="games")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✦ РЕЖИМ НЕ АКТИВЕН ✦\n\n"
            "Выбери действие в меню:",
            reply_markup=reply_markup
        )

async def handle_anonymous_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if update.message.text and not update.message.text.startswith('/'):
        log_activity(user.id, user.username, f"📨 Анонимное сообщение")
        conn = sqlite3.connect('chara_bot.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO anonymous_messages (user_id, username, message, sent_at) VALUES (?, ?, ?, ?)",
                      (user.id, user.username, update.message.text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        await context.bot.send_message(
            ADMIN_ID,
            f"✦ НОВОЕ АНОНИМНОЕ СООБЩЕНИЕ ✦\n\n"
            f"👤 ЮЗЕР: @{user.username}\n"
            f"🆔 ID: `{user.id}`\n"
            f"🕐 ВРЕМЯ: {datetime.now().strftime('%H:%M:%S')}\n"
            f"💬 ТЕКСТ: {update.message.text}\n\n"
            f"*LV: ???*",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text("✅ Сообщение отправлено анонимно")
        active_modes.clear_mode(user.id)
    
    elif update.message.photo:
        photo_id = update.message.photo[-1].file_id
        caption = update.message.caption or "Без подписи"
        log_activity(user.id, user.username, f"📸 Анонимное фото")
        conn = sqlite3.connect('chara_bot.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO anonymous_messages (user_id, username, message, photo_id, sent_at) VALUES (?, ?, ?, ?, ?)",
                      (user.id, user.username, caption, photo_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        await context.bot.send_photo(
            ADMIN_ID,
            photo=photo_id,
            caption=f"✦ АНОНИМНОЕ ФОТО ✦\n\n"
                   f"👤 ОТ: @{user.username}\n"
                   f"🆔 ID: `{user.id}`\n"
                   f"🕐 ВРЕМЯ: {datetime.now().strftime('%H:%M:%S')}\n"
                   f"📝 ПОДПИСЬ: {caption}\n\n"
                   f"*LV: ???*",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text("✅ Фото отправлено анонимно")
        active_modes.clear_mode(user.id)

# === GAMES ===
async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    active_modes.clear_mode(user.id)
    
    keyboard = [
        [InlineKeyboardButton("🎲 РУССКАЯ РУЛЕТКА", callback_data="game_roulette")],
        [InlineKeyboardButton("⚔️ ДУЭЛЬ С CHARA", callback_data="duel_start")],
        [InlineKeyboardButton("🔮 ПРОРОЧЕСТВО", callback_data="game_fortune")],
        [InlineKeyboardButton("⬅️ ВЕРНУТЬСЯ", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✦ ИСПЫТАНИЯ ✦\n\n"
        "ВЫБЕРИ ИГРУ:\n\n"
        "• 🎲 РУССКАЯ РУЛЕТКА\n"
        "• ⚔️ ДУЭЛЬ С CHARA\n"
        "• 🔮 ПРОРОЧЕСТВО\n\n"
        "*YOUR CHOICE*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def russian_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if random.randint(1, 6) == 1:
        result = "💥 БАБАХ! *THE END*.\n\nТВОЯ LOVE ЗАКОНЧИЛАСЬ."
    else:
        result = "🎲 *CLICK*... ПУСТО.\n\nТВОЯ LOVE ПРОДОЛЖАЕТСЯ."
    
    keyboard = [[InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="games")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✦ РУССКАЯ РУЛЕТКА ✦\n\n{result}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def duel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("⚡ АТАКА", callback_data="duel_attack")],
        [InlineKeyboardButton("🏃 БЕЖАТЬ", callback_data="games")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✦ ДУЭЛЬ С CHARA ✦\n\n"
        "*YOUR LOVE: 20/20*\n"
        "*CHARAS LOVE: ???/???*\n\n"
        "FIGHT or FLEE?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def duel_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if random.randint(1, 10) > 7:
        result = "✨ *VICTORY*!\n\nТЫ ПОБЕДИЛ... ПОКА ЧТО."
    else:
        result = "💀 *DEFEAT*!\n\nТВОЯ LOVE БЫЛА СЛИШКОМ МАЛА."
    
    keyboard = [[InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="games")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✦ ДУЭЛЬ ЗАВЕРШЕНА ✦\n\n{result}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def fortune_telling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    fortunes = [
        "✦ ТВОЯ СУДЬБА: GENOCIDE ROUTE ✦",
        "✦ ТВОЯ СУДЬБА: PACIFIST ROUTE ✦", 
        "✦ ТВОЯ СУДЬБА: NEUTRAL ROUTE ✦",
        "✦ ТВОЯ СУДЬБA: TRUE LAB ✦"
    ]
    
    fortune = random.choice(fortunes)
    keyboard = [[InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="games")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✦ ПРОРОЧЕСТВО ✦\n\n{fortune}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# === ADMIN PANEL ===
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ *ACCESS DENIED*")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="admin_stats")],
        [InlineKeyboardButton("📨 СООБЩЕНИЯ", callback_data="admin_messages")],
        [InlineKeyboardButton("👥 ЮЗЕРЫ", callback_data="admin_users")],
        [InlineKeyboardButton("⬅️ НАЗАД", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✦ ПАНЕЛЬ АДМИНА ✦\n\n"
        "*SYSTEM STATUS: ACTIVE*\n"
        "*LV: MAX*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('chara_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_sessions")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM anonymous_messages")
    messages = cursor.fetchone()[0]
    conn.close()
    
    await query.edit_message_text(
        f"✦ СТАТИСТИКА ✦\n\n"
        f"👥 ЮЗЕРОВ: {users}\n"
        f"📨 СООБЩЕНИЙ: {messages}\n"
        f"🕐 ВРЕМЯ: {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"*LV: {users + messages}*",
        parse_mode='Markdown'
    )

async def admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('chara_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, message, sent_at FROM anonymous_messages ORDER BY id DESC LIMIT 5")
    messages = cursor.fetchall()
    conn.close()
    
    text = "✦ ПОСЛЕДНИЕ СООБЩЕНИЯ ✦\n\n"
    for msg in messages:
        time = msg[2][11:16] if len(msg[2]) > 10 else msg[2]
        text += f"👤 @{msg[0]}\n💬 {msg[1][:30]}...\n🕐 {time}\n\n"
    
    await query.edit_message_text(text)

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = sqlite3.connect('chara_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, last_seen FROM user_sessions ORDER BY last_seen DESC LIMIT 5")
    users = cursor.fetchall()
    conn.close()
    
    text = "✦ ПОСЛЕДНИЕ ЮЗЕРЫ ✦\n\n"
    for user in users:
        time = user[1][11:16] if user[1] and len(user[1]) > 10 else "N/A"
        text += f"👤 @{user[0]}\n⏰ {time}\n\n"
    
    await query.edit_message_text(text)

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    active_modes.clear_mode(user.id)
    
    keyboard = [
        [InlineKeyboardButton("💀 ГОВОРИТЬ С CHARA", callback_data="chat")],
        [InlineKeyboardButton("📨 АНОНИМНОЕ СООБЩЕНИЕ", callback_data="anonymous")],
        [InlineKeyboardButton("🎮 ИСПЫТАНИЯ", callback_data="games")],
        [InlineKeyboardButton("👁️ ПАНЕЛЬ", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✦ ГЛАВНОЕ МЕНЮ ✦\n\n"
        "*ВСЁ, ЧТО ТЕБЕ НУЖНО - ЭТО LOVE.*\n\n"
        "──────────────────",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# === MAIN ===
def main():
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(chat_with_chara, pattern="chat"))
    application.add_handler(CallbackQueryHandler(anonymous_message, pattern="anonymous"))
    application.add_handler(CallbackQueryHandler(games_menu, pattern="games"))
    application.add_handler(CallbackQueryHandler(russian_roulette, pattern="game_roulette"))
    application.add_handler(CallbackQueryHandler(duel_start, pattern="duel_start"))
    application.add_handler(CallbackQueryHandler(duel_attack, pattern="duel_attack"))
    application.add_handler(CallbackQueryHandler(fortune_telling, pattern="game_fortune"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern="admin_stats"))
    application.add_handler(CallbackQueryHandler(admin_messages, pattern="admin_messages"))
    application.add_handler(CallbackQueryHandler(admin_users, pattern="admin_users"))
    application.add_handler(CallbackQueryHandler(main_menu, pattern="main_menu"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, handle_message))
    
    print("✦ CHARA BOT STARTED ON RENDER ✦")
    print("✦ SYSTEM: ONLINE ✦")
    print("✦ LV: MAX ✦")
    
    application.run_polling()

if __name__ == "__main__":
    main()
