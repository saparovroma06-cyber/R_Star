import os
import random
import requests
from django.contrib.auth import get_user_model # Для получения модели User
from .models import Product, Order, OrderItem # Импортируем нужные модели
from django.db import models # Добавляем импорт models для Sum
from asgiref.sync import sync_to_async # Добавляем этот импорт

User = get_user_model() # Получаем текущую модель User

def send_telegram_notification(message):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("Telegram BOT_TOKEN or CHAT_ID is not set in .env")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status() # Вызывает исключение для HTTP ошибок
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")
        return False

# --- Функции для получения статистики ---

def get_registered_users_count():
    return User.objects.count()

def get_total_products_on_site():
    return Product.objects.filter(is_active=True).count()

def get_total_items_sold():
    # Суммируем количество товаров из завершенных заказов
    # Предполагаем, что статус 'completed' означает проданные товары
    return OrderItem.objects.filter(order__status=Order.Status.COMPLETED).aggregate(total_sold=models.Sum('quantity'))['total_sold'] or 0

def get_total_items_in_stock():
    # Суммируем количество всех активных товаров на складе
    return Product.objects.filter(is_active=True).aggregate(total_stock=models.Sum('count'))['total_stock'] or 0

@sync_to_async
def get_site_statistics_message():
    users_count = get_registered_users_count()
    products_count = get_total_products_on_site()
    items_sold = get_total_items_sold()
    items_in_stock = get_total_items_in_stock()

    message = (
        f"📊 <b>Sayt statistikasi:</b>\n\n"
        f"<b>Foydalanuvchilar soni:</b> {users_count}\n"
        f"<b>Faol mahsulotlar:</b> {products_count}\n"
        f"<b>Jami sotilgan mahsulotlar:</b> {items_sold}\n"
        f"<b>Omborda qolgan mahsulotlar:</b> {items_in_stock}\n"
    )
    return message

@sync_to_async
def get_user_info_message(username):
    try:
        user = User.objects.get(username__iexact=username)
        profile = user.profile
        
        total_orders = user.orders.count()
        total_spent = user.orders.filter(status=Order.Status.COMPLETED).aggregate(total_sum=models.Sum('total_price'))['total_sum'] or 0
        
        message = (
            f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
            f"<b>Username:</b> {user.username}\n"
            f"<b>Ism:</b> {user.first_name or 'Kiritilmagan'}\n"
            f"<b>Familiya:</b> {user.last_name or 'Kiritilmagan'}\n"
            f"<b>Email:</b> {user.email or 'Kiritilmagan'}\n"
            f"<b>Telefon:</b> {profile.phone or 'Kiritilmagan'}\n"
            f"<b>O'zi haqida:</b>\n{profile.bio or 'Kiritilmagan'}\n"
            f"<b>Ro'yxatdan o'tgan:</b> {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"<b>Saqlangan to'lov usuli:</b> {'Ha' if profile.has_saved_payment_method else 'Yo\'q'}\n\n"
            f"<b>Buyurtmalar:</b> {total_orders} ta\n"
            f"<b>Jami sarflangan:</b> {total_spent} UZS\n"
        )
        return message
    except User.DoesNotExist:
        return f"Foydalanuvchi '{username}' topilmadi."
    except Exception as e:
        return f"Foydalanuvchi ma'lumotlarini olishda xatolik yuz berdi: {e}"


# --- Рандомные демо-заказы для Telegram ---

RANDOM_NAMES = [
    'Sardor Karimov', 'Aziza Rustamova', 'Javohir Aliyev', 'Malika Yusupova',
    'Bekzod Tursunov', 'Nilufar Qodirova', 'Otabek Ismoilov', 'Zarina Nazarova',
    'Shoxrux Rahimov', 'Dilnoza Sultonova', 'Islom Xudoyorov', 'Sevara Oripova',
]

RANDOM_PHONES = [
    '+998 90 123 45 67', '+998 91 234 56 78', '+998 93 345 67 89',
    '+998 94 456 78 90', '+998 97 567 89 01', '+998 99 678 90 12',
]

RANDOM_DISTRICTS = [
    'Toshkent, Chilonzor tumani, 9-kvartal',
    'Toshkent, Yunusobod tumani, 4-mavze',
    'Toshkent, Mirzo Ulug\'bek tumani, 2-kvartal',
    'Toshkent, Sergeli tumani, Yangi Sergeli',
    'Toshkent, Yashnobod tumani, 1-mavze',
    'Toshkent, Bekobod tumani, Do\'stlik ko\'chasi',
]

RANDOM_BANKS = ['Kapitalbank', 'Ipak Yo\'li Banki', 'Hamkorbank', 'Asakabank', 'TBC Bank']


def send_random_order_notification():
    """Случайный демо-заказ отправляется в Telegram-чат."""
    products = list(Product.objects.filter(is_active=True)[:8])
    if not products:
        return False

    picked = random.sample(products, min(random.randint(1, 3), len(products)))
    name = random.choice(RANDOM_NAMES)
    phone = random.choice(RANDOM_PHONES)
    address = random.choice(RANDOM_DISTRICTS)
    payment_method, payment_label = random.choice([
        ('cash', 'Naqd pul'),
        ('card', 'Karta orqali'),
        ('transfer', 'Bank o\'tkazmasi'),
    ])
    delivery_method, delivery_label = random.choice([
        ('pickup', 'O\'zim olib ketaman'),
        ('delivery', 'Kuryer orqali'),
    ])

    items_lines = []
    total = 0
    for p in picked:
        qty = random.randint(1, 3)
        subtotal = p.sale_price * qty
        total += subtotal
        items_lines.append(f"• {p.name} — {qty} dona × {int(subtotal / qty):,} UZS = {int(subtotal):,} UZS")

    if delivery_method == 'delivery':
        total += 15000

    order_id = random.randint(10000, 99999)

    payment_extra = ''
    if payment_method == 'card':
        payment_extra = f"\n<b>Karta:</b> **** **** **** {random.randint(1000, 9999)}"
    elif payment_method == 'transfer':
        payment_extra = f"\n<b>Bank:</b> {random.choice(RANDOM_BANKS)}"

    message = (
        f"🛒 <b>Yangi buyurtma (demo)!</b>\n\n"
        f"<b>Buyurtma ID:</b> #{order_id}\n"
        f"<b>Mijoz:</b> {name}\n"
        f"<b>Telefon:</b> {phone}\n"
        f"<b>Manzil:</b> {address}\n"
        f"<b>Yetkazib berish:</b> {delivery_label}\n"
        f"<b>To'lov usuli:</b> {payment_label}{payment_extra}\n\n"
        f"<b>Mahsulotlar:</b>\n" + "\n".join(items_lines) + "\n\n"
        f"<b>Jami:</b> {int(total):,} UZS"
    )

    return send_telegram_notification(message)