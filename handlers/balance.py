from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import keyboards
from services.database import db
import uuid
from datetime import datetime, timedelta

router = Router()

# Karta raqami (USER TO'LOV UCHUN)
CARD_NUMBER = "5614686700537437"


class BalanceStates(StatesGroup):
    waiting_amount = State()


@router.message(F.text == "✨ Hisobni to'ldirish")
async def topup_menu(message: Message, state: FSMContext):
    """Show balance top-up menu"""
    user_id = message.from_user.id
    
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return
    
    text = (
        f"💰 <b>Balansni to'ldirish</b>\n\n"
        f"Quyidagi miqdorni kiriting:\n\n"
        f"🔻Minimal: 1 000 so'm\n"
        f"🔺Maksimal: 2 500 000 so'm"
    )
    
    await message.answer(text, parse_mode="HTML", reply_markup=keyboards.get_back_keyboard())
    await state.set_state(BalanceStates.waiting_amount)


@router.message(BalanceStates.waiting_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    """Process top-up amount and show card info"""
    try:
        amount = float(message.text.replace(",", "").replace(" ", ""))
        
        if amount < 1000:
            await message.answer("❌ Minimal summa: 1 000 so'm. Qayta urinib ko'ring.")
            return
        
        if amount > 2500000:
            await message.answer("❌ Maksimal summa: 2 500 000 so'm. Qayta urinib ko'ring.")
            return
        
        await state.clear()
        
        user_id = message.from_user.id
        order_id = uuid.uuid4().hex[:10]
        
        await db.create_order(order_id, user_id, "topup", int(amount), amount)
        
        # Calculate time window (Tashkent UTC+5)
        now = datetime.utcnow() + timedelta(hours=5)
        end_time = now + timedelta(minutes=5)
        time_str = f"{now.strftime('%H:%M:%S')} — {end_time.strftime('%H:%M:%S')} (Toshkent)"
        
        text = (
            f"✅ <b>To'lov so'rovi yaratildi!</b>\n\n"
            f"🆔 Buyurtma: <code>{order_id}</code>\n"
            f"💰 Miqdori: {int(amount):,} so'm\n\n"
            f"💳 To'lov uchun karta:\n"
            f"<code>{CARD_NUMBER}</code>\n\n"
            f"⏰ To'lov amalga oshirilgach, quyidagi tugmani bosing "
            f"yoki bot avtomatik aniqlaydi.\n\n"
            f"⚠️ Muddat: {time_str}\n"
            f"Aniq 5 daqiqa. Undan keyin avtomatik bekor qilinadi!"
        )
        
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboards.get_card_payment_keyboard(order_id)
        )
        
    except ValueError:
        await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery):
    """Check payment status"""
    await callback.answer("Tekshirilmoqda...")
    
    order_id = callback.data.split("_", 2)[2]
    
    # Check payment status in local database
    from services.database import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        payment = await conn.fetchrow(
            "SELECT * FROM payments WHERE shop_order_id = $1 AND status = 'paid'",
            order_id
        )
    
    if payment:
        # Update order and user balance
        order = await db.get_order(order_id)
        
        if order and order['status'] == "pending":
            await db.update_order(order_id, status="completed")
            
            # Update user balance
            # order keys: telegram_id, amount (not user_id, price)
            await db.update_balance(order['telegram_id'], order['amount'], 'add')
            
            user = await db.get_user(order['telegram_id'])
            
            await callback.message.edit_text(
                f"✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
                f"Hisobingizga {order['amount']:,.0f} so'm qo'shildi.\n"
                f"Yangi balans: {user['balance']:,.0f} so'm",
                parse_mode="HTML"
            )
            await callback.message.answer(
                "🏠 Bosh menyu:",
                reply_markup=keyboards.get_webapp_main_keyboard()
            )
    else:
        await callback.answer(
            "⏳ To'lov hali amalga oshmagan. Iltimos, avval to'lovni bajaring.",
            show_alert=True
        )


@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order(callback: CallbackQuery):
    """Cancel order"""
    await callback.answer()
    
    order_id = callback.data.split("_", 2)[2]
    
    order = await db.get_order(order_id)
    
    if order and order['status'] == "pending":
        await db.update_order(order_id, status="cancelled")
    
    await callback.message.edit_text(
        "❌ Buyurtma bekor qilindi.",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "🏠 Bosh menyu:",
        reply_markup=keyboards.get_webapp_main_keyboard()
    )
