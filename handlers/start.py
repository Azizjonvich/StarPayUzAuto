from aiogram import Router, F
from aiogram.types import Message, MessageEntity
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery
from aiogram.utils.formatting import Text, Bold, as_list, as_marked_section
from aiogram.enums import ParseMode
import logging
import keyboards
from services.database import db
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()

# Premium emoji IDs
EMOJI_WAVE = "5312345830382910731"  # 👋
EMOJI_ORANGE = "5336936725765700868"  # 🟠
EMOJI_WALLET = "5215420556089776398"  # 👛
EMOJI_MONEY = "5407091881219736716"  # 💰
EMOJI_PEOPLE = "5879905000972358125"  # 👥
EMOJI_LIGHTNING = "5224496844188458905"  # ⚡️
EMOJI_STAR = "5807791714093502248"  # ⭐️
EMOJI_GIFT = "5348068314629315530"  # 🎁
EMOJI_CHECKMARK = "5774022692642492953"  # ✅
EMOJI_CROSS = "5774077015388852135"  # ❌


def get_welcome_text(user: dict, username: str | None, first_name: str | None) -> str:
    display = f"@{username}" if username else (first_name or "Foydalanuvchi")
    sp_id = user.get("sp_id") or user.get("id", "—")
    return (
        f'<tg-emoji emoji-id="{EMOJI_WAVE}">👋</tg-emoji> <b>Assalomu alaykum, {display}</b>\n\n'
        f'<tg-emoji emoji-id="{EMOJI_ORANGE}">🟠</tg-emoji> <b>StarPayUz ID:</b> <code>{sp_id}</code>\n'
        f'┗ <tg-emoji emoji-id="{EMOJI_WALLET}">👛</tg-emoji> <b>Balans:</b> {user["balance"]:,.0f} so\'m\n'
        f'┗ <tg-emoji emoji-id="{EMOJI_PEOPLE}">👥</tg-emoji> <b>Referallar:</b> {user["referrals"]} ta\n\n'
        f'<blockquote><tg-emoji emoji-id="{EMOJI_LIGHTNING}">⚡️</tg-emoji> <b>Kerakli bo\'limni tanlang:</b></blockquote>'
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Check for referral
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
        except:
            pass
    
    # Create or update user in database
    user = await db.get_user(user_id)
    
    if not user:
        user = await db.create_user(user_id, username, first_name, referrer_id)
    
    welcome_text = get_welcome_text(user, username, first_name)

    await message.answer(
        welcome_text,
        reply_markup=keyboards.get_webapp_main_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🏠 Bosh menyu")
async def back_to_main(message: Message):
    """Return to main menu"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if user:
        text = get_welcome_text(
            user,
            message.from_user.username,
            message.from_user.first_name,
        )
    else:
        text = "🏠 Bosh menyu:"
    
    await message.answer(
        text,
        reply_markup=keyboards.get_webapp_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: CallbackQuery):
    """Show user's orders"""
    await callback.answer()
    user_id = callback.from_user.id
    
    orders = await db.get_user_orders(user_id, limit=10)
    
    if not orders:
        await callback.message.answer(
            "📦 <b>Buyurtmalarim</b>\n\n"
            "Sizda hali buyurtmalar yo'q.",
            parse_mode="HTML"
        )
        return
    
    text = "📦 <b>So'nggi 10 ta buyurtma:</b>\n\n"
    
    for order in orders:
        status_emoji = {
            "pending": "⏳",
            "processing": "🔄",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "🚫"
        }.get(order['status'], "❓")
        
        product_name = {
            "stars": "⭐ Stars",
            "premium": "💎 Premium",
            "topup": "💰 Hisobni to'ldirish",
            "phone": "📱 Virtual raqam",
            "gift": "🎁 Gift"
        }.get(order['product_type'], order['product_type'])
        
        text += (
            f"{status_emoji} <b>{product_name}</b>\n"
            f"   ID: <code>{order['order_id']}</code>\n"
            f"   Summa: {order['price']:,.0f} so'm\n"
            f"   Sana: {order['created_at'][:19].replace('T', ' ')}\n\n"
        )
    
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "referrals")
async def callback_referrals(callback: CallbackQuery):
    """Show referral information"""
    await callback.answer()
    user_id = callback.from_user.id
    
    user = await db.get_user(user_id)
    
    if not user:
        await callback.message.answer("❌ Foydalanuvchi topilmadi!")
        return
    
    # Get referral link
    bot_username = (await callback.bot.me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    # Count referrals
    referrals = await db.get_referrals(user_id)
    
    text = (
        f"👥 <b>Referral dasturi</b>\n\n"
        f"Do'stlaringizni taklif qiling va bonus oling!\n\n"
        f"📊 <b>Sizning statistikangiz:</b>\n"
        f"👤 Taklif qilinganlar: {len(referrals)} ta\n"
        f"💰 Referal bonusi: {len(referrals) * 5000:,.0f} so'm\n\n"
        f"🎁 Har bir do'stingiz uchun: 5,000 so'm\n\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"Havolani nusxalab, do'stlaringizga yuboring!"
    )
    
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "stars_menu")
async def callback_stars_menu(callback: CallbackQuery):
    """Show stars purchase menu"""
    await callback.answer()
    
    text = (
        f'<tg-emoji emoji-id="{EMOJI_STAR}">⭐</tg-emoji> <b>Telegram Stars sotib olish</b>\n\n'
        "Stars — Telegram ichida maxsus kontent va xizmatlarni "
        "sotib olish uchun ishlatiladi.\n\n"
        "📦 <b>Mavjud paketlar:</b>"
    )
    
    await callback.message.answer(
        text,
        reply_markup=keyboards.get_stars_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "premium_menu")
async def callback_premium_menu(callback: CallbackQuery):
    """Show premium purchase menu"""
    await callback.answer()
    
    text = (
        "💎 <b>Telegram Premium sotib olish</b>\n\n"
        "Premium obuna bilan qo'shimcha imkoniyatlarga ega bo'ling:\n\n"
        "✨ Tezroq yuklab olish tezligi\n"
        "📁 4 GB gacha fayllar\n"
        "🎨 Eksklyuziv stikerlar\n"
        "👤 Premium emoji va badge\n"
        "💬 Kengaytirilgan chat imkoniyatlari\n\n"
        "📦 <b>Mavjud paketlar:</b>"
    )
    
    await callback.message.answer(
        text,
        reply_markup=keyboards.get_premium_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "phone_menu")
async def callback_phone_menu(callback: CallbackQuery):
    """Show phone menu"""
    await callback.answer()
    
    text = (
        "📱 <b>Virtual raqamlar</b>\n\n"
        "Tez orada mavjud bo'ladi...\n\n"
        "Bu bo'limda siz turli xizmatlar uchun "
        "virtual telefon raqamlarini sotib olishingiz mumkin bo'ladi."
    )
    
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "gift_menu")
async def callback_gift_menu(callback: CallbackQuery):
    """Show gift menu"""
    await callback.answer()
    
    text = (
        f'<tg-emoji emoji-id="{EMOJI_GIFT}">🎁</tg-emoji> <b>Gift sovg\'alar</b>\n\n'
        "Tez orada mavjud bo'ladi...\n\n"
        "Bu bo'limda siz do'stlaringizga Premium, "
        "Stars va boshqa sovg'alarni yuborishingiz mumkin bo'ladi."
    )
    
    await callback.message.answer(
        text,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "topup_menu")
async def callback_topup_menu(callback: CallbackQuery):
    """Show topup menu"""
    await callback.answer()
    
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        text = f'<tg-emoji emoji-id="{EMOJI_CROSS}">❌</tg-emoji> Foydalanuvchi topilmadi!'
        await callback.message.answer(text, parse_mode="HTML")
        return
    
    text = (
        f'<tg-emoji emoji-id="{EMOJI_MONEY}">💰</tg-emoji> <b>Hisobni to\'ldirish</b>\n\n'
        f"Joriy balans: {user['balance']:,.0f} so'm\n\n"
        f"To'ldirish funksiyasi tez orada qo'shiladi.\n"
        f"Hozircha admin bilan bog'laning: @StarPayUz_Admin"
    )
    
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "support")
async def callback_support(callback: CallbackQuery):
    """Show support information"""
    await callback.answer()
    
    text = (
        "🔒 <b>Qo'llab-quvvatlash</b>\n\n"
        "Savol yoki muammo bo'lsa, biz bilan bog'laning:\n\n"
        "👤 Admin: @StarPayUzAdmin\n"
        "📢 Kanal: @StarPayUzNews\n"
        "💬 Guruh: @StarPayUz_Chat\n\n"
        "⏰ Ish vaqti: 9:00 - 22:00 (har kuni)\n\n"
        "📧 Email: support@starpayuz.com"
    )
    
    await callback.message.answer(text, parse_mode="HTML")
