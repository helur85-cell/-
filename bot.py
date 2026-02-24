import asyncio
import os
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import re

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

GROUPS = [
    "МР-24", "ИС-21", "ИС-22", "ИС-23", "ИС-24",
    "ПИ-21", "ПИ-22", "ПИ-23", "ПИ-24",
    "ЭЛ-21", "ЭЛ-22", "ЭЛ-23", "ЭЛ-24",
    "МА-21", "МА-22", "МА-23", "МА-24",
    "ФИ-21", "ФИ-22", "ФИ-23", "ФИ-24",
    "БИ-21", "БИ-22", "БИ-23", "БИ-24",
    "ХИ-21", "ХИ-22", "ХИ-23", "ХИ-24", "ХИ-25"
]

BASE_URL = "https://kmt.kemobl.ru/Studentu-fx3ifzdiool1km80bra3c7/Raspisanie-zanyatij-sds6lyy3puj6e7uocr20i3/"

# ---------------- Парсер ----------------
def get_available_dates_from_footer():
    """
    Парсим нижний блок сайта и получаем даты в формате dd.mm.yyyy
    """
    try:
        response = requests.get(BASE_URL, timeout=10)
        response.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text()

    # Ищем даты формата dd.mm.yyyy
    dates = re.findall(r"\b\d{2}\.\d{2}\.\d{4}\b", text)
    # убираем дубликаты
    return sorted(list(set(dates)))

def get_schedule(group: str, date_str: str):
    """
    Получаем расписание для группы и даты
    """
    payload = {"group": group, "date": date_str}
    try:
        response = requests.get(BASE_URL, params=payload, timeout=10)
        response.raise_for_status()
    except Exception:
        return "Ошибка: не удалось получить расписание с сайта."

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr")

    lessons = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 4:
            time = cols[0].text.strip()
            subject = cols[1].text.strip()
            teacher = cols[2].text.strip()
            room = cols[3].text.strip()
            lessons.append(f"{time} {subject} {teacher} {room}")

    if not lessons:
        return "Занятий нет."
    return "\n".join(lessons)

# ---------------- Клавиатуры ----------------
def group_keyboard():
    keyboard = []
    for group in GROUPS:
        keyboard.append([InlineKeyboardButton(text=group, callback_data=f"group_{group}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def date_keyboard():
    dates = get_available_dates_from_footer()
    keyboard = []
    for date_str in dates:
        keyboard.append([InlineKeyboardButton(text=date_str, callback_data=f"date_{date_str}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ---------------- Хэндлеры ----------------
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Выберите группу:", reply_markup=group_keyboard())

@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    data = call.data

    if data.startswith("group_"):
        group = data.replace("group_", "")
        # запоминаем выбранную группу через user_data
        await call.message.answer(
            f"Группа {group}. Выберите дату:",
            reply_markup=date_keyboard()
        )
        # Сохраним в callback, чтобы потом знать выбранную группу
        # Так как aiogram 3.4 не хранит user_data автоматически,
        # можно просто закодировать группу в callback дата, например:
        global LAST_SELECTED_GROUP
        LAST_SELECTED_GROUP = group

    elif data.startswith("date_"):
        date_str = data.replace("date_", "")
        group = globals().get("LAST_SELECTED_GROUP", None)
        if not group:
            await call.message.answer("Сначала выберите группу.")
            return

        schedule = get_schedule(group, date_str)
        await call.message.answer(
            f"{group} | {date_str}\n\n{schedule}"
        )

# ---------------- Запуск ----------------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
