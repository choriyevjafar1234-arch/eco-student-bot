import asyncio
import logging
import re
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import os
TOKEN = os.getenv("TOKEN")
import os
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB_NAME = "locations.db"

PHONE_RE = re.compile(r"^\+?\d{9,13}$")


class WasteForm(StatesGroup):
    waste_type = State()
    photo = State()
    location = State()
    address = State()
    phone = State()


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS waste_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT,
            waste_type TEXT,
            photo_id TEXT,
            latitude REAL,
            longitude REAL,
            address TEXT,
            phone TEXT,
            status TEXT DEFAULT 'yangi',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_location(user_id, username, full_name, lat, lon):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_locations (user_id, username, full_name, latitude, longitude, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, username, full_name, lat, lon, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_user_locations(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT latitude, longitude, created_at
        FROM user_locations
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_locations():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, username, full_name, latitude, longitude, created_at
        FROM user_locations
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_waste_request(user_id, username, full_name, waste_type, photo_id, lat, lon, address, phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO waste_requests
        (user_id, username, full_name, waste_type, photo_id, latitude, longitude, address, phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, full_name, waste_type, photo_id, lat, lon, address, phone,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_all_waste_requests():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, full_name, username, waste_type, latitude, longitude, address, phone, created_at
        FROM waste_requests
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)],
            [KeyboardButton(text="📋 Mening lokatsiyalarim")],
            [KeyboardButton(text="♻️ Chiqindi topshirish"), KeyboardButton(text="📞 Bog'lanish")],
            [KeyboardButton(text="ℹ️ Ma'lumot")]
        ],
        resize_keyboard=True
    )


def waste_type_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧴 Plastik"), KeyboardButton(text="📄 Qog'oz")],
            [KeyboardButton(text="💻 Elektronika"), KeyboardButton(text="🍾 Shisha")],
            [KeyboardButton(text="🗑 Boshqa")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "🌿 Yashil makon, yashil kelajak loyihasiga xush kelibsiz!\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=main_keyboard()
    )


# MUHIM: bu handler faqat foydalanuvchi hech qanday FSM holatida bo'lmaganda ishlaydi
# (StateFilter(None)). Aks holda "Chiqindi topshirish" jarayonidagi lokatsiya shu yerga
# tushib qolib, waste_location_handler hech qachon chaqirilmas edi.
@dp.message(StateFilter(None), lambda message: message.location is not None)
async def location_handler(message: Message):
    lat = message.location.latitude
    lon = message.location.longitude
    user = message.from_user

    save_location(
        user_id=user.id,
        username=user.username or "yoq",
        full_name=user.full_name,
        lat=lat,
        lon=lon
    )

    await message.answer(
        f"Joylashuvingiz saqlandi!\n\n"
        f"Kenglik: {lat}\n"
        f"Uzunlik: {lon}\n"
        f"Xarita: https://maps.google.com/?q={lat},{lon}"
    )


@dp.message(StateFilter(None), lambda message: message.text == "📋 Mening lokatsiyalarim")
async def my_locations_handler(message: Message):
    rows = get_user_locations(message.from_user.id)

    if not rows:
        await message.answer("Siz hali lokatsiya yubormagansiz.")
        return

    text = f"Sizning lokatsiyalaringiz (oxirgi {len(rows)} ta):\n\n"
    for i, (lat, lon, created) in enumerate(rows[:10], 1):
        text += f"{i}. {created}\n   {lat}, {lon}\n\n"

    await message.answer(text)


@dp.message(StateFilter(None), lambda message: message.text == "♻️ Chiqindi topshirish")
async def waste_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Chiqindi topshirish\n\n"
        "Qanday turdagi chiqindini topshirmoqchisiz?",
        reply_markup=waste_type_keyboard()
    )
    await state.set_state(WasteForm.waste_type)


@dp.message(WasteForm.waste_type)
async def waste_type_handler(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_keyboard())
        return

    valid_types = {"🧴 Plastik", "📄 Qog'oz", "💻 Elektronika", "🍾 Shisha", "🗑 Boshqa"}
    if message.text not in valid_types:
        await message.answer("Iltimos, tugmalardan birini tanlang.")
        return

    await state.update_data(waste_type=message.text)
    await message.answer(
        f"Turi: {message.text}\n\n"
        "Endi chiqindining rasmini yuboring:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(WasteForm.photo)


@dp.message(WasteForm.photo)
async def waste_photo_handler(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_keyboard())
        return

    if not message.photo:
        await message.answer("Iltimos, rasm yuboring!")
        return

    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)

    await message.answer(
        "Rasm qabul qilindi!\n\n"
        "Endi joylashuvingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)],
                [KeyboardButton(text="❌ Bekor qilish")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(WasteForm.location)


@dp.message(WasteForm.location)
async def waste_location_handler(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_keyboard())
        return

    if not message.location:
        await message.answer("Iltimos, joylashuvni yuboring!")
        return

    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )

    await message.answer(
        "Joylashuv qabul qilindi!\n\n"
        "Endi manzilni yozing (kocha, uy raqami):",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(WasteForm.address)


@dp.message(WasteForm.address)
async def waste_address_handler(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_keyboard())
        return

    if not message.text:
        await message.answer("Iltimos, manzilni matn ko'rinishida yozing!")
        return

    await state.update_data(address=message.text)
    await message.answer(
        "Manzil qabul qilindi!\n\n"
        "Endi telefon raqamingizni yuboring:\n"
        "(Masalan: +998901234567)",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)],
                [KeyboardButton(text="❌ Bekor qilish")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(WasteForm.phone)


@dp.message(WasteForm.phone)
async def waste_phone_handler(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_keyboard())
        return

    if message.contact:
        phone = message.contact.phone_number
    elif message.text and PHONE_RE.match(message.text.replace(" ", "")):
        phone = message.text.replace(" ", "")
    else:
        await message.answer(
            "Telefon raqam noto'g'ri formatda.\n"
            "Iltimos, quyidagi ko'rinishda yuboring: +998901234567"
        )
        return

    data = await state.get_data()
    user = message.from_user

    save_waste_request(
        user_id=user.id,
        username=user.username or "yoq",
        full_name=user.full_name,
        waste_type=data.get("waste_type"),
        photo_id=data.get("photo_id"),
        lat=data.get("latitude"),
        lon=data.get("longitude"),
        address=data.get("address"),
        phone=phone
    )

    await message.answer(
        "Arizangiz qabul qilindi!\n\n"
        f"Turi: {data.get('waste_type')}\n"
        f"Manzil: {data.get('address')}\n"
        f"Telefon: {phone}\n\n"
        "Tez orada kongillilar chiqindini olib ketishadi!",
        reply_markup=main_keyboard()
    )

    try:
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=data.get("photo_id"),
            caption=(
                f"YANGI ARIZA!\n\n"
                f"{user.full_name} (@{user.username or 'yoq'})\n"
                f"Turi: {data.get('waste_type')}\n"
                f"Manzil: {data.get('address')}\n"
                f"Telefon: {phone}\n"
                f"{data.get('latitude')}, {data.get('longitude')}"
            )
        )
    except Exception as e:
        logging.error(f"Admin ga xabar yuborishda xato: {e}")

    await state.clear()


@dp.message(StateFilter(None), lambda message: message.text == "📞 Bog'lanish")
async def contact_handler(message: Message):
    await message.answer(
        "Boglanish:\n\n"
        "Telefon: +998 97 642 81 11\n"
        "Email: info@eco.uz\n"
        "Telegram: @EcoStudentTashkent\n"
        "Manzil: Toshkent sh."
    )


@dp.message(StateFilter(None), lambda message: message.text == "ℹ️ Ma'lumot")
async def info_handler(message: Message):
    await message.answer(
        "EKO Chiqindi bot haqida:\n\n"
        "Yashil makon, yashil kelajak loyihasi\n"
        "Chiqindilarni yigish va qayta ishlash\n"
        "Kongillilar chiqindini olib ketadi\n\n"
        "Biz bilan tabiatni asrang!"
    )


@dp.message(Command("admin"))
async def admin_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda ruxsat yoq.")
        return

    rows = get_all_locations()
    if not rows:
        await message.answer("Baza bosh.")
        return

    text = "Oxirgi lokatsiyalar:\n\n"
    for user_id, username, full_name, lat, lon, created in rows:
        text += f"{full_name} (@{username})\n"
        text += f"{lat}, {lon}\n"
        text += f"{created}\n\n"

    await message.answer(text)


@dp.message(Command("arizalar"))
async def admin_waste_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda ruxsat yoq.")
        return

    rows = get_all_waste_requests()
    if not rows:
        await message.answer("Arizalar yoq.")
        return

    text = "Oxirgi arizalar:\n\n"
    for req_id, full_name, username, waste_type, lat, lon, address, phone, created in rows:
        text += f"#{req_id} | {created}\n"
        text += f"{full_name} (@{username})\n"
        text += f"Turi: {waste_type}\n"
        text += f"Manzil: {address}\n"
        text += f"Telefon: {phone}\n\n"

    await message.answer(text)


async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
