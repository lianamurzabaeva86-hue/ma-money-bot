import os

# Токен бота — ТОЛЬКО из переменной окружения!
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID администратора
ADMIN_ID = 6782041245

# Настройки базы данных
DATABASE_PATH = "moneybot.db"

# Настройки бота
MIN_WITHDRAWAL = 200
REFERRAL_PERCENT = 10

# Рабочее время бота (7:00 - 20:00 по Москве)
WORK_START_HOUR = 7
WORK_END_HOUR = 20