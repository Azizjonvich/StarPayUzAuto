"""Simple payment webhook test"""
import requests
import json
from datetime import datetime

# Your order ID from webapp
order_id = input("Введите Order ID из webapp (или Enter для тестового): ").strip()
if not order_id:
    order_id = f"test_{int(datetime.now().timestamp())}"

amount = input("Введите сумму (или Enter для 50000): ").strip()
if not amount:
    amount = 50000
else:
    amount = int(amount)

user_id = 8784918764  # Your Telegram ID

# Webhook payload
payload = {
    "order_id": order_id,
    "amount": amount,
    "status": "paid",
    "user_id": user_id,
    "shop_id": "665210",
    "payment_method": "manual_test"
}

print("\n" + "="*60)
print("Отправка тестового платежа...")
print("="*60)
print(f"Order ID: {order_id}")
print(f"Amount: {amount:,} so'm")
print(f"User ID: {user_id}")
print("="*60)

try:
    response = requests.post(
        "https://worker-production-679d.up.railway.app/webhook/payment",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    print(f"\nStatus: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get("ok"):
            print("\n✅ SUCCESS! Платеж обработан!")
            print("Проверьте Telegram - должно прийти уведомление")
        else:
            print(f"\n⚠️ Response OK но есть проблема: {result}")
    else:
        print(f"\n❌ ERROR: Status {response.status_code}")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "="*60)
