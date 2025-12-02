from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import datetime
import logging
import re
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импортируем ваши модули
from database import Database
from settings import MIN_WITHDRAWAL, WORK_START_HOUR, WORK_END_HOUR, ADMIN_ID

router = Router()
db = Database()

# ===== КЛАВИАТУРЫ =====
def main_menu_keyboard(user_id=None):
    """Главное меню"""
    keyboard = [
        [KeyboardButton(text="💼 Приступить к работе"), KeyboardButton(text="📊 Личный кабинет")],
        [KeyboardButton(text="👥 Реферальная система"), KeyboardButton(text="💳 Вывести средства")],
        [KeyboardButton(text="🆘 Поддержка")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="👨‍💼 Админ")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True
    )

def user_management_keyboard(user_id):
    """Клавиатура для управления пользователем"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💸 Списать средства", callback_data=f"deduct_balance_{user_id}"),
                InlineKeyboardButton(text="💰 Пополнить баланс", callback_data=f"add_balance_{user_id}")
            ],
            [
                InlineKeyboardButton(text="👥 Управление рефералами", callback_data=f"manage_refs_{user_id}"),
                InlineKeyboardButton(text="📊 История операций", callback_data=f"history_{user_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_balances")
            ]
        ]
    )

def referrals_management_keyboard(referrals):
    """Клавиатура для выбора рефералов"""
    keyboard = []
    # Добавляем кнопки для каждого реферала
    for referral in referrals:
        ref_user_id, ref_username, ref_registered_at, ref_balance = referral
        username_display = f"@{ref_username}" if ref_username else f"ID: {ref_user_id}"
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ {username_display}",
                callback_data=f"select_ref_{ref_user_id}"
            )
        ])
    # Добавляем кнопки для массовых действий
    keyboard.append([
        InlineKeyboardButton(text="✅ Выбрать все", callback_data="select_all_refs"),
        InlineKeyboardButton(text="🗑️ Удалить выбранные", callback_data="remove_selected_refs")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_user_management")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_keyboard():
    """Клавиатура админ-панели"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📝 Создать задание")],
            [KeyboardButton(text="⏳ Задания на проверке"), KeyboardButton(text="💳 Выводы на проверке")],
            [KeyboardButton(text="📋 Все задания"), KeyboardButton(text="👥 Балансы пользователей")],
            [KeyboardButton(text="📋 История выводов"), KeyboardButton(text="📢 Рассылка")],
            [KeyboardButton(text="📢 Реклама"), KeyboardButton(text="🔙 В главное меню")]
        ],
        resize_keyboard=True
    )

def ads_management_keyboard():
    """Клавиатура управления рекламой"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Создать рекламу"), KeyboardButton(text="📋 Список реклам")],
            [KeyboardButton(text="🗑️ Очистить рекламу"), KeyboardButton(text="🔙 В главное меню")]
        ],
        resize_keyboard=True
    )

def confirmation_keyboard():
    """Клавиатура подтверждения вывода"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Всё верно, подтверждаю вывод")],
            [KeyboardButton(text="❌ Отменить вывод")]
        ],
        resize_keyboard=True
    )

def payment_method_keyboard():
    """Клавиатура выбора способа оплаты"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Номер карты"), KeyboardButton(text="📱 Номер телефона")],
            [KeyboardButton(text="❌ Отменить вывод")]
        ],
        resize_keyboard=True
    )

def tasks_menu_keyboard(tasks=None):
    """Клавиатура меню заданий только с заданиями и главным меню"""
    keyboard = []
    if tasks:
        # Добавляем кнопки для каждого задания
        for task in tasks:
            task_id, title, price, description, instruction, link, max_completions, current_completions, is_active, created_at = task
            button_text = f"🎯 {title} - {price} руб."
            keyboard.append([KeyboardButton(text=button_text)])
    # Только кнопка главного меню
    keyboard.append([KeyboardButton(text="🔙 Главное меню")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def task_detail_keyboard(task_id):
    """Клавиатура для деталей задания"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"✅ Взять задание #{task_id}")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def tasks_keyboard(tasks):
    """Инлайн клавиатура с заданиями"""
    keyboard = []
    for task in tasks:
        task_id, title, price, description, instruction, link, max_completions, current_completions, is_active, created_at = task
        # Форматируем текст кнопки
        button_text = f"{title} [{price} руб.]"
        keyboard.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"task_{task_id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def withdrawal_review_keyboard(withdrawal_id):
    """Клавиатура проверки вывода для админа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_withdrawal_{withdrawal_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_withdrawal_{withdrawal_id}")
            ]
        ]
    )

def task_review_keyboard(user_task_id):
    """Клавиатура проверки задания для админа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_task_{user_task_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_task_{user_task_id}")
            ]
        ]
    )

def get_advertisement_keyboard():
    """Клавиатура с рекламой для пользователей"""
    try:
        active_ad = db.get_active_advertisement()
        if active_ad:
            ad_id, ad_text, ad_link, is_active, created_at = active_ad
            # Создаем кнопку с рекламой
            return InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"📢 {ad_text}", url=ad_link)],
                ]
            )
        else:
            return None
    except Exception as e:
        logger.error(f"Error getting ad keyboard: {e}")
        return None

# ===== СОСТОЯНИЯ =====
class WithdrawalStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_bank = State()
    waiting_for_payment_method = State()
    waiting_for_card_number = State()
    waiting_for_phone_number = State()
    waiting_for_recipient_name = State()
    waiting_for_confirmation = State()

class TaskStates(StatesGroup):
    waiting_for_screenshot = State()

class AdminStates(StatesGroup):
    waiting_for_task_title = State()
    waiting_for_task_price = State()
    waiting_for_task_description = State()
    waiting_for_task_instruction = State()
    waiting_for_task_link = State()
    waiting_for_task_max_completions = State()
    waiting_for_reject_reason = State()
    waiting_for_user_selection = State()
    waiting_for_deduct_amount = State()
    waiting_for_deduct_reason = State()
    waiting_for_remove_ref_user = State()
    waiting_for_remove_ref_selection = State()
    waiting_for_withdrawal_reject_reason = State()

class BroadcastStates(StatesGroup):
    waiting_for_broadcast_message = State()
    waiting_for_ad_broadcast_message = State()
    waiting_for_ad_broadcast_link = State()

class AdStates(StatesGroup):
    waiting_for_ad_text = State()
    waiting_for_ad_link = State()
    waiting_for_ad_confirmation = State()

# ===== ФУНКЦИЯ ДЛЯ ОТОБРАЖЕНИЯ РЕКЛАМЫ ВСЕМ ПОЛЬЗОВАТЕЛЯМ =====
async def show_pinned_ad_to_user(user_id: int, bot):
    """Показать закрепленную рекламу пользователю"""
    try:
        active_ad = db.get_active_advertisement()
        if active_ad:
            ad_id, ad_text, ad_link, is_active, created_at, created_by = active_ad
            # Создаем кнопку с рекламой
            ad_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Перейти", url=ad_link)],
                ]
            )
            # Отправляем сообщение и закрепляем его
            sent_message = await bot.send_message(
                chat_id=user_id,
                text=f"📢 {ad_text}",
                reply_markup=ad_keyboard
            )
            # Закрепляем сообщение
            await bot.pin_chat_message(
                chat_id=user_id,
                message_id=sent_message.message_id
            )
            return True
    except Exception as e:
        logger.error(f"Error showing pinned ad to user {user_id}: {e}")
    return False

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    local_db = Database()  # ← локальный экземпляр
    try:
        await state.clear()
        user_id = message.from_user.id
        username = message.from_user.username
        invited_by = None
        parts = message.text.split()
        if len(parts) > 1:
            ref_param = parts[1]
            if ref_param.isdigit():
                invited_by = int(ref_param)
            elif ref_param.startswith('ref_'):
                try:
                    invited_by = int(ref_param[4:])
                except:
                    pass
            else:
                numbers = re.findall(r'\d+', ref_param)
                if numbers:
                    invited_by = int(numbers[0])

        if invited_by == user_id:
            invited_by = None
        else:
            referrer_exists = local_db.get_user(invited_by)
            if not referrer_exists:
                invited_by = None

        if invited_by and invited_by != user_id:
            local_db.add_user(user_id, username, invited_by)
            referrer_data = local_db.get_user(invited_by)
            if referrer_data:
                new_ref_count = local_db.get_actual_ref_count(invited_by)
                try:
                    await message.bot.send_message(
                        chat_id=invited_by,
                        text=f"🎉 По вашей ссылке присоединился новый пользователь!\n👤: @{username or 'без username'}\n📊 Теперь у вас {new_ref_count} рефералов!"
                    )
                except:
                    pass
        else:
            local_db.add_user(user_id, username)

        # Показ рекламы
        active_ad = local_db.get_active_advertisement()
        if active_ad:
            ad_id, ad_text, ad_link, is_active, created_at = active_ad[:5]
            ad_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔗 Перейти", url=ad_link)]]
            )
            sent_message = await message.bot.send_message(
                chat_id=user_id,
                text=f"📢 {ad_text}",
                reply_markup=ad_keyboard
            )
            await message.bot.pin_chat_message(chat_id=user_id, message_id=sent_message.message_id)

        welcome_text = """
👋 Добро пожаловать в MoneyBot!
💰 Зарабатывайте выполняя простые задания
⏰ Работаем с 7:00 до 20:00 по МСК  
💎 Приводите друзей и получайте бонусы!
Выберите нужный раздел:
        """
        await message.answer(welcome_text, reply_markup=main_menu_keyboard(user_id))
    except Exception as e:
        logger.error(f"Error in start: {e}")
        await message.answer("❌ Ошибка.")
    finally:
        local_db.close()  # ← обязательно закрываем!

@router.message(Command("ref_link"))
async def ref_link(message: Message):
    """Проверка правильности реферальной ссылки"""
    user_id = message.from_user.id
    try:
        bot_username = (await message.bot.get_me()).username
        print(f"Bot username: {bot_username}")
        # Разные варианты ссылок
        ref_links = {
            "Стандартная": f"https://t.me/{bot_username}?start={user_id}",
            "Без https": f"t.me/{bot_username}?start={user_id}", 
            "С ref_": f"https://t.me/{bot_username}?start=ref_{user_id}",
            "Только команда": f"/start {user_id}"
        }
        text = "🔗 ПРОВЕРКА РЕФЕРАЛЬНЫХ ССЫЛОК:\n"
        text += f"🤖 Username бота: @{bot_username}\n"
        text += f"👤 Ваш ID: {user_id}\n"
        for name, link in ref_links.items():
            text += f"**{name}:**\n`{link}`\n"
        text += "📝 **Инструкция:**\n"
        text += "1. Скопируйте любую ссылку\n"
        text += "2. Отправьте другу или откройте сами\n"
        text += "3. Проверьте логи в консоли бота\n"
        text += "4. Используйте /debug_ref для проверки\n"
        await message.answer(text)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("debug_ref"))
async def debug_ref(message: Message):
    """Команда для отладки реферальной системы"""
    user_id = message.from_user.id
    # Получаем данные пользователя
    user_data = db.get_user(user_id)
    if not user_data:
        await message.answer("❌ Пользователь не найден в БД")
        return
    debug_text = f"""
🔧 ДЕБАГ РЕФЕРАЛЬНОЙ СИСТЕМЫ:
👤 Ваш ID: {user_data[0]}
📛 Username: @{user_data[1]}
💰 Баланс: {user_data[2]:.2f} руб.
👥 Рефералов: {user_data[4]}
💰 Заработано с рефералов: {user_data[5]:.2f} руб.
🤝 Пригласил: {user_data[6] or 'никто'}
📅 Регистрация: {user_data[7]}
📊 ПРОВЕРКА МЕТОДОВ БАЗЫ ДАННЫХ:
"""
    # Тестируем методы базы данных
    try:
        # Тест increment_ref_count
        original_ref_count = user_data[4]
        test_success = db.increment_ref_count(user_id)
        # Проверяем обновленные данные
        updated_data = db.get_user(user_id)
        new_ref_count = updated_data[4] if updated_data else original_ref_count
        debug_text += f"\n🔹 increment_ref_count: {'✅ УСПЕХ' if test_success else '❌ ОШИБКА'}"
        debug_text += f"\n🔹 Рефералов ДО: {original_ref_count}"
        debug_text += f"\n🔹 Рефералов ПОСЛЕ: {new_ref_count}"
        # Тест add_user
        test_user_id = 999000111  # тестовый ID
        add_test = db.add_user(test_user_id, "test_user", user_id)
        debug_text += f"\n🔹 add_user: {'✅ УСПЕХ' if add_test else '❌ ОШИБКА'}"
        # Удаляем тестового пользователя
        try:
            db.cursor.execute("DELETE FROM users WHERE user_id = ?", (test_user_id,))
            db.conn.commit()
        except:
            pass
    except Exception as e:
        debug_text += f"\n❌ Ошибка теста: {e}"
    # Проверяем ссылку
    try:
        bot_username = (await message.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        debug_text += f"\n🔗 ВАША РЕФЕРАЛЬНАЯ ССЫЛКА:\n`{ref_link}`"
        debug_text += f"\n📝 ФОРМАТ КОМАНДЫ ПРИ ПЕРЕХОДЕ:\n`/start {user_id}`"
    except Exception as e:
        debug_text += f"\n❌ Ошибка получения username бота: {e}"
    await message.answer(debug_text)

@router.message(Command("test_ref"))
async def test_ref(message: Message):
    """Тест реферальной системы с симуляцией"""
    user_id = message.from_user.id
    # Получаем текущие данные
    user_data = db.get_user(user_id)
    original_ref_count = user_data[4] if user_data else 0
    # Симулируем переход по реферальной ссылке
    test_user_id = user_id + 1  # уникальный тестовый ID
    test_username = "test_referral_user"
    print(f"\n{'='*50}")
    print(f"🧪 ТЕСТ РЕФЕРАЛЬНОЙ СИСТЕМЫ")
    print(f"Реферер: {user_id}")
    print(f"Тестовый реферал: {test_user_id}")
    print(f"{'='*50}")
    # Тестируем добавление пользователя с рефералом
    print("1. Тестируем add_user...")
    add_success = db.add_user(test_user_id, test_username, user_id)
    print(f"   add_user результат: {add_success}")
    # Тестируем увеличение счетчика
    print("2. Тестируем increment_ref_count...")
    ref_success = db.increment_ref_count(user_id)
    print(f"   increment_ref_count результат: {ref_success}")
    # Проверяем обновленные данные
    print("3. Проверяем обновленные данные...")
    updated_user = db.get_user(user_id)
    new_ref_count = updated_user[4] if updated_user else original_ref_count
    # Проверяем данные тестового пользователя
    test_user_data = db.get_user(test_user_id)
    test_invited_by = test_user_data[6] if test_user_data else None
    # Очищаем тестовые данные
    try:
        db.cursor.execute("DELETE FROM users WHERE user_id = ?", (test_user_id,))
        db.conn.commit()
        print("4. Тестовые данные очищены")
    except Exception as e:
        print(f"4. Ошибка очистки тестовых данных: {e}")
    # Формируем результат
    test_result = f"""
🧪 ТЕСТ РЕФЕРАЛЬНОЙ СИСТЕМЫ:
📊 ВАШИ ДАННЫЕ:
├─ ID: {user_id}
├─ Рефералов ДО: {original_ref_count}
└─ Рефералов ПОСЛЕ: {new_ref_count}
🔧 РЕЗУЛЬТАТЫ ТЕСТА:
├─ add_user: {'✅ УСПЕХ' if add_success else '❌ ОШИБКА'}
├─ increment_ref_count: {'✅ УСПЕХ' if ref_success else '❌ ОШИБКА'}
└─ invited_by у тестового пользователя: {test_invited_by or '❌ НЕ УСТАНОВЛЕН'}
📈 ИТОГ: {'✅ РЕФЕРАЛЬНАЯ СИСТЕМА РАБОТАЕТ' if (add_success and ref_success and test_invited_by == user_id) else '❌ ЕСТЬ ПРОБЛЕМЫ'}
🔍 Проверьте логи в консоли для деталей.
"""
    await message.answer(test_result)

@router.message(Command("check_ref"))
async def check_ref(message: Message):
    """Проверка реферальной системы"""
    user_id = message.from_user.id
    user_data = db.get_user(user_id)
    if user_data:
        debug_text = f"""
🔍 ПРОВЕРКА РЕФЕРАЛЬНОЙ СИСТЕМЫ:
👤 Ваш ID: {user_data[0]}
📛 Username: @{user_data[1]}
💰 Баланс: {user_data[2]:.2f} руб.
📈 Всего заработано: {user_data[3]:.2f} руб.
👥 Рефералов: {user_data[4]}
💰 С рефералов: {user_data[5]:.2f} руб.
🤝 Пригласил: {user_data[6] or 'никто'}
📅 Регистрация: {user_data[7]}
        """
        # Проверяем пригласившего
        if user_data[6]:
            referrer_data = db.get_user(user_data[6])
            if referrer_data:
                debug_text += f"\n👥 ДАННЫЕ ПРИГЛАСИВШЕГО:"
                debug_text += f"\nID: {referrer_data[0]}"
                debug_text += f"\nUsername: @{referrer_data[1]}"
                debug_text += f"\nРефералов: {referrer_data[4]}"
                debug_text += f"\nБаланс: {referrer_data[2]:.2f} руб."
            else:
                debug_text += f"\n❌ Пригласивший (ID: {user_data[6]}) не найден в БД"
        await message.answer(debug_text)
    else:
        await message.answer("❌ Пользователь не найден в БД")

# ===== МЕНЮ ЗАДАНИЙ =====
async def show_tasks_menu(message: Message):
    """Показать меню заданий с доступными заданиями"""
    local_db = Database()  # ← создаём локальный экземпляр
    try:
        can_interact, error_message = local_db.can_user_interact(message.from_user.id)
        if not can_interact:
            await message.answer(
                error_message,
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🔙 Главное меню")]],
                    resize_keyboard=True
                )
            )
            return

        tasks = local_db.get_active_tasks_for_user(message.from_user.id)
        if not tasks:
            await message.answer(
                "📭 На данный момент нет доступных заданий для вас",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="🔙 Главное меню")]],
                    resize_keyboard=True
                )
            )
            return

        # Показываем только кнопки заданий + главное меню
        await message.answer(
            "🎯 **Доступные задания**\n⬇️ Выберите задание ниже:",
            parse_mode="HTML",
            reply_markup=tasks_menu_keyboard(tasks)
        )
    except Exception as e:
        logger.error(f"Error in show_tasks_menu: {e}")
        await message.answer("❌ Ошибка при загрузке заданий")
    finally:
        local_db.close()  # ← обязательно закрываем соединение

@router.message(F.text == "💼 Приступить к работе")
async def start_work(message: Message, state: FSMContext):
    local_db = Database()
    try:
        await state.clear()
        can_interact, error_message = local_db.can_user_interact(message.from_user.id)
        if not can_interact:
            await message.answer(error_message, reply_markup=main_menu_keyboard(message.from_user.id))
            return

        active_task = local_db.get_user_active_task(message.from_user.id)
        if active_task:
            task = local_db.get_task(active_task[2])
            if task:
                await message.answer(
                    f"⚠️ У вас уже есть активное задание: \"{task[1]}\"!\nПосле выполнения отправьте скриншот подтверждения.\n📸 Отправьте скриншот выполнения задания:",
                    reply_markup=cancel_keyboard()
                )
                await state.set_state(TaskStates.waiting_for_screenshot)
                return

        tasks = local_db.get_active_tasks_for_user(message.from_user.id)
        await message.answer("🎯 Доступные задания...", reply_markup=tasks_menu_keyboard(tasks))
    except Exception as e:
        logger.error(f"Error in start_work: {e}")
        await message.answer("❌ Ошибка.")
    finally:
        local_db.close()
        
@router.message(F.text == "📋 Список заданий")
async def show_tasks_list(message: Message):
    """Показать список заданий с инлайн кнопками - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        # ПРОВЕРКА РАБОЧЕГО ВРЕМЕНИ
        can_interact, error_message = db.can_user_interact(message.from_user.id)
        if not can_interact:
            await message.answer(
                error_message,
                reply_markup=tasks_menu_keyboard()
            )
            return
        tasks = db.get_active_tasks_for_user(message.from_user.id)
        if not tasks:
            await message.answer(
                "📭 На данный момент нет доступных заданий",
                reply_markup=tasks_menu_keyboard()
            )
            return
        # Формируем текст как на скриншоте
        text = "🎯 Доступные задания\n"
        text += "💡 Выберите задание для просмотра деталей:\n"
        # Добавляем информацию о каждом задании
        for task in tasks:
            task_id, title, price, description, instruction, link, max_completions, current_completions, is_active, created_at = task
            text += f"• **{title}** — {price} руб.\n"
            if description:
                text += f"  📝 {description}\n"
            text += f"  👥 Выполнено: {current_completions}/{max_completions}\n"
        text += "⬇️ **Выберите задание ниже:**"
        # Отправляем сообщение с inline-клавиатурой
        await message.answer(
            text=text,
            reply_markup=tasks_keyboard(tasks)
        )
    except Exception as e:
        logger.error(f"Error in show_tasks_list: {e}")
        await message.answer("❌ Ошибка при загрузке списка заданий")

@router.message(F.text == "🔄 Обновить список")
async def refresh_tasks_list(message: Message):
    """Обновление списка заданий"""
    try:
        # ПРОВЕРКА РАБОЧЕГО ВРЕМЕНИ
        can_interact, error_message = db.can_user_interact(message.from_user.id)
        if not can_interact:
            await message.answer(
                error_message,
                reply_markup=tasks_menu_keyboard()
            )
            return
        await message.answer("🔄 Обновляем список заданий...")
        await show_tasks_menu(message)
    except Exception as e:
        logger.error(f"Error in refresh_tasks_list: {e}")
        await message.answer("❌ Ошибка при обновлении")

@router.message(F.text == "🔙 Главное меню")
async def back_to_main_from_tasks(message: Message, state: FSMContext):
    """Возврат в главное меню из меню заданий"""
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard(message.from_user.id)
    )

# ===== ЛИЧНЫЙ КАБИНЕТ =====
@router.message(F.text == "📊 Личный кабинет")
async def personal_account(message: Message):
    local_db = Database()
    try:
        user_data = local_db.get_user(message.from_user.id)
        if user_data:
            user_id = user_data[0]
            balance = user_data[2] if len(user_data) > 2 else 0.0
            total_earned = user_data[3] if len(user_data) > 3 else 0.0
            registered_at = user_data[7] if len(user_data) > 7 else "Неизвестно"
            pending_tasks = local_db.get_user_pending_tasks(user_id)
            pending_tasks_count = len(pending_tasks)

            if registered_at != "Неизвестно":
                try:
                    registered_at = registered_at.split()[0]
                except:
                    pass

            text = f"""👤 Ваш личный кабинет:
💰 Баланс: {balance:.2f} руб.
⏳ Заданий на проверке: {pending_tasks_count}
📊 Всего заработано: {total_earned:.2f} руб.
📅 Дата регистрации: {registered_at}"""
            await message.answer(text, reply_markup=main_menu_keyboard(user_id))
        else:
            await message.answer("❌ Пользователь не найден.")
    except Exception as e:
        logger.error(f"Error in account: {e}")
        await message.answer("❌ Ошибка.")
    finally:
        local_db.close()
        
# ===== РЕФЕРАЛЬНАЯ СИСТЕМА =====
@router.message(F.text == "👥 Реферальная система")
async def referral_system(message: Message):
    local_db = Database()
    try:
        user_data = local_db.get_user(message.from_user.id)
        if user_data:
            user_id = user_data[0]
            actual_ref_count = local_db.get_actual_ref_count(user_id)
            bot_username = (await message.bot.get_me()).username
            text = f"""
👥 Реферальная система
👤 Приглашено друзей: {actual_ref_count}
💰 Заработано с рефералов: {user_data[5]:.2f} руб.
🔗 Ваши реферальные ссылки:
Основная ссылка:
`https://t.me/{bot_username}?start={user_id}`
Альтернативная ссылка:
`https://t.me/{bot_username}?start=ref_{user_id}`
Простая команда:
`/start {user_id}`
💡 Как работает система:
• Приглашайте друзей по любой из ваших ссылок
• Когда ваш реферал выводит средства, вы получаете 10% от суммы его вывода
• Бонусы автоматически начисляются на ваш баланс
• В личном кабинете отображается общий заработок с рефералов
🎁 Пример: если ваш реферал выводит 1000 руб., вы получаете 100 руб. на баланс!
📊 Ваши рефералы: {actual_ref_count} человек
"""
            await message.answer(text)
    except Exception as e:
        logger.error(f"Error in referral: {e}")
        await message.answer("❌ Ошибка.")
    finally:
        local_db.close()
        
# ===== СИСТЕМА ВЫВОДА СРЕДСТВ =====
@router.message(F.text == "💳 Вывести средства")
async def withdraw_funds(message: Message, state: FSMContext):
    local_db = Database()
    try:
        user_data = local_db.get_user(message.from_user.id)
        if not user_data:
            await message.answer("❌ Пользователь не найден")
            return
        balance = user_data[2]
        if balance < MIN_WITHDRAWAL:
            await message.answer(f"❌ Минимальная сумма: {MIN_WITHDRAWAL} руб.")
            return
        await message.answer(f"💰 Ваш баланс: {balance:.2f} руб.\nВведите сумму...")
        await state.set_state(WithdrawalStates.waiting_for_amount)
    except Exception as e:
        logger.error(f"Error in withdraw: {e}")
        await message.answer("❌ Ошибка.")
    finally:
        local_db.close()

@router.message(WithdrawalStates.waiting_for_amount)
async def receive_withdrawal_amount(message: Message, state: FSMContext):
    """Получение суммы вывода"""
    try:
        amount = float(message.text)
        user_data = db.get_user(message.from_user.id)
        balance = user_data[2]
        if amount < MIN_WITHDRAWAL:
            await message.answer(f"❌ Минимальная сумма для вывода: {MIN_WITHDRAWAL} руб.")
            return
        if amount > balance:
            await message.answer("❌ Недостаточно средств на балансе")
            return
        await state.update_data(amount=amount)
        await message.answer(
            "🏦 Введите название банка для перевода:\n"
            "Например: Сбербанк, Тинькофф, ВТБ, Альфа-Банк и т.д."
        )
        await state.set_state(WithdrawalStates.waiting_for_bank)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")

@router.message(WithdrawalStates.waiting_for_bank)
async def receive_bank_name(message: Message, state: FSMContext):
    """Получение названия банка"""
    bank_name = message.text.strip()
    if len(bank_name) < 2:
        await message.answer("❌ Пожалуйста, введите корректное название банка")
        return
    await state.update_data(bank_name=bank_name)
    await message.answer(
        "💳 Выберите способ получения средств:",
        reply_markup=payment_method_keyboard()
    )
    await state.set_state(WithdrawalStates.waiting_for_payment_method)

@router.message(WithdrawalStates.waiting_for_payment_method, F.text == "💳 Номер карты")
async def select_card_method(message: Message, state: FSMContext):
    """Выбран вывод на карту"""
    await state.update_data(payment_method="card")
    await message.answer(
        "💳 Введите номер банковской карты:\n"
        "Пример: 2200 1234 5678 9012\n"
        "⚠️ Убедитесь, что карта принадлежит указанному вами банку!",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отменить вывод")]],
            resize_keyboard=True
        )
    )
    await state.set_state(WithdrawalStates.waiting_for_card_number)

@router.message(WithdrawalStates.waiting_for_payment_method, F.text == "📱 Номер телефона")
async def select_phone_method(message: Message, state: FSMContext):
    """Выбран вывод на номер телефона"""
    await state.update_data(payment_method="phone")
    await message.answer(
        "📱 Введите номер телефона для перевода:\n"
        "Пример: +79123456789 или 89123456789\n"
        "⚠️ Убедитесь, что номер зарегистрирован в указанном вами банку!",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отменить вывод")]],
            resize_keyboard=True
        )
    )
    await state.set_state(WithdrawalStates.waiting_for_phone_number)

@router.message(WithdrawalStates.waiting_for_card_number)
async def receive_card_number(message: Message, state: FSMContext):
    """Получение номера карты"""
    card_number = message.text.strip()
    # Убираем пробелы для проверки
    clean_card_number = card_number.replace(" ", "")
    if len(clean_card_number) < 16 or not clean_card_number.isdigit():
        await message.answer("❌ Пожалуйста, введите корректный номер карты (16 цифр)")
        return
    await state.update_data(card_number=card_number)
    await message.answer(
        "👤 Введите имя и фамилию владельца карты:\n"
        "Пример: Иванов Иван\n"
        "⚠️ Убедитесь, что имя совпадает с данными в банковской системе!"
    )
    await state.set_state(WithdrawalStates.waiting_for_recipient_name)

@router.message(WithdrawalStates.waiting_for_phone_number)
async def receive_phone_number(message: Message, state: FSMContext):
    """Получение номера телефона"""
    phone_number = message.text.strip()
    # Очищаем номер от лишних символов
    clean_phone = phone_number.replace("+", "").replace(" ", "").replace("-", "")
    if len(clean_phone) < 10 or not clean_phone.isdigit():
        await message.answer("❌ Пожалуйста, введите корректный номер телефона")
        return
    await state.update_data(phone_number=phone_number)
    await message.answer(
        "👤 Введите имя и фамилие владельца телефона:\n"
        "Пример: Иванов Иван\n"
        "⚠️ Убедитесь, что имя совпадает с данми в банковской системе!"
    )
    await state.set_state(WithdrawalStates.waiting_for_recipient_name)

@router.message(WithdrawalStates.waiting_for_recipient_name)
async def receive_recipient_name(message: Message, state: FSMContext):
    """Получение имени получателя"""
    recipient_name = message.text.strip()
    if len(recipient_name) < 3:
        await message.answer("❌ Пожалуйста, введите корректное имя получателя")
        return
    await state.update_data(recipient_name=recipient_name)
    # Получаем все данные и показываем для подтверждения
    data = await state.get_data()
    # Формируем текст в зависимости от способа оплаты
    if data.get('payment_method') == 'card':
        payment_info = f"💳 Номер карты: {data['card_number']}"
    else:
        payment_info = f"📱 Номер телефона: {data['phone_number']}"
    confirmation_text = (
        "🔍 ПОЖАЛУЙСТА, ВНИМАТЕЛЬНО ПЕРЕПРОВЕРЬТЕ ВСЕ ДАННЫЕ:\n"
        f"💰 Сумма вывода: {data['amount']:.2f} руб.\n"
        f"🏦 Банк: {data['bank_name']}\n"
        f"{payment_info}\n"
        f"👤 Получатель: {data['recipient_name']}\n"
        "⚠️ ВНИМАНИЕ! ПЕРЕД ПОДТВЕРЖДЕНИЕМ ПРОВЕРЬТЕ:\n"
        "• Правильность названия банка\n"
        "• Корректность номера карты/телефона\n"
        "• Совпадение имени получателя с банковскими данными\n"
        "• После отправки заявки изменить данные будет невозможно!\n"
        "✅ Если все данные верны, подтвердите вывод:"
    )
    await message.answer(confirmation_text, reply_markup=confirmation_keyboard())
    await state.set_state(WithdrawalStates.waiting_for_confirmation)

@router.message(WithdrawalStates.waiting_for_confirmation, F.text == "✅ Всё верно, подтверждаю вывод")
async def confirm_withdrawal(message: Message, state: FSMContext):
    """Подтверждение вывода - ИСПРАВЛЕННАЯ ВЕРСИЯ (реферальный бонус перенесен в approve_withdrawal)"""
    try:
        data = await state.get_data()
        user_id = message.from_user.id
        # Проверяем баланс еще раз
        user_data = db.get_user(user_id)
        if not user_data or user_data[2] < data['amount']:
            await message.answer("❌ Недостаточно средств на балансе")
            await state.clear()
            return
        # Формируем банковские данные в зависимости от способа оплаты
        if data.get('payment_method') == 'card':
            payment_details = f"Карта: {data['card_number']}"
        else:
            payment_details = f"Телефон: {data['phone_number']}"
        bank_details = f"{data['bank_name']} | {payment_details} | {data['recipient_name']}"
        # Создаем заявку на вывод
        withdrawal_id = db.create_withdrawal_request(
            user_id=user_id,
            amount=data['amount'],
            bank_details=bank_details
        )
        # Списываем средства с баланса пользователя
        db.update_user_balance(user_id, -data['amount'])
        # Формируем информацию для пользователя
        if data.get('payment_method') == 'card':
            payment_info_user = f"💳 **Номер карты:** {data['card_number']}"
        else:
            payment_info_user = f"📱 **Номер телефона:** {data['phone_number']}"
        # Уведомляем пользователя
        success_text = (
            "✅ Заявка на вывод средств успешно создана!\n"
            f"💰 Сумма: {data['amount']:.2f} руб.\n"
            f"🏦 Банк: {data['bank_name']}\n"
            f"{payment_info_user}\n"
            f"👤 Получатель: {data['recipient_name']}\n"
            "⏳ Статус: Ожидает проверки администратором\n"
            "📅 Срок зачисления: до 24 часов\n"
            "Вы получите уведомление когда средства будут переведены."
        )
        await message.answer(success_text, reply_markup=main_menu_keyboard(user_id))
        await state.clear()
    except Exception as e:
        logger.error(f"Error in confirm_withdrawal: {e}")
        await message.answer("❌ Произошла ошибка при создании заявки.")

@router.message(WithdrawalStates.waiting_for_confirmation, F.text == "❌ Отменить вывод")
async def cancel_withdrawal(message: Message, state: FSMContext):
    """Отмена вывода"""
    await message.answer(
        "❌ Вывод средств отменен.",
        reply_markup=main_menu_keyboard(message.from_user.id)
    )
    await state.clear()

# ===== ОБРАБОТКА ЗАДАНИЙ =====
@router.message(F.text.startswith("🎯"))
async def handle_task_selection(message: Message, state: FSMContext):
    """Обработчик выбора задания из меню - ТОЛЬКО ОСНОВНАЯ ИНФОРМАЦИЯ"""
    try:
        # Извлекаем название задания из текста кнопки
        button_text = message.text
        task_title = button_text.replace("🎯 ", "").split(" - ")[0]
        # Находим задание в базе данных
        tasks = db.get_active_tasks_for_user(message.from_user.id)
        selected_task = None
        for task in tasks:
            if task[1] == task_title:  # task[1] - название задания
                selected_task = task
                break
        if not selected_task:
            await message.answer("❌ Задание не найдено или больше недоступно")
            return
        task_id, title, price, description, instruction, link, max_completions, current_completions, is_active, created_at = selected_task
        # ПОКАЗЫВАЕМ ТОЛЬКО ОСНОВНУЮ ИНФОРМАЦИЮ
        text = f"""
📝 Задание: {title}**
💰 Стоимость: {price:.2f} руб.
📄 Описание: {description}
💡 Нажмите кнопку ниже чтобы взять задание и увидеть полную инструкцию
        """
        await message.answer(
            text=text,
            reply_markup=task_detail_keyboard(task_id)
        )
    except Exception as e:
        logger.error(f"Error in handle_task_selection: {e}")
        await message.answer("❌ Ошибка при загрузке задания")

# ... (все импорты и классы остаются без изменений)

# ===== ОБРАБОТЧИКИ ЗАДАНИЙ =====

@router.message(F.text.startswith("✅ Взять задание #"))
async def take_task_from_button(message: Message, state: FSMContext):
    """Взятие задания через кнопку — обновлено под новую логику счётчика"""
    try:
        can_interact, error_message = db.can_user_interact(message.from_user.id)
        if not can_interact:
            await message.answer(
                error_message,
                reply_markup=main_menu_keyboard(message.from_user.id)
            )
            return

        task_id = int(message.text.split("#")[1])
        user_id = message.from_user.id

        active_task = db.get_user_active_task(user_id)
        if active_task:
            await message.answer("⚠️ У вас уже есть активное задание! Сначала выполните его.")
            return

        task = db.get_task(task_id)
        if not task:
            await message.answer("❌ Задание не найдено.")
            return

        # Проверка лимита выполнений НЕ нужна — она делается внутри assign_task_to_user
        if not db.can_user_take_task(user_id, task_id):
            await message.answer("❌ Вы уже брали это задание!")
            return

        # 🔥 В assign_task_to_user теперь сразу занимается слот (current_completions += 1)
        task_assigned = db.assign_task_to_user(user_id, task_id)

        if task_assigned:
            task_id, title, price, description, instruction, link, max_completions, current_completions, is_active, created_at = task
            text = f"""
🎯 **Вы взяли задание!**
📝 Задание: {title}
💰 Стоимость: {price:.2f} руб.
📄 Описание: {description}
📋 Инструкция: {instruction}
🔗 Ссылка: {link}
⏰ **У вас есть 15 минут на выполнение!**
📸 **Отправьте четкий скриншот подтверждения выполнения задания.**

💡 **Это задание больше недоступно другим пользователям.**
            """
            await message.answer(text)
            await message.answer(
                "📸 **Отправьте четкий скриншот подтверждения выполнения задания:**",
                reply_markup=cancel_keyboard()
            )
            await state.set_state(TaskStates.waiting_for_screenshot)
        else:
            await message.answer(
                "❌ Не удалось взять задание. Оно, вероятно, уже занято другим пользователем."
            )
    except Exception as e:
        logger.error(f"Error in take_task_from_button: {e}")
        await message.answer("❌ Ошибка при взятии задания")
        
@router.message(TaskStates.waiting_for_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    """Получение скриншота выполнения задания — счётчик уже учтён, просто отправляем на проверку"""
    try:
        can_interact, error_message = db.can_user_interact(message.from_user.id)
        if not can_interact:
            await message.answer(
                error_message,
                reply_markup=main_menu_keyboard(message.from_user.id)
            )
            await state.clear()
            return

        active_task = db.get_user_active_task(message.from_user.id)
        if not active_task:
            await message.answer(
                "❌ Активное задание не найдено",
                reply_markup=main_menu_keyboard(message.from_user.id)
            )
            await state.clear()
            return

        user_task_id = active_task[0]
        task_id = active_task[2]
        photo_id = message.photo[-1].file_id

        success = db.submit_task(user_task_id, photo_id)
        if success:
            task = db.get_task(task_id)
            task_title = task[1] if task else "Неизвестно"
            await message.answer(
                f"✅ Скриншот задания \"{task_title}\" отправлен на проверку!\n"
                "⏳ Ожидайте одобрения администратора.\n"
                "💡 **Теперь вы можете взять новое задание!**\n"
                "💼 Нажмите \"Приступить к работе\".",
                reply_markup=main_menu_keyboard(message.from_user.id)
            )
        else:
            await message.answer(
                "❌ Ошибка при отправке скриншота",
                reply_markup=main_menu_keyboard(message.from_user.id)
            )
        await state.clear()
    except Exception as e:
        logger.error(f"Error in receive_screenshot: {e}")
        await message.answer("❌ Произошла ошибка при отправке скриншота")
        await state.clear()
        
@router.message(Command("my_tasks"))
async def my_tasks_command(message: Message):
    """Показать статус заданий пользователя"""
    try:
        user_id = message.from_user.id
        # Активное задание (assigned)
        active_task = db.get_user_active_task(user_id)
        # Задания на проверке (submitted)
        pending_tasks = db.get_user_pending_tasks(user_id)
        text = "📊 Ваши задания:\n"
        if active_task:
            task = db.get_task(active_task[2])
            if task:
                text += f"🎯 **Активное задание:**\n"
                text += f"🏷 {task[1]}\n"
                text += f"💰 {task[2]} руб.\n"
                text += f"⏰ Взято: {active_task[5]}\n"
                text += f"📝 Статус: В процессе выполнения\n"
        if pending_tasks:
            text += f"⏳ **Задания на проверке:** {len(pending_tasks)}\n"
            for pending_task in pending_tasks[:3]:  # Показываем первые 3
                text += f"• {pending_task[8]} - отправлено {pending_task[6]}\n"
            text += "\n"
        if not active_task and not pending_tasks:
            text += "📭 У вас еще нет заданий\n"
            text += "💼 Нажмите \"Приступить к работе\" чтобы взять первое задание!"
        else:
            text += "💡 После отправки скриншота вы можете брать новые задания!"
        await message.answer(text)
    except Exception as e:
        logger.error(f"Error in my_tasks_command: {e}")
        await message.answer("❌ Ошибка при загрузке заданий")

@router.message(Command("debug_status"))
async def debug_status(message: Message):
    """Отладочная команда для проверки статуса"""
    try:
        user_id = message.from_user.id
        active_task = db.get_user_active_task(user_id)
        pending_tasks = db.get_user_pending_tasks(user_id)
        text = f"🔍 Статус пользователя {user_id}:\n"
        text += f"🎯 Активное задание (assigned): {'ЕСТЬ' if active_task else 'НЕТ'}\n"
        text += f"⏳ Заданий на проверке (submitted): {len(pending_tasks)}\n"
        if active_task:
            task = db.get_task(active_task[2])
            text += f"Активное задание: {task[1] if task else 'Не найдено'}\n"
        text += "\n💡 После отправки скриншота активное задание исчезает и можно брать новое!"
        await message.answer(text)
    except Exception as e:
        logger.error(f"Error in debug_status: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@router.message(TaskStates.waiting_for_screenshot)
async def handle_wrong_screenshot(message: Message):
    """Обработка некорректного ввода в состоянии ожидания скриншота"""
    await message.answer("❌ Пожалуйста, отправьте скриншот в виде изображения (фото)")

@router.callback_query(F.data == "back_to_tasks")
async def back_to_tasks_callback(callback: CallbackQuery):
    """Возврат к списку заданий"""
    try:
        # Получаем доступные задания
        tasks = db.get_active_tasks_for_user(callback.from_user.id)
        if not tasks:
            await callback.message.edit_text("📭 На данный момент нет доступных заданий для вас")
            return
        text = "📋 **Список доступных заданий:**\n"
        text += "💡 Выберите задание для просмотра деталей:\n"
        await callback.message.edit_text(text, reply_markup=tasks_keyboard(tasks))
    except Exception as e:
        logger.error(f"Error in back_to_tasks: {e}")
        await callback.answer("❌ Ошибка при загрузке заданий")

# ===== АДМИН-ПАНЕЛЬ =====
@router.message(F.text == "👨‍💼 Админ")
async def admin_panel(message: Message, state: FSMContext):
    """Админ-панель"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    await state.clear()
    await message.answer("👨‍💼 Админ-панель", reply_markup=admin_keyboard())

@router.message(F.text == "📝 Создать задание")
async def create_task_start(message: Message, state: FSMContext):
    """Начало создания задания"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    await message.answer("Введите название задания:")
    await state.set_state(AdminStates.waiting_for_task_title)

@router.message(AdminStates.waiting_for_task_title)
async def receive_task_title(message: Message, state: FSMContext):
    """Получение названия задания"""
    await state.update_data(title=message.text)
    await message.answer("Введите стоимость задания (в рублях):")
    await state.set_state(AdminStates.waiting_for_task_price)

@router.message(AdminStates.waiting_for_task_price)
async def receive_task_price(message: Message, state: FSMContext):
    """Получение стоимости задания"""
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("Введите описание задания:")
        await state.set_state(AdminStates.waiting_for_task_description)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")

@router.message(AdminStates.waiting_for_task_description)
async def receive_task_description(message: Message, state: FSMContext):
    """Получение описания задания"""
    await state.update_data(description=message.text)
    await message.answer("Введите инструкцию к заданию:")
    await state.set_state(AdminStates.waiting_for_task_instruction)

@router.message(AdminStates.waiting_for_task_instruction)
async def receive_task_instruction(message: Message, state: FSMContext):
    """Получение инструкции задания"""
    await state.update_data(instruction=message.text)
    await message.answer("Введите ссылку для задания:")
    await state.set_state(AdminStates.waiting_for_task_link)

@router.message(AdminStates.waiting_for_task_link)
async def receive_task_link(message: Message, state: FSMContext):
    """Получение ссылки задания"""
    await state.update_data(link=message.text)
    await message.answer("Введите максимальное количество выполнений задания:")
    await state.set_state(AdminStates.waiting_for_task_max_completions)

@router.message(AdminStates.waiting_for_task_max_completions)
async def receive_task_max_completions(message: Message, state: FSMContext):
    """Получение максимального количества выполнений"""
    try:
        max_completions = int(message.text)
        data = await state.get_data()
        # Создаем задание в базе данных
        task_id = db.create_task(
            title=data['title'],
            price=data['price'],
            description=data['description'],
            instruction=data['instruction'],
            link=data['link'],
            max_completions=max_completions
        )
        await message.answer(
            f"✅ Задание успешно создано!\n"
            f"🏷 Название: {data['title']}\n"
            f"💰 Стоимость: {data['price']} руб.\n"
            f"📄 Описание: {data['description']}\n"
            f"🔗 Ссылка: {data['link']}\n"
            f"👥 Максимум выполнений: {max_completions}\n"
            f"📋 ID задания: {task_id}",
            reply_markup=admin_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число")

@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    """Статистика для админа"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    try:
        # Получаем статистику
        all_users = db.get_all_users()
        all_tasks = db.get_all_tasks()
        pending_tasks = db.get_pending_tasks()
        pending_withdrawals = db.get_pending_withdrawals()
        total_users = len(all_users)
        total_tasks = len(all_tasks)
        total_pending_tasks = len(pending_tasks)
        total_pending_withdrawals = len(pending_withdrawals)
        # Считаем общий баланс всех пользователей
        total_balance = sum(user[2] for user in all_users)
        total_earned = sum(user[3] for user in all_users)
        text = f"""
📊 Статистика бота:
👥 Пользователей: {total_users}
📋 Заданий: {total_tasks}
⏳ Заданий на проверке: {total_pending_tasks}
💳 Выводов на проверке: {total_pending_withdrawals}
💰 Общий баланс: {total_balance:.2f} руб.
📈 Всего заработано: {total_earned:.2f} руб.
        """
        await message.answer(text)
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await message.answer("❌ Ошибка при загрузке статистики")

@router.message(F.text == "⏳ Задания на проверке")
async def admin_pending_tasks(message: Message):
    """Задания на проверке для админа — ИСПРАВЛЕНО (БЕЗ debug_check_all_pending_tasks)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    try:
        pending_tasks = db.get_pending_tasks()
        if not pending_tasks:
            await message.answer("📭 Нет заданий на проверке")
            return

        for task in pending_tasks:
            try:
                user_task_id, user_id, task_id, status, screenshot_file_id, submitted_at, username, title, price = task
                if screenshot_file_id and not screenshot_file_id.startswith('REASON:'):
                    await message.bot.send_photo(
                        chat_id=message.chat.id,
                        photo=screenshot_file_id,
                        caption=f"📸 Скриншот для задания \"{title}\"\n"
                                f"👤 Пользователь: @{username or 'без username'}",
                        reply_markup=task_review_keyboard(user_task_id)
                    )
                else:
                    await message.answer(
                        f"⚠️ Скриншот недоступен для задания \"{title}\"\n"
                        f"👤 Пользователь: @{username or 'без username'}",
                        reply_markup=task_review_keyboard(user_task_id)
                    )
            except Exception as e:
                logger.error(f"Ошибка при обработке задания {task}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in admin_pending_tasks: {e}")
        await message.answer(f"❌ Ошибка при загрузке заданий: {e}")
        
@router.message(F.text == "💳 Выводы на проверке")
async def admin_pending_withdrawals(message: Message):
    """Выводы на проверке для админа - ТОЛЬКО АКТИВНЫЕ ЗАЯВКИ"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    try:
        pending_withdrawals = db.get_pending_withdrawals()
        if not pending_withdrawals:
            await message.answer("📭 Нет выводов на проверке")
            return
        processed_count = 0
        for withdrawal in pending_withdrawals:
            try:
                # БЕЗОПАСНАЯ РАСПАКОВКА: используем индексы вместо распаковки
                withdrawal_id = withdrawal[0]
                user_id = withdrawal[1]
                amount = withdrawal[2]
                status = withdrawal[3]
                bank_details = withdrawal[4]
                created_at = withdrawal[5]
                processed_at = withdrawal[6]
                username = withdrawal[7] if len(withdrawal) > 7 else "неизвестно"
                # Проверяем, что статус действительно pending
                if status != 'pending':
                    continue
                # Обрабатываем случай, когда пользователь был удалён
                display_username = username if username is not None else "Пользователь удалён"
                withdrawal_text = f"""
💰 **Сумма:** {amount:.2f} руб.
👤 **Пользователь:** @{display_username} (ID: {user_id})
🏦 **Банковские данные:** {bank_details}
📅 **Дата:** {created_at}
📋 **ID вывода:** {withdrawal_id}
"""
                await message.answer(withdrawal_text, reply_markup=withdrawal_review_keyboard(withdrawal_id))
                processed_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка обработки вывода: {e}")
                logger.error(f"Данные вывода: {withdrawal}")
                continue
        # Если ни один вывод не был обработан
        if processed_count == 0:
            await message.answer("❌ Нет выводов со статусом 'pending' для отображения")
        else:
            await message.answer(f"✅ Показано выводов на проверке: {processed_count}")
    except Exception as e:
        logger.error(f"Error in admin_pending_withdrawals: {e}")
        await message.answer("❌ Ошибка при загрузке выводов")

# ===== НОВАЯ ФУНКЦИЯ: ИСТОРИЯ ВЫВОДОВ =====
@router.message(F.text == "📋 История выводов")
async def admin_withdrawal_history(message: Message):
    """История всех выводов средств — ИСПРАВЛЕНО"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    try:
        # ИСПОЛЬЗУЕМ МЕТОД БАЗЫ ДАННЫХ (он уже возвращает username из таблицы withdrawals)
        all_withdrawals = db.get_pending_withdrawals()  # ❌ НЕТ! Он только pending
        # ПРАВИЛЬНО: делаем запрос без JOIN, так как username уже в withdrawals

        db.cursor.execute('''
            SELECT withdrawal_id, user_id, amount, status, bank_details, 
                   created_at, processed_at, username
            FROM withdrawals
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        all_withdrawals = db.cursor.fetchall()

        if not all_withdrawals:
            await message.answer("📭 Нет заявок на вывод")
            return

        text = "📋 История выводов (последние 50):\n"
        for withdrawal in all_withdrawals:
            withdrawal_id, user_id, amount, status, bank_details, created_at, processed_at, username = withdrawal

            if status == 'approved':
                status_icon = "✅"
                status_text = "ОДОБРЕН"
            elif status == 'rejected':
                status_icon = "❌"
                status_text = "ОТКЛОНЕН"
            else:
                status_icon = "⏳"
                status_text = "НА ПРОВЕРКЕ"

            # Парсим банковские данные
            bank_parts = bank_details.split(' | ')
            bank_name = bank_parts[0] if len(bank_parts) > 0 else "Не указан"
            payment_info = bank_parts[1] if len(bank_parts) > 1 else "Не указано"
            recipient_name = bank_parts[2] if len(bank_parts) > 2 else "Не указано"

            text += f"{status_icon} **{status_text}** | {amount:.2f} руб.\n"
            text += f"👤 **Пользователь:** @{username or 'без username'} (ID: {user_id})\n"
            text += f"🏦 **Банк:** {bank_name}\n"
            text += f"💳 **Реквизиты:** {payment_info}\n"
            text += f"👤 **Получатель:** {recipient_name}\n"
            text += f"📅 **Дата заявки:** {created_at}\n"
            if processed_at:
                text += f"📅 **Дата обработки:** {processed_at}\n"
            text += f"📋 **ID вывода:** {withdrawal_id}\n"
            text += "─" * 40 + "\n"

            if len(text) > 3500:
                await message.answer(text, parse_mode="Markdown")
                text = ""

        if text:
            await message.answer(text, parse_mode="Markdown")

        # Статистика
        approved_count = len([w for w in all_withdrawals if w[3] == 'approved'])
        rejected_count = len([w for w in all_withdrawals if w[3] == 'rejected'])
        pending_count = len([w for w in all_withdrawals if w[3] == 'pending'])
        total_amount = sum(w[2] for w in all_withdrawals if w[3] == 'approved')

        stats_text = f"""
📊 **Статистика выводов:**
✅ Одобрено: {approved_count} на сумму {total_amount:.2f} руб.
❌ Отклонено: {rejected_count}
⏳ Ожидают: {pending_count}
📋 Всего заявок: {len(all_withdrawals)}
        """
        await message.answer(stats_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in admin_withdrawal_history: {e}")
        await message.answer("❌ Ошибка при загрузке истории выводов")
        
@router.message(F.text == "📋 Все задания")
async def admin_all_tasks(message: Message):
    """Показать все задания для админа с кнопками удаления"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    try:
        all_tasks = db.get_all_tasks()
        if not all_tasks:
            await message.answer("📭 Нет созданных заданий")
            return

        for task in all_tasks:
            task_id, title, price, description, instruction, link, max_completions, current_completions, is_active, created_at = task
            status = "✅ Активно" if is_active else "❌ Неактивно"
            task_text = (
                f"**Задание #{task_id}** | {status}\n"
                f"🏷 **Название:** {title}\n"
                f"💰 **Стоимость:** {price} руб.\n"
                f"📄 **Описание:** {description}\n"
                f"👥 **Выполнений:** {current_completions}/{max_completions}\n"
                f"📅 **Создано:** {created_at}\n"
                f"🔗 **Ссылка:** {link}"
            )
            # Клавиатура с кнопкой удаления
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="❌ Удалить задание",
                            callback_data=f"delete_task_{task_id}"
                        )
                    ]
                ]
            )
            await message.answer(task_text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in admin_all_tasks: {e}")
        await message.answer("❌ Ошибка при загрузке заданий")
        
@router.callback_query(F.data.startswith("delete_task_"))
async def delete_task_handler(callback: CallbackQuery):
    """Удаление задания навсегда"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа", show_alert=True)
        return

    try:
        task_id = int(callback.data.split("_")[-1])
        task = db.get_task(task_id)
        if not task:
            await callback.answer("❌ Задание не найдено", show_alert=True)
            return

        title = task[1]
        success = db.delete_task(task_id)
        if success:
            await callback.message.delete()  # Удаляем сообщение с заданием
            await callback.answer(f"✅ Задание \"{title}\" удалено!", show_alert=True)
        else:
            await callback.answer("❌ Ошибка при удалении задания", show_alert=True)
    except Exception as e:
        logger.error(f"Error in delete_task_handler: {e}")
        await callback.answer("❌ Критическая ошибка", show_alert=True)
        
@router.message(F.text == "👥 Балансы пользователей")
async def admin_user_balances(message: Message):
    """Показать балансы пользователей для админа"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    try:
        # Получаем всех пользователей
        all_users = db.get_all_users()
        if not all_users:
            await message.answer("📭 Нет пользователей")
            return
        # Сортируем по балансу (по убыванию)
        all_users_sorted = sorted(all_users, key=lambda x: x[2], reverse=True)
        text = "👥 Балансы пользователей:\n"
        for user in all_users_sorted[:20]:  # Показываем топ-20
            user_id, username, balance, total_earned, ref_count, ref_earned, invited_by, registered_at = user
            username_display = f"@{username}" if username else f"ID: {user_id}"
            text += f"**{username_display}**\n"
            text += f"💰 Баланс: `{balance:.2f}` руб.\n"
            text += f"📈 Всего заработано: {total_earned:.2f} руб.\n"
            text += f"👥 Рефералов: {ref_count}\n"
            text += f"📅 Регистрация: {registered_at}\n"
            # Добавляем кнопки для управления балансом
            await message.answer(
                text,
                reply_markup=user_management_keyboard(user_id)
            )
            text = ""  # Сбрасываем текст для следующего сообщения
        # Если пользователей больше 20, показываем общую статистику
        if len(all_users) > 20:
            total_balance = sum(user[2] for user in all_users)
            text += f"\n📊 Всего пользователей: {len(all_users)}"
            text += f"\n💰 Общий баланс: {total_balance:.2f} руб."
            await message.answer(text)
    except Exception as e:
        logger.error(f"Error in admin_user_balances: {e}")
        await message.answer("❌ Ошибка при загрузке балансов")

# ===== УПРАВЛЕНИЕ РЕФЕРАЛАМИ - ИСПРАВЛЕННЫЕ ОБРАБОТЧИКИ =====
@router.callback_query(F.data.startswith("manage_refs_"))
async def manage_refs_start(callback: CallbackQuery, state: FSMContext):
    """Начало управления рефералами пользователя - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    print(f"🎯 CALLBACK УПРАВЛЕНИЯ РЕФЕРАЛАМИ ПОЛУЧЕН: {callback.data}")
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        # Извлекаем ID пользователя из callback данных
        target_user_id = int(callback.data.split('_')[2])
        print(f"✅ Извлечен ID пользователя: {target_user_id}")
        # 🔥 ИСПРАВЛЕНИЕ: Синхронизируем счётчик перед отображением
        db.fix_ref_count(target_user_id)
        # Сохраняем в состоянии
        await state.update_data(managing_refs_user_id=target_user_id)
        # Получаем рефералов (реальные, из базы)
        referrals = db.get_actual_referrals(target_user_id)
        print(f"📊 Найдено рефералов: {len(referrals)}")
        if not referrals:
            await callback.message.edit_text(
                f"❌ У пользователя ID {target_user_id} нет рефералов.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_user_management")]
                ])
            )
            await callback.answer()
            return
        # Создаем текст и клавиатуру
        text = f"👥 Управление рефералами\n"
        text += f"👤 Пользователь: ID {target_user_id}\n"
        text += f"📊 Всего рефералов: {len(referrals)}\n"
        text += "🗑️ Выберите рефералов для удаления:"
        keyboard = referrals_management_keyboard(referrals)
        # Редактируем сообщение
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("✅ Список рефералов загружен")
        print(f"✅ Управление рефералами успешно показано")
    except Exception as e:
        print(f"❌ Ошибка в manage_refs_start: {e}")
        await callback.answer("❌ Ошибка при загрузке рефералов", show_alert=True)

@router.callback_query(F.data.startswith("select_ref_"))
async def select_ref_for_removal(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        ref_user_id = int(callback.data.split("_")[2])
        data = await state.get_data()
        managing_user_id = data.get('managing_refs_user_id')
        if not managing_user_id:
            await callback.answer("❌ Ошибка: неизвестный пользователь для управления рефералами.", show_alert=True)
            return
        # 🔥 ЗАМЕНА: delete_referral → unlink_referral
        success = db.unlink_referral(ref_user_id)
        if success:
            await callback.answer(f"✅ Реферал {ref_user_id} отвязан.")
            updated_referrals = db.get_actual_referrals(managing_user_id)
            if updated_referrals:
                text = f"👥 Управление рефералами пользователя ID: {managing_user_id}\n"
                text += f"📊 Всего рефералов: {len(updated_referrals)}\n"
                text += "Выберите рефералов для удаления:"
                await callback.message.edit_text(text, reply_markup=referrals_management_keyboard(updated_referrals))
            else:
                await callback.message.edit_text("✅ У этого пользователя больше нет рефералов.")
                back_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад к управлению пользователем", callback_data="back_to_user_management")]]
                )
                await callback.message.edit_reply_markup(reply_markup=back_keyboard)
        else:
            await callback.answer("❌ Не удалось отвязать реферала.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in select_ref_for_removal: {e}")
        await callback.answer("❌ Ошибка при отвязке реферала")

@router.callback_query(F.data == "remove_selected_refs")
async def remove_selected_refs(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        data = await state.get_data()
        managing_user_id = data.get('managing_refs_user_id')
        refs_to_remove = data.get('refs_to_remove', [])
        if not refs_to_remove:
            await callback.answer("❌ Не выбрано ни одного реферала для удаления.", show_alert=True)
            return
        success_count = 0
        for ref_id in refs_to_remove:
            # 🔥 ЗАМЕНА: delete_referral → unlink_referral
            if db.unlink_referral(ref_id):
                success_count += 1
        if success_count > 0:
            await callback.answer(f"✅ Отвязано {success_count} рефералов.")
            await state.update_data(refs_to_remove=[])
            updated_referrals = db.get_actual_referrals(managing_user_id)
            if updated_referrals:
                text = f"👥 Управление рефералами пользователя ID: {managing_user_id}\n"
                text += f"📊 Всего рефералов: {len(updated_referrals)}\n"
                text += "Выберите рефералов для удаления:"
                await callback.message.edit_text(text, reply_markup=referrals_management_keyboard(updated_referrals))
            else:
                await callback.message.edit_text("✅ У этого пользователя больше нет рефералов.")
                back_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад к управлению пользователем", callback_data="back_to_user_management")]]
                )
                await callback.message.edit_reply_markup(reply_markup=back_keyboard)
        else:
            await callback.answer("❌ Не удалось отвязать ни одного реферала.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in remove_selected_refs: {e}")
        await callback.answer("❌ Ошибка при отвязке рефералов")

@router.callback_query(F.data == "select_all_refs")
async def select_all_refs_for_removal(callback: CallbackQuery, state: FSMContext):
    """Выбор всех рефералов для удаления"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        data = await state.get_data()
        managing_user_id = data.get('managing_refs_user_id')
        if not managing_user_id:
            await callback.answer("❌ Ошибка: неизвестный пользователь для управления рефералами.", show_alert=True)
            return
        referrals = db.get_actual_referrals(managing_user_id)
        if not referrals:
            await callback.answer("❌ Нет рефералов для выбора.", show_alert=True)
            return
        # Сохраняем все ID рефералов для удаления
        ref_ids_to_remove = [ref[0] for ref in referrals]
        await state.update_data(refs_to_remove=ref_ids_to_remove)
        await callback.answer(f"✅ Выбраны все {len(ref_ids_to_remove)} рефералов для удаления.")
    except Exception as e:
        logger.error(f"Error in select_all_refs_for_removal: {e}")
        await callback.answer("❌ Ошибка при выборе всех рефералов")

@router.callback_query(F.data == "back_to_user_management")
async def back_to_user_management(callback: CallbackQuery, state: FSMContext):
    """Возврат к управлению пользователем"""
    print(f"🔙 CALLBACK ВОЗВРАТА К УПРАВЛЕНИЮ ПОЛЬЗОВАТЕЛЕМ")
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        data = await state.get_data()
        managing_user_id = data.get('managing_refs_user_id')
        if not managing_user_id:
            # Если ID неизвестен — возвращаем к общему списку
            await callback.message.edit_text("🔙 Возврат к списку пользователей...")
            await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_balances")]]
            ))
            return
        user_data = db.get_user(managing_user_id)
        if not user_data:
            await callback.message.edit_text("❌ Пользователь удалён или не найден.")
            await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_balances")]]
            ))
            return
        # 🔥 ИСПРАВЛЕНИЕ: используем актуальное число рефералов
        actual_ref_count = db.get_actual_ref_count(managing_user_id)
        user_id, username, balance, total_earned, _, ref_earned, _, registered_at = user_data
        text = f"👤 Управление пользователем:\n"
        text += f"🆔 ID: {user_id}\n"
        text += f"👤 Username: @{username or 'нет'}\n"
        text += f"💰 Баланс: {balance:.2f} руб.\n"
        text += f"👥 Рефералов: {actual_ref_count}\n"
        text += f"💸 Заработано с рефералов: {ref_earned:.2f} руб.\n"
        text += f"📅 Регистрация: {registered_at}"
        await callback.message.edit_text(text, reply_markup=user_management_keyboard(managing_user_id))
        await state.update_data(managing_refs_user_id=None, refs_to_remove=[])
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in back_to_user_management: {e}")
        await callback.answer("❌ Ошибка при возврате", show_alert=True)

# ===== ИСПРАВЛЕННЫЕ ОБРАБОТЧИКИ CALLBACK'ОВ =====
@router.callback_query(F.data.startswith("approve_task_"))
async def approve_task_handler(callback: CallbackQuery):
    """Одобрение задания - ИСПРАВЛЕННАЯ ВЕРСИЯ с корректной обработкой лимита"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        user_task_id = int(callback.data.split("_")[-1])
        # Проверяем существование задания в БД
        task_info = db.get_user_task_info(user_task_id)
        if not task_info:
            await callback.answer("❌ Задание не найдено", show_alert=True)
            return
        user_id, task_title, price, task_id = task_info
        # 🔥 ИСПРАВЛЕНИЕ: Одобряем задание
        success = db.approve_task(user_task_id)
        if not success:
            # Проверяем, почему не удалось одобрить
            # Получаем актуальные данные задания
            task = db.get_task(task_id)
            if task:
                current_completions = task[7]
                max_completions = task[6]
                if current_completions >= max_completions:
                    # Лимит достигнут — это НЕ ошибка, а бизнес-логика
                    await callback.answer(
                        f"⚠️ Задание '{task_title}' уже достигло лимита ({current_completions}/{max_completions})",
                        show_alert=True
                    )
                else:
                    # Это реальная ошибка
                    await callback.answer("❌ Ошибка при одобрении задания", show_alert=True)
            else:
                await callback.answer("❌ Ошибка при одобрении задания", show_alert=True)
            return
        # Удаляем сообщение с кнопками
        await callback.message.delete()
        # Получаем обновленную информацию о задании
        updated_task = db.get_task(task_id)
        status_text = ""
        if updated_task:
            current_completions = updated_task[7]
            max_completions = updated_task[6]
            if current_completions >= max_completions:
                status_text = f"\n📊 Задание достигло лимита выполнений ({current_completions}/{max_completions}) и скрыто."
        # Отправляем подтверждение
        await callback.message.answer(
            f"✅ Задание одобрено!\n"
            f"🏷 Задание: {task_title}\n"
            f"💰 Начислено: {price:.2f} руб.\n"
            f"👤 Пользователь: ID {user_id}"
            f"{status_text}"
        )
        await callback.answer("✅ Задание одобрено!")
        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                chat_id=user_id,
                text=f"✅ Ваше задание \"{task_title}\" одобрено!\n"
                     f"💰 На ваш баланс начислено: {price:.2f} руб.\n"
                     f"💎 Теперь вы можете брать новые задания!"
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
    except Exception as e:
        logger.error(f"Error in approve_task: {e}")
        await callback.answer("❌ Критическая ошибка при одобрении", show_alert=True)

@router.callback_query(F.data.startswith("reject_task_"))
async def reject_task_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса отклонения задания - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        # ПРАВИЛЬНОЕ извлечение ID
        user_task_id = int(callback.data.split("_")[-1])
        # Сохраняем ID задания в состоянии
        await state.update_data(user_task_id=user_task_id)
        # УДАЛЯЕМ сообщение с кнопками сразу
        await callback.message.delete()
        # Запрашиваем причину отклонения
        await callback.message.answer(
            "📝 Укажите причину отклонения задания:\n"
            "Примеры:\n"
            "• Неверный скриншот\n" 
            "• Задание выполнено не полностью\n"
            "• Нарушение правил выполнения\n"
            "• Другая причина",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(AdminStates.waiting_for_reject_reason)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in reject_task_start: {e}")
        await callback.answer("❌ Ошибка при отклонении задания")

@router.message(AdminStates.waiting_for_reject_reason)
async def receive_reject_reason(message: Message, state: FSMContext):
    """Получение причины отклонения и выполнение отклонения"""
    try:
        reason = message.text.strip()
        if len(reason) < 3:
            await message.answer("❌ Пожалуйста, укажите развернутую причину отклонения (минимум 3 символа)")
            return
        # Получаем данные из состояния
        data = await state.get_data()
        user_task_id = data['user_task_id']
        # Получаем информацию о задании
        task_info = db.get_user_task_info(user_task_id)
        if not task_info:
            await message.answer("❌ Задание не найдено")
            await state.clear()
            return
        user_id, task_title, price, task_id = task_info

        # ❌ УДАЛЕН ОПАСНЫЙ ВЫЗОВ (он вызывал ошибку):
        # db.decrement_task_completions(task_id)

        # Отклоняем задание с причиной (внутри метода счетчик уже корректно уменьшается)
        success = db.reject_task_with_reason(user_task_id, reason)
        if not success:
            await message.answer("❌ Ошибка при отклонении задания")
            await state.clear()
            return

        # Уведомляем администратора об успехе
        await message.answer(
            f"✅ Задание отклонено!\n"
            f"🏷 Задание: {task_title}\n"
            f"📝 Причина: {reason}\n"
            f"👤 Пользователь: ID {user_id}\n"
            f"🔁 Слот задания освобожден",
            reply_markup=admin_keyboard()
        )

        # Уведомляем пользователя об отклонении
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=f"❌ Ваше задание \"{task_title}\" отклонено!\n"
                     f"📋 Причина отклонения: {reason}\n"
                     f"💡 Если у вас есть вопросы, обратитесь в поддержку."
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
            await message.answer("⚠️ Не удалось отправить уведомление пользователю")

        await state.clear()

    except Exception as e:
        logger.error(f"Error in receive_reject_reason: {e}")
        await message.answer("❌ Произошла ошибка")
        await state.clear()

@router.callback_query(F.data.startswith("approve_withdrawal_"))
async def approve_withdrawal(callback: CallbackQuery):
    """Одобрение вывода средств - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        withdrawal_id = int(callback.data.split("_")[-1])
        withdrawal = db.get_withdrawal(withdrawal_id)
        if not withdrawal:
            await callback.answer("❌ Вывод не найден")
            return
        # Безопасная распаковка
        withdrawal_id, user_id, amount, status, bank_details, created_at, processed_at, username = withdrawal
        # Обновляем статус вывода
        success = db.update_withdrawal_status(withdrawal_id, "approved")
        if not success:
            await callback.answer("❌ Ошибка при обновлении статуса")
            return
        # --- НАЧИСЛЕНИЕ РЕФЕРАЛЬНОГО БОНУСА ---
        user_data = db.get_user(user_id)
        if user_data:
            invited_by = user_data[6]  # invited_by из базы данных
            if invited_by and invited_by != user_id:
                ref_bonus = amount * 0.10  # 10% от суммы вывода
                # Обновляем баланс пригласившего
                db.update_user_balance(invited_by, ref_bonus)
                # Обновляем счетчик заработанного с рефералов
                db.update_ref_earned(invited_by, ref_bonus)
                # Обновляем общий заработок пригласившего
                db.update_total_earned(invited_by, ref_bonus)
                # Уведомляем пригласившего о начислении бонуса
                try:
                    await callback.bot.send_message(
                        chat_id=invited_by,
                        text=f"🎉 Ваш реферал вывел {amount:.2f} руб.! Вы получили реферальный бонус: {ref_bonus:.2f} руб."
                    )
                except Exception as e:
                    logger.error(f"Error notifying referrer about bonus: {e}")
        # УДАЛЯЕМ сообщение с кнопками после одобрения
        await callback.message.delete()
        # Уведомляем пользователя о поступлении средств
        try:
            await callback.bot.send_message(
                chat_id=user_id,
                text=f"💸 Средства поступили на ваш кошелек!\n"
                     f"💰 Сумма: {amount:.2f} руб.\n"
                     f"🏦 Банковские реквизиты: {bank_details}\n"
                     f"📋 Номер заявки: {withdrawal_id}\n"
                     f"✅ Перевод успешно завершен!\n"
                     f"💳 Деньги уже должны быть на вашем счете.\n"
                     f"📞 Если возникли проблемы, обратитесь в поддержку."
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
        # Отправляем подтверждение администратору
        await callback.message.answer(
            f"✅ Вывод одобрен!\n"
            f"💰 Сумма: {amount:.2f} руб.\n"
            f"👤 Пользователь ID: {user_id}\n"
            f"🏦 Банковские данные: {bank_details}\n"
            f"📨 Пользователь уведомлен о поступлении средств."
        )
        await callback.answer("✅ Вывод одобрен!")
    except Exception as e:
        logger.error(f"Error in approve_withdrawal: {e}")
        await callback.answer("❌ Ошибка при одобрении вывода", show_alert=True)

@router.callback_query(F.data.startswith("reject_withdrawal_"))
async def reject_withdrawal_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса отклонения вывода - запрос причины"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        withdrawal_id = int(callback.data.split("_")[-1])
        withdrawal = db.get_withdrawal(withdrawal_id)
        if not withdrawal:
            await callback.answer("❌ Вывод не найден")
            return
        # Сохраняем данные в состоянии
        await state.update_data(
            withdrawal_id=withdrawal_id,
            withdrawal_data=withdrawal
        )
        # УДАЛЯЕМ сообщение с кнопками
        await callback.message.delete()
        # Запрашиваем причину отклонения
        await callback.message.answer(
            "📝 Укажите причину отклонения вывода:\n"
            "Примеры:\n"
            "• Неверные банковские реквизиты\n"
            "• Подозрительная активность\n" 
            "• Нарушение правил системы\n"
            "• Другая причина",
            reply_markup=cancel_keyboard()
        )
        await state.set_state(AdminStates.waiting_for_withdrawal_reject_reason)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in reject_withdrawal_start: {e}")
        await callback.answer("❌ Ошибка при отклонении вывода")

@router.message(AdminStates.waiting_for_withdrawal_reject_reason)
async def receive_withdrawal_reject_reason(message: Message, state: FSMContext):
    """Получение причины отклонения вывода и выполнение отклонения"""
    try:
        reason = message.text.strip()
        if len(reason) < 3:
            await message.answer("❌ Пожалуйста, укажите развернутую причину отклонения (минимум 3 символа)")
            return
        # Получаем данные из состояния
        data = await state.get_data()
        withdrawal_id = data.get('withdrawal_id')
        withdrawal = data.get('withdrawal_data')
        if not withdrawal_id or not withdrawal:
            await message.answer("❌ Ошибка: данные вывода не найдены")
            await state.clear()
            return
        # Безопасная распаковка данных вывода
        withdrawal_id, user_id, amount, status, bank_details, created_at, processed_at, username = withdrawal
        # Возвращаем средства на баланс пользователя
        db.update_user_balance(user_id, amount)
        # Обновляем статус вывода
        db.update_withdrawal_status(withdrawal_id, "rejected")
        # Уведомляем администратора об успехе
        await message.answer(
            f"✅ Вывод отклонен!\n"
            f"💰 Сумма: {amount:.2f} руб.\n"
            f"👤 Пользователь ID: {user_id}\n"
            f"📝 Причина: {reason}\n"
            f"💸 Средства возвращены на баланс пользователя",
            reply_markup=admin_keyboard()
        )
        # Уведомляем пользователя об отклонении с причиной
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=f"❌ Ваш вывод на {amount:.2f} руб. отклонен!\n"
                     f"📋 Причина отклонения: {reason}\n"
                     f"💰 Сумма возвращена на ваш баланс.\n"
                     f"💡 Для уточнения причин обратитесь в поддержку."
            )
        except Exception as e:
            logger.error(f"Error notifying user: {e}")
            await message.answer("⚠️ Не удалось отправить уведомление пользователю")
        await state.clear()
    except Exception as e:
        logger.error(f"Error in receive_withdrawal_reject_reason: {e}")
        await message.answer("❌ Произошла ошибка при отклонении вывода")
        await state.clear()

# ===== УПРАВЛЕНИЕ РЕКЛАМОЙ =====
@router.message(F.text == "📢 Реклама")
async def ads_management(message: Message, state: FSMContext):
    """Управление рекламой"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к управлению рекламой")
        return
    await state.clear()
    await message.answer("📢 Управление рекламой", reply_markup=ads_management_keyboard())

@router.message(F.text == "📢 Создать рекламу")
async def create_ad_start(message: Message, state: FSMContext):
    """Начало создания закрепленной рекламы"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа")
        return
    await message.answer(
        "📝 Введите текст закрепленной рекламы:\n"
        "Пример: \"🎉 Присоединяйтесь к нашему каналу!\"\n"
        "Это сообщение будет закреплено вверху у всех пользователей.",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdStates.waiting_for_ad_text)

@router.message(AdStates.waiting_for_ad_text)
async def receive_ad_text(message: Message, state: FSMContext):
    """Получение текста рекламы"""
    ad_text = message.text.strip()
    if len(ad_text) < 5:
        await message.answer("❌ Текст рекламы должен содержать минимум 5 символов")
        return
    await state.update_data(ad_text=ad_text)
    await message.answer(
        "🔗 Теперь введите ссылку для рекламы:\n"
        "Примеры:\n"
        "• https://t.me/your_channel\n"
        "• https://t.me/your_bot\n"
        "• @username",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdStates.waiting_for_ad_link)

@router.message(AdStates.waiting_for_ad_link)
async def receive_ad_link(message: Message, state: FSMContext):
    """Получение ссылки для рекламы"""
    ad_link = message.text.strip()
    # Упрощенная проверка ссылки
    if len(ad_link) < 5:
        await message.answer("❌ Ссылка должна содержать минимум 5 символов")
        return
    # Форматируем ссылку если нужно
    if ad_link.startswith('@'):
        ad_link = f"https://t.me/{ad_link[1:]}"
    elif ad_link.startswith('t.me/'):
        ad_link = f"https://{ad_link}"
    await state.update_data(ad_link=ad_link)
    # Получаем данные
    data = await state.get_data()
    ad_text = data['ad_text']
    # Формируем предпросмотр рекламы
    preview_text = (
        "🔍 ПРЕДПРОСМОТР РЕКЛАМЫ\n"
        "📢 Закрепленное сообщение:\n"
        f"{ad_text}\n"
        f"🔗 Ссылка: {ad_link}\n"
        "✅ Это сообщение будет закреплено вверху у всех пользователей"
    )
    # Создаем клавиатуру подтверждения
    confirmation_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да, закрепить рекламу"), KeyboardButton(text="❌ Отменить")],
        ],
        resize_keyboard=True
    )
    await message.answer(preview_text, reply_markup=confirmation_keyboard)
    await state.set_state(AdStates.waiting_for_ad_confirmation)

@router.message(AdStates.waiting_for_ad_confirmation, F.text == "✅ Да, закрепить рекламу")
async def confirm_ad_creation(message: Message, state: FSMContext):
    """Подтверждение создания закрепленной рекламы"""
    try:
        data = await state.get_data()
        ad_text = data['ad_text']
        ad_link = data['ad_link']
        # Создаем рекламу в базе данных
        ad_id, result_message = db.create_pinned_ad(ad_text, ad_link, message.from_user.id)
        if not ad_id:
            await message.answer(f"❌ Ошибка при создании рекламы: {result_message}", reply_markup=ads_management_keyboard())
            await state.clear()
            return
        # Создаем кнопку для рекламы
        ad_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Перейти", url=ad_link)],
            ]
        )
        # Отправляем закрепленное сообщение всем пользователям
        user_ids = db.get_all_user_ids()
        total_users = len(user_ids)
        successful_pins = 0
        failed_pins = 0
        await message.answer(f"🔄 Рассылаю закрепленную рекламу для {total_users} пользователей...")
        for user_id in user_ids:
            try:
                # Отправляем сообщение и закрепляем его
                sent_message = await message.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 {ad_text}",
                    reply_markup=ad_keyboard
                )
                # Закрепляем сообщение
                await message.bot.pin_chat_message(
                    chat_id=user_id,
                    message_id=sent_message.message_id
                )
                successful_pins += 1
            except Exception as e:
                failed_pins += 1
                print(f"❌ Не удалось закрепить рекламу для пользователя {user_id}: {e}")
        # Сохраняем рекламу в историю
        db.save_advertisement(ad_text, ad_link, successful_pins)
        success_text = (
            f"✅ {result_message}\n"
            f"📊 Статистика:\n"
            f"• Всего пользователей: {total_users}\n"
            f"• Успешно закреплено: {successful_pins}\n"
            f"• Не удалось: {failed_pins}\n"
            f"📝 Текст: {ad_text}\n"
            f"🔗 Ссылка: {ad_link}"
        )
        await message.answer(success_text, reply_markup=ads_management_keyboard())
        await state.clear()
    except Exception as e:
        logger.error(f"Error creating pinned ad: {e}")
        await message.answer("❌ Ошибка при создании закрепленной рекламы", reply_markup=ads_management_keyboard())
        await state.clear()

@router.message(F.text == "📋 Список реклам")
async def show_ads_list(message: Message):
    """Показать статистику рекламы"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа")
        return
    try:
        # Получаем статистику рекламы
        ad_stats = db.get_ad_stats()
        # Получаем все рекламы
        all_ads = db.get_all_pinned_ads()
        text = "📋 **Управление рекламой**\n"
        if ad_stats:
            text += f"📊 **Статистика:**\n"
            text += f"• Всего реклам: {ad_stats.get('total_ads', 0)}\n"
            text += f"• Активных реклам: {ad_stats.get('active_ads', 0)}\n"
        if all_ads:
            text += "📝 **Список реклам:**\n"
            for ad in all_ads:
                ad_id, ad_text, ad_link, is_active, created_at, created_by, created_by_username = ad
                # Обрезаем длинный текст
                preview_text = ad_text[:50] + "..." if len(ad_text) > 50 else ad_text
                status = "✅ Активна" if is_active else "❌ Неактивна"
                text += f"📅 {created_at}\n"
                text += f"🆔 ID: {ad_id} | {status}\n"
                text += f"📝 {preview_text}\n"
                text += f"🔗 {ad_link}\n"
                if created_by_username:
                    text += f"👤 Создал: @{created_by_username}\n"
                text += "─" * 30 + "\n"
            await message.answer(text)
        else:
            await message.answer(
                "📭 Нет созданных реклам\n"
                "💡 Создайте первую закрепленную рекламу",
                reply_markup=ads_management_keyboard()
            )
    except Exception as e:
        logger.error(f"Error showing ads list: {e}")
        await message.answer("❌ Ошибка при загрузке списка реклам")

@router.message(F.text == "🗑️ Очистить рекламу")
async def clear_ads(message: Message):
    """Очистка закрепленных реклам у всех пользователей"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа")
        return
    try:
        user_ids = db.get_all_user_ids()
        total_users = len(user_ids)
        successful_unpins = 0
        failed_unpins = 0
        await message.answer(f"🔄 Очищаю закрепленные сообщения у {total_users} пользователей...")
        for user_id in user_ids:
            try:
                # Открепляем все сообщения у пользователя
                await message.bot.unpin_all_chat_messages(chat_id=user_id)
                successful_unpins += 1
            except Exception as e:
                failed_unpins += 1
                print(f"❌ Не удалось открепить сообщения у пользователя {user_id}: {e}")
        success_text = (
            "✅ Закрепленные сообщения очищены!\n"
            f"📊 Статистика:\n"
            f"• Всего пользователей: {total_users}\n"
            f"• Успешно очищено: {successful_unpins}\n"
            f"• Не удалось: {failed_unpins}"
        )
        await message.answer(success_text, reply_markup=ads_management_keyboard())
    except Exception as e:
        logger.error(f"Error clearing pinned ads: {e}")
        await message.answer("❌ Ошибка при очистке закрепленных сообщений")

# ===== ОБРАБОТЧИКИ ОТМЕНЫ ДЛЯ РЕКЛАМЫ =====
@router.message(AdStates.waiting_for_ad_text, F.text == "❌ Отменить")
@router.message(AdStates.waiting_for_ad_link, F.text == "❌ Отменить")
@router.message(AdStates.waiting_for_ad_confirmation, F.text == "❌ Отменить")
async def cancel_ad_creation(message: Message, state: FSMContext):
    """Отмена создания рекламы"""
    await message.answer("❌ Создание рекламы отменено", reply_markup=ads_management_keyboard())
    await state.clear()

# ===== ВСПОМОГАТЕЛЬНЫЕ ОБРАБОТЧИКИ =====
@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery):
    """Возврат в главное меню из callback"""
    await callback.message.edit_text("Возврат в главное меню")
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard(callback.from_user.id)
    )

@router.callback_query(F.data == "personal_cabinet")
async def personal_cabinet_callback(callback: CallbackQuery):
    """Переход в личный кабинет из callback"""
    await callback.answer()
    await personal_account(callback.message)

@router.message(F.text == "🆘 Поддержка")
async def support(message: Message):
    """Поддержка"""
    await message.answer("📞 По всем вопросам обращайтесь: @Vop_rosie_bot")

# Обработчик отмены вывода в разных состояниях
@router.message(
    WithdrawalStates.waiting_for_bank,
    WithdrawalStates.waiting_for_payment_method, 
    WithdrawalStates.waiting_for_card_number,
    WithdrawalStates.waiting_for_phone_number,
    WithdrawalStates.waiting_for_recipient_name,
    WithdrawalStates.waiting_for_confirmation,
    F.text == "❌ Отменить вывод"
)
async def cancel_withdrawal_any_state(message: Message, state: FSMContext):
    """Отмена вывода из любого состояния"""
    await message.answer(
        "❌ Вывод средств отменен.",
        reply_markup=main_menu_keyboard(message.from_user.id)
    )
    await state.clear()

@router.message(F.text == "❌ Отменить")
async def cancel_any_action(message: Message, state: FSMContext):
    """Отмена любого действия и возврат в главное меню"""
    current_state = await state.get_state()
    if current_state:
        await message.answer(
            "❌ Действие отменено.",
            reply_markup=main_menu_keyboard(message.from_user.id)
        )
        await state.clear()
    else:
        # Если нет активного состояния, просто показываем главное меню
        await message.answer(
            "Главное меню:",
            reply_markup=main_menu_keyboard(message.from_user.id)
        )

# Обработчик возврата в главное меню
@router.message(F.text == "🔙 В главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard(message.from_user.id)
    )

@router.callback_query(F.data.startswith("deduct_balance_"))
async def deduct_balance_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса списания средств"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ У вас нет доступа")
        return
    try:
        user_id = int(callback.data.split("_")[-1])
        # Получаем информацию о пользователе
        user_data = db.get_user(user_id)
        if not user_data:
            await callback.answer("❌ Пользователь не найден")
            return
        username = user_data[1] or "без username"
        balance = user_data[2]
        # Сохраняем данные в состоянии
        await state.update_data(
            target_user_id=user_id,
            target_username=username,
            target_balance=balance
        )
        # Удаляем старое сообщение
        await callback.message.delete()
        # Запрашиваем сумму списания
        await callback.message.answer(
            f"💸 Списание средств\n"
            f"👤 Пользователь: @{username} (ID: {user_id})\n"
            f"💰 Текущий баланс: {balance:.2f} руб.\n"
            f"💵 Введите сумму для списания:"
        )
        await state.set_state(AdminStates.waiting_for_deduct_amount)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in deduct_balance_start: {e}")
        await callback.answer("❌ Ошибка")

@router.message(AdminStates.waiting_for_deduct_amount)
async def receive_deduct_amount(message: Message, state: FSMContext):
    """Получение суммы для списания и подтверждение"""
    try:
        amount_str = message.text.strip()
        # Проверяем, что введено число
        try:
            amount = float(amount_str)
            if amount <= 0:
                await message.answer("❌ Сумма должна быть положительной.")
                return
            # Продолжение логики: запрос причины списания и т.д.
            await state.update_data(deduct_amount=amount)
            await message.answer("📝 Укажите причину списания:")
            await state.set_state(AdminStates.waiting_for_deduct_reason)
        except ValueError:
            await message.answer("❌ Некорректный формат суммы. Введите число.")
    except Exception as e:
        logger.error(f"Ошибка при списании средств: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        await state.clear()
        
@router.message(F.text == "📢 Рассылка")
async def start_broadcast(message: Message, state: FSMContext):
    """Начало рассылки — запрос текста"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    await message.answer(
        "📤 Отправьте текст рассылки всем пользователям бота.\n"
        "Вы можете использовать форматирование (жирный, курсив и т.д.)\n"
        "Для отмены нажмите «❌ Отменить».",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_broadcast_message)
    
@router.message(BroadcastStates.waiting_for_broadcast_message)
async def process_broadcast(message: Message, state: FSMContext):
    """Отправка рассылки всем пользователям"""
    if message.from_user.id != ADMIN_ID:
        return

    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("❌ Рассылка отменена.", reply_markup=admin_keyboard())
        return

    broadcast_text = message.text or message.caption
    if not broadcast_text:
        await message.answer("❌ Пожалуйста, отправьте текст рассылки.")
        return

    # Сохраняем рассылку в БД
    broadcast_id = db.create_broadcast(broadcast_text, message_type="notification", sent_by_admin_id=message.from_user.id)
    
    # Получаем всех пользователей
    user_ids = db.get_all_user_ids()
    total = len(user_ids)
    success = 0
    failed = 0

    await message.answer(f"📤 Начинаю рассылку {total} пользователям...")
    
    for user_id in user_ids:
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=broadcast_text,
                parse_mode=None  # или "HTML", если поддерживаете
            )
            success += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Не удалось отправить пользователю {user_id}: {e}")

    # Обновляем статистику в БД
    db.update_broadcast_stats(broadcast_id, success, failed)

    await message.answer(
        f"✅ Рассылка завершена!\n"
        f"📤 Отправлено: {success}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего пользователей: {total}",
        reply_markup=admin_keyboard()
    )
    await state.clear()