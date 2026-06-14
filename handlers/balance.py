from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import keyboards
from services.database import db
import uuid
from api_client import api_client

router = Router()


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
        f"💰 <b>Hisobni to'ldirish</b>\n\n"
        f"Joriy balans: {user['balance']:,.0f} so'm\n\n"
        f"To'ldirmoqchi bo'lgan summani kiriting (so'mda):\n\n"
        f"Minimal summa: 10,000 so'm\n"
        f"Maksimal summa: 10,000,000 so'm"
    )
    
    await message.answer(text, parse_mode="HTML")
    await state.set_state(BalanceStates.waiting_amount)


@router.message(BalanceStates.waiting_amount)
async def process_topup_amount(message: Message, state: FSMContext):
    """Process top-up amount"""
    try:
        amount = float(message.text.replace(",", "").replace(" ", ""))
        
        if amount < 10000:
            await message.answer("❌ Minimal summa: 10,000 so'm")
            return
        
        if amount > 10000000:
            await message.answer("❌ Maksimal summa: 10,000,000 so'm")
            return
        
        user_id = message.from_user.id
        
        # Create payment order
        order_id = f"topup_{uuid.uuid4().hex[:8]}"
        
        await db.create_order(order_id, user_id, "topup", int(amount), amount)
        
        # Create payment link
        payment_result = await api_client.create_payment(
            amount=amount,
            order_id=order_id,
            user_id=user_id,
            description=f"Hisobni to'ldirish - {amount:,.0f} so'm"
        )
        
        if payment_result and (payment_result.get("ok") or payment_result.get("success") or payment_result.get("payment_url")):
            payment_url = payment_result.get("payment_url")
            
            # Update order with payment URL
            await db.update_order(order_id, payment_url=payment_url)
            
            text = (
                f"💳 <b>To'lov sahifasi tayyor!</b>\n\n"
                f"Summa: {amount:,.0f} so'm\n"
                f"Buyurtma ID: {order_id}\n\n"
                f"Quyidagi tugmani bosib to'lovni amalga oshiring:"
            )
            
            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=keyboards.get_payment_keyboard(payment_url, order_id)
            )
        else:
            await message.answer(
                "❌ To'lov yaratishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                reply_markup=keyboards.get_main_keyboard()
            )
        
        await state.clear()
        
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
            await db.update_balance(order['user_id'], order['price'], 'add')
            
            user = await db.get_user(order['user_id'])
            
            await callback.message.edit_text(
                f"✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
                f"Hisobingizga {order['price']:,.0f} so'm qo'shildi.\n"
                f"Yangi balans: {user['balance']:,.0f} so'm",
                parse_mode="HTML"
            )
            await callback.message.answer(
                "🏠 Bosh menyu:",
                reply_markup=keyboards.get_main_keyboard()
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
        reply_markup=keyboards.get_main_keyboard()
    )
