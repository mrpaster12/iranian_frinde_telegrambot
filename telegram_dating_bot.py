import sqlite3
import os
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
from telegram.error import TelegramError
from datetime import datetime

# --- Configuration ---
TOKEN = os.getenv('7944848798:AAFYtAuBn1MmbKZIs2xkL36h3bIMosIf6y0',
                  '7944848798:AAFYtAuBn1MmbKZIs2xkL36h3bIMosIf6y0')
ADMIN_PASSWORD = os.getenv('Iliath_1389', 'Iliath_1389')
CHANNEL_ID = '@newdostchanel'

# --- Language Support ---
LANGUAGES = {
    'fa': {
        'welcome': "👋 خوش اومدی! برای استفاده از ربات، ابتدا باید در کانال ما عضو بشی:\n👉 t.me/newdostchanel\nبعد از عضویت، دوباره /start کن!",
        'menu': "👋 یکی از گزینه‌ها رو انتخاب کن:",
        'select_gender': "👤 جنسیتت رو انتخاب کن:",
        'enter_age': "📅 سنت چنده؟ (عدد بفرست)",
        'invalid_age': "❗ لطفاً عدد معتبر وارد کن.",
        'enter_city': "🏙️ اهل کجا هستی؟",
        'enter_bio': "📝 یک بیو کوتاه درباره خودت بنویس:",
        'registration_complete': "✅ ثبت‌نامت کامل شد! برای جستجو دکمه 🔎 رو بزن یا /start کن.",
        'select_search_gender': "🔍 دنبال چه جنسیتی هستی؟",
        'select_search_age': "🎯 چه بازه سنی میخوای؟",
        'partner_found': "✅ دوست پیدا شد! می‌تونی چت کنی.",
        'no_partner': "❌ کسی پیدا نشد. به صف انتظار اضافه شدی!",
        'chat_ended': "✅ چت تموم شد.",
        'no_active_chat': "❗ شما چتی نداری.",
        'blocked': "✅ کاربر بلاک شد و چت قطع شد.",
        'no_block_target': "❗ کسی برای بلاک وجود نداره.",
        'admin_password': "🔐 رمز ادمین رو وارد کن:",
        'wrong_password': "❌ رمز اشتباهه.",
        'edit_profile': "✏️ کدوم بخش رو می‌خوای ویرایش کنی؟",
        'anonymous_chat': "💬 چت ناشناس شروع شد! فقط پیام متنی می‌تونی بفرستی.",
        'not_in_channel': "❌ برای استفاده از ربات، ابتدا باید در کانال ما عضو بشی:\n👉 t.me/newdostchanel"
    },
    'en': {
        'welcome': "👋 Welcome! To use the bot, you must first join our channel:\n👉 t.me/newdostchanel\nAfter joining, run /start again!",
        'menu': "👋 Choose an option:",
        'select_gender': "👤 Select your gender:",
        'enter_age': "📅 How old are you? (Send a number)",
        'invalid_age': "❗ Please enter a valid number.",
        'enter_city': "🏙️ Where are you from?",
        'enter_bio': "📝 Write a short bio about yourself:",
        'registration_complete': "✅ Registration complete! Press 🔎 to search or /start.",
        'select_search_gender': "🔍 Looking for which gender?",
        'select_search_age': "🎯 What age range?",
        'partner_found': "✅ Friend found! You can start chatting.",
        'no_partner': "❌ No one found. You've been added to the queue!",
        'chat_ended': "✅ Chat ended.",
        'no_active_chat': "❗ You don't have an active chat.",
        'blocked': "✅ User blocked and chat ended.",
        'no_block_target': "❗ No one to block.",
        'admin_password': "🔐 Enter admin password:",
        'wrong_password': "❌ Wrong password.",
        'edit_profile': "✏️ Which section do you want to edit?",
        'anonymous_chat': "💬 Anonymous chat started! You can only send text messages.",
        'not_in_channel': "❌ To use the bot, you must first join our channel:\n👉 t.me/newdostchanel"
    }
}

# --- Database ---


def init_db():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                gender TEXT,
                age INTEGER,
                city TEXT,
                bio TEXT,
                language TEXT DEFAULT 'fa'
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                user1_id INTEGER,
                user2_id INTEGER,
                anonymous INTEGER DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                sender_id INTEGER,
                receiver_id INTEGER,
                content TEXT,
                type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS blocked_users (
                blocker_id INTEGER,
                blocked_id INTEGER
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS queue (
                user_id INTEGER PRIMARY KEY,
                gender_filter TEXT,
                age_filter TEXT
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON users(id);')
        c.execute(
            'CREATE INDEX IF NOT EXISTS idx_chats ON chats(user1_id, user2_id);')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()


# --- Registration states ---
GENDER, AGE, CITY, BIO, EDIT_PROFILE, ADMIN_PASSWORD, LANGUAGE = range(7)


async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except TelegramError:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        try:
            await update.message.reply_text(LANGUAGES[lang]['welcome'])
        except TelegramError:
            await update.message.reply_text("❌ خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        return

    keyboard = [
        [InlineKeyboardButton(
            "🚹 ثبت نام" if lang == 'fa' else "🚹 Register", callback_data='register')],
        [InlineKeyboardButton("🔎 جستجوی دوست" if lang ==
                              'fa' else "🔎 Search Friend", callback_data='search')],
        [InlineKeyboardButton("✏️ ویرایش پروفایل" if lang ==
                              'fa' else "✏️ Edit Profile", callback_data='edit')],
        [InlineKeyboardButton("🚫 پایان چت" if lang ==
                              'fa' else "🚫 End Chat", callback_data='end')],
        [InlineKeyboardButton("⛔ بلاک" if lang ==
                              'fa' else "⛔ Block", callback_data='block')],
        [InlineKeyboardButton(
            "🌐 زبان" if lang == 'fa' else "🌐 Language", callback_data='language')]
    ]
    try:
        await update.message.reply_text(LANGUAGES[lang]['menu'], reply_markup=InlineKeyboardMarkup(keyboard))
    except TelegramError:
        await update.message.reply_text("❌ خطایی رخ داد. لطفاً دوباره امتحان کنید.")


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        return

    if query.data == 'register':
        keyboard = [
            [InlineKeyboardButton("🚹 پسر" if lang == 'fa' else "🚹 Male", callback_data='male'),
             InlineKeyboardButton("🚺 دختر" if lang == 'fa' else "🚺 Female", callback_data='female')]
        ]
        await query.edit_message_text(LANGUAGES[lang]['select_gender'], reply_markup=InlineKeyboardMarkup(keyboard))
        return GENDER
    elif query.data == 'search':
        await search(update, context)
    elif query.data == 'edit':
        await edit_profile(update, context)
        return EDIT_PROFILE
    elif query.data == 'end':
        await end_chat(update, context)
    elif query.data == 'block':
        await block(update, context)
    elif query.data == 'language':
        keyboard = [
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data='lang_fa'),
             InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')]
        ]
        await query.edit_message_text("🌐 Select your language:" if lang == 'en' else "🌐 زبان خود را انتخاب کنید:",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return LANGUAGE


async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    lang = query.data.replace('lang_', '')

    if not await check_channel_membership(context, user.id):
        await query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        return

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET language = ? WHERE id = ?", (lang, user.id))
        conn.commit()
    except sqlite3.Error:
        await query.edit_message_text("❌ Error updating language.")
    finally:
        conn.close()

    await query.edit_message_text(LANGUAGES[lang]['menu'])
    await start(update, context)
    return ConversationHandler.END


async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        return

    context.user_data['gender'] = query.data
    await query.edit_message_text(LANGUAGES[lang]['enter_age'])
    return AGE


async def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    if not update.message.text.isdigit() or int(update.message.text) < 13:
        await update.message.reply_text(LANGUAGES[lang]['invalid_age'])
        return AGE
    context.user_data['age'] = int(update.message.text)
    await update.message.reply_text(LANGUAGES[lang]['enter_city'])
    return CITY


async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    context.user_data['city'] = update.message.text
    await update.message.reply_text(LANGUAGES[lang]['enter_bio'])
    return BIO


async def bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    context.user_data['bio'] = update.message.text

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (id, gender, age, city, bio, language) VALUES (?, ?, ?, ?, ?, ?)",
                  (user.id, context.user_data['gender'], context.user_data['age'],
                   context.user_data['city'], context.user_data['bio'], lang))
        conn.commit()

        c.execute(
            "SELECT gender_filter, age_filter FROM queue WHERE user_id = ?", (user.id,))
        queue_data = c.fetchone()
        if queue_data:
            await try_match_from_queue(user.id, queue_data[0], queue_data[1], context)
    except sqlite3.Error:
        await update.message.reply_text("❌ خطایی در ثبت‌نام رخ داد.")
        return ConversationHandler.END
    finally:
        conn.close()

    await update.message.reply_text(LANGUAGES[lang]['registration_complete'])
    return ConversationHandler.END

# --- Profile Editing ---


async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        if update.callback_query:
            await update.callback_query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        else:
            await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    keyboard = [
        [InlineKeyboardButton(
            "👤 جنسیت" if lang == 'fa' else "👤 Gender", callback_data='edit_gender')],
        [InlineKeyboardButton(
            "📅 سن" if lang == 'fa' else "📅 Age", callback_data='edit_age')],
        [InlineKeyboardButton("🏙️ شهر" if lang ==
                              'fa' else "🏙️ City", callback_data='edit_city')],
        [InlineKeyboardButton(
            "📝 بیو" if lang == 'fa' else "📝 Bio", callback_data='edit_bio')]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(LANGUAGES[lang]['edit_profile'], reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(LANGUAGES[lang]['edit_profile'], reply_markup=InlineKeyboardMarkup(keyboard))


async def edit_profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        return

    if query.data == 'edit_gender':
        keyboard = [
            [InlineKeyboardButton("🚹 پسر" if lang == 'fa' else "🚹 Male", callback_data='male'),
             InlineKeyboardButton("🚺 دختر" if lang == 'fa' else "🚺 Female", callback_data='female')]
        ]
        await query.edit_message_text(LANGUAGES[lang]['select_gender'], reply_markup=InlineKeyboardMarkup(keyboard))
        return GENDER
    elif query.data == 'edit_age':
        await query.edit_message_text(LANGUAGES[lang]['enter_age'])
        return AGE
    elif query.data == 'edit_city':
        await query.edit_message_text(LANGUAGES[lang]['enter_city'])
        return CITY
    elif query.data == 'edit_bio':
        await query.edit_message_text(LANGUAGES[lang]['enter_bio'])
        return BIO

# --- Search and Filters ---


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        if update.callback_query:
            await update.callback_query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        else:
            await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    keyboard = [
        [InlineKeyboardButton("🚹 پسر" if lang == 'fa' else "🚹 Male", callback_data='search_male'),
         InlineKeyboardButton("🚺 دختر" if lang == 'fa' else "🚺 Female", callback_data='search_female')],
        [InlineKeyboardButton("👥 فرقی نداره" if lang ==
                              'fa' else "👥 Any", callback_data='search_any')],
        [InlineKeyboardButton(
            "💬 چت ناشناس" if lang == 'fa' else "💬 Anonymous", callback_data='search_anonymous')]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(LANGUAGES[lang]['select_search_gender'], reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(LANGUAGES[lang]['select_search_gender'], reply_markup=InlineKeyboardMarkup(keyboard))


async def filter_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        return

    gender = query.data.replace('search_', '')
    context.user_data['search_gender'] = gender

    if gender == 'anonymous':
        await start_anonymous_chat(update, context)
        return
    keyboard = [
        [InlineKeyboardButton("13-20", callback_data='13-20'),
         InlineKeyboardButton("21-30", callback_data='21-30')],
        [InlineKeyboardButton("31-40", callback_data='31-40'),
         InlineKeyboardButton("🆗 فرقی نداره" if lang == 'fa' else "🆗 Any", callback_data='any')]
    ]
    await query.edit_message_text(LANGUAGES[lang]['select_search_age'], reply_markup=InlineKeyboardMarkup(keyboard))


async def filter_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        return

    age_range = query.data
    context.user_data['search_age'] = age_range

    if context.user_data.get('chat_partner'):
        await query.edit_message_text("❗ شما در حال حاضر در چت هستید. ابتدا چت را پایان دهید.")
        return

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        gender_filter = context.user_data.get('search_gender')
        age_filter = context.user_data.get('search_age')

        c.execute(
            "SELECT blocked_id FROM blocked_users WHERE blocker_id = ?", (user.id,))
        blocked_ids = [row[0] for row in c.fetchall()]

        sql = "SELECT id, gender, age, city, bio FROM users WHERE id != ? AND id NOT IN ({})".format(
            ','.join('?' * len(blocked_ids)))
        params = [user.id] + blocked_ids

        if gender_filter != 'any':
            sql += " AND gender = ?"
            params.append(gender_filter)
        if age_filter != 'any':
            min_age, max_age = map(int, age_filter.split('-'))
            sql += " AND age BETWEEN ? AND ?"
            params.extend([min_age, max_age])

        c.execute(sql, params)
        results = c.fetchall()

        if results:
            result = random.choice(results)
            partner_id = result[0]
            context.user_data['chat_partner'] = partner_id
            c.execute(
                "INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)", (user.id, partner_id))
            conn.commit()
            await context.bot.send_message(chat_id=partner_id, text=LANGUAGES[lang]['partner_found'])
            await query.edit_message_text(LANGUAGES[lang]['partner_found'])
        else:
            c.execute("INSERT OR REPLACE INTO queue (user_id, gender_filter, age_filter) VALUES (?, ?, ?)",
                      (user.id, gender_filter, age_filter))
            conn.commit()
            await query.edit_message_text(LANGUAGES[lang]['no_partner'])
    except (sqlite3.Error, TelegramError):
        await query.edit_message_text("❌ خطایی رخ داد. لطفاً دوباره امتحان کنید.")
    finally:
        conn.close()


async def try_match_from_queue(user_id, gender_filter, age_filter, context):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        sql = "SELECT id FROM users WHERE id != ?"
        params = [user_id]
        if gender_filter != 'any':
            sql += " AND gender = ?"
            params.append(gender_filter)
        if age_filter != 'any':
            min_age, max_age = map(int, age_filter.split('-'))
            sql += " AND age BETWEEN ? AND ?"
            params.extend([min_age, max_age])

        c.execute(sql, params)
        results = c.fetchall()

        if results:
            partner_id = random.choice(results)[0]
            c.execute("DELETE FROM queue WHERE user_id = ?", (user_id,))
            c.execute(
                "INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)", (user_id, partner_id))
            conn.commit()
            await context.bot.send_message(chat_id=user_id, text=LANGUAGES[get_user_language(user_id)]['partner_found'])
            await context.bot.send_message(chat_id=partner_id, text=LANGUAGES[get_user_language(partner_id)]['partner_found'])
    except (sqlite3.Error, TelegramError):
        pass
    finally:
        conn.close()

# --- Chat ---


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    partner_id = context.user_data.get('chat_partner')

    if not partner_id:
        await update.message.reply_text(LANGUAGES[lang]['no_active_chat'])
        return

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        c.execute("SELECT anonymous FROM chats WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)",
                  (user.id, partner_id, partner_id, user.id))
        is_anonymous = c.fetchone()[0]

        if is_anonymous and (update.message.photo or update.message.video or update.message.voice):
            await update.message.reply_text(LANGUAGES[lang]['anonymous_chat'])
            return

        if update.message.text:
            await context.bot.send_message(chat_id=partner_id, text=update.message.text)
            c.execute("INSERT INTO messages (sender_id, receiver_id, content, type) VALUES (?, ?, ?, ?)",
                      (user.id, partner_id, update.message.text, 'text'))
        elif update.message.photo:
            for photo in update.message.photo:
                await context.bot.send_photo(chat_id=partner_id, photo=photo.file_id)
                c.execute("INSERT INTO messages (sender_id, receiver_id, content, type) VALUES (?, ?, ?, ?)",
                          (user.id, partner_id, photo.file_id, 'photo'))
        elif update.message.video:
            await context.bot.send_video(chat_id=partner_id, video=update.message.video.file_id)
            c.execute("INSERT INTO messages (sender_id, receiver_id, content, type) VALUES (?, ?, ?, ?)",
                      (user.id, partner_id, update.message.video.file_id, 'video'))
        elif update.message.voice:
            await context.bot.send_voice(chat_id=partner_id, voice=update.message.voice.file_id)
            c.execute("INSERT INTO messages (sender_id, receiver_id, content, type) VALUES (?, ?, ?, ?)",
                      (user.id, partner_id, update.message.voice.file_id, 'voice'))

        conn.commit()
    except (sqlite3.Error, TelegramError):
        await update.message.reply_text("❌ خطایی در ارسال پیام رخ داد.")
    finally:
        conn.close()


async def start_anonymous_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await update.callback_query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        return

    if context.user_data.get('chat_partner'):
        await update.callback_query.edit_message_text("❗ شما در حال حاضر در چت هستید. ابتدا چت را پایان دهید.")
        return

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE id != ?", (user.id,))
        results = c.fetchall()

        if results:
            partner_id = random.choice(results)[0]
            context.user_data['chat_partner'] = partner_id
            c.execute(
                "INSERT INTO chats (user1_id, user2_id, anonymous) VALUES (?, ?, 1)", (user.id, partner_id))
            conn.commit()
            await context.bot.send_message(chat_id=partner_id, text=LANGUAGES[get_user_language(partner_id)]['anonymous_chat'])
            await update.callback_query.edit_message_text(LANGUAGES[lang]['anonymous_chat'])
        else:
            c.execute("INSERT OR REPLACE INTO queue (user_id, gender_filter, age_filter) VALUES (?, ?, ?)",
                      (user.id, 'any', 'any'))
            conn.commit()
            await update.callback_query.edit_message_text(LANGUAGES[lang]['no_partner'])
    except (sqlite3.Error, TelegramError):
        await update.callback_query.edit_message_text("❌ خطایی رخ داد.")
    finally:
        conn.close()

# --- End Chat ---


async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        if update.callback_query:
            await update.callback_query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        else:
            await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    partner_id = context.user_data.get('chat_partner')

    if not partner_id:
        if update.callback_query:
            await update.callback_query.edit_message_text(LANGUAGES[lang]['no_active_chat'])
        else:
            await update.message.reply_text(LANGUAGES[lang]['no_active_chat'])
        return

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute(
            "DELETE FROM chats WHERE user1_id = ? OR user2_id = ?", (user.id, user.id))
        conn.commit()
        await context.bot.send_message(chat_id=partner_id, text=LANGUAGES[get_user_language(partner_id)]['chat_ended'])
        context.user_data['chat_partner'] = None
        if update.callback_query:
            await update.callback_query.edit_message_text(LANGUAGES[lang]['chat_ended'])
        else:
            await update.message.reply_text(LANGUAGES[lang]['chat_ended'])
    except (sqlite3.Error, TelegramError):
        await update.message.reply_text("❌ خطایی رخ داد.")
    finally:
        conn.close()

# --- Block ---


async def block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        if update.callback_query:
            await update.callback_query.edit_message_text(LANGUAGES[lang]['not_in_channel'])
        else:
            await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    partner_id = context.user_data.get('chat_partner')

    if not partner_id:
        if update.callback_query:
            await update.callback_query.edit_message_text(LANGUAGES[lang]['no_block_target'])
        else:
            await update.message.reply_text(LANGUAGES[lang]['no_block_target'])
        return

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute(
            "INSERT INTO blocked_users (blocker_id, blocked_id) VALUES (?, ?)", (user.id, partner_id))
        c.execute(
            "DELETE FROM chats WHERE user1_id = ? OR user2_id = ?", (user.id, user.id))
        conn.commit()
        await context.bot.send_message(chat_id=partner_id, text=LANGUAGES[get_user_language(partner_id)]['blocked'])
        context.user_data['chat_partner'] = None
        if update.callback_query:
            await update.callback_query.edit_message_text(LANGUAGES[lang]['blocked'])
        else:
            await update.message.reply_text(LANGUAGES[lang]['blocked'])
    except (sqlite3.Error, TelegramError):
        await update.message.reply_text("❌ خطایی رخ داد.")
    finally:
        conn.close()

# --- Admin ---


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    await update.message.reply_text(LANGUAGES[lang]['admin_password'])
    return ADMIN_PASSWORD


async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_language(user.id)

    if not await check_channel_membership(context, user.id):
        await update.message.reply_text(LANGUAGES[lang]['not_in_channel'])
        return

    password = update.message.text

    if password != ADMIN_PASSWORD:
        await update.message.reply_text(LANGUAGES[lang]['wrong_password'])
        return ConversationHandler.END

    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        c.execute(
            "SELECT sender_id, receiver_id, content, type, timestamp FROM messages ORDER BY timestamp DESC LIMIT 50")
        messages = c.fetchall()

        text = f"👥 تعداد کاربران: {user_count}\n\n📝 آخرین پیام‌ها:\n" if lang == 'fa' else f"👥 Total users: {user_count}\n\n📝 Recent messages:\n"
        for msg in messages:
            text += f"\nاز {msg[0]} به {msg[1]} ({msg[3]}, {msg[4]}): {msg[2][:50]}..."

        await update.message.reply_text(text[:4096])
    except (sqlite3.Error, TelegramError):
        await update.message.reply_text("❌ خطایی رخ داد.")
    finally:
        conn.close()

    return ConversationHandler.END

# --- Helper Functions ---


def get_user_language(user_id):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT language FROM users WHERE id = ?", (user_id,))
        result = c.fetchone()
        return result[0] if result else 'fa'
    except sqlite3.Error:
        return 'fa'
    finally:
        conn.close()

# --- Main ---


async def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [CallbackQueryHandler(gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio)],
            EDIT_PROFILE: [CallbackQueryHandler(edit_profile_handler)],
            ADMIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            LANGUAGE: [CallbackQueryHandler(language_handler)]
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(
        menu_handler, pattern='^(register|search|edit|end|block|language)$'))
    app.add_handler(CallbackQueryHandler(filter_gender, pattern='^search_'))
    app.add_handler(CallbackQueryHandler(
        edit_profile_handler, pattern='^edit_'))
    app.add_handler(CallbackQueryHandler(
        filter_age, pattern='^(13-20|21-30|31-40|any)$'))
    app.add_handler(CommandHandler('admin', admin))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO |
                    filters.VIDEO | filters.VOICE, chat))

    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
