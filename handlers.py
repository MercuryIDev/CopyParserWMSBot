"""
handlers.py - Модуль обработчиков сообщений и кнопок бота

Назначение:
- Обработка входящих сообщений
- Парсинг данных из сообщений
- Обработка нажатий кнопок
- Управление интерфейсом бота

Структура обработчиков:
1. handle_supply_message - парсинг сообщений с поставками
2. button_handler - обработка нажатий инлайн-кнопок
3. handle_user_reply_to_dispatcher - обработка реплаев
4. debug_all_messages - дебаг всех входящих сообщений

Порядок обработки (в bot.py):
1. Реплаи (самый приоритетный)
2. Текстовые сообщения
3. Нажатия кнопок
4. Дебаг всех сообщений (если включен)
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from config import CHAT_ID
from storage import storage
from utils import parse_supply_ids, format_ids_for_copy, validate_chat_id, logger, get_user_identifier, is_message_after_start, format_timestamp
from debugger import debug, MessageInfo, DebugCategory

async def handle_supply_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Основной обработчик сообщений с поставками
    
    Алгоритм:
        1. Проверяет, что сообщение из целевого чата
        2. Парсит ID AX и WMS из текста
        3. Если находит ID - создает кнопки
        4. Сохраняет данные в хранилище
    
    Особенности:
        - Работает только с текстовыми сообщениями
        - Пропускает команды (filters.TEXT & ~filters.COMMAND)
        - Проверяет CHAT_ID из конфигурации
    """
    try:
        message = update.message
        if not message or not message.text:
            return
        
        message_id = message.message_id
        
        # Начало секции обработки
        debug.section_start("HANDLE SUPPLY MESSAGE", message_id)
        
        # ===== ПРОВЕРКА СООБЩЕНИЙ ПОСЛЕ ЗАПУСКА БОТА =====
        message_date = message.date.timestamp()
        if not is_message_after_start(message_date):
            debug.info_msg(f"Message was sent BEFORE bot started - skipping")
            debug.info_msg(f"Message time: {format_timestamp(message_date)}")
            debug.section_end()
            return
        
        # Выполнение очистки устаревших данных
        cleaned_count = storage.cleanup_old_data()
        if cleaned_count > 0:
            debug.cleanup_info(cleaned_count, len(storage.store))
        
        # Проверка, что сообщение из целевого чата
        if not validate_chat_id(message.chat_id, CHAT_ID):
            debug.info_msg("Not target chat - skipping")
            debug.section_end()
            return
        
        message_text = message.text
        chat_id = message.chat_id
        
        # Логирование информации о сообщении
        debug.step(DebugCategory.MESSAGE, f"Processing message")
        user_identifier = get_user_identifier(message.from_user)
        debug.info_msg(f"From: {user_identifier}")
        
        # Парсинг ID из текста сообщения
        ax_ids, wms_ids = parse_supply_ids(message_text)
        debug.parsing_results(ax_ids, wms_ids)
        
        has_ax = len(ax_ids) > 0
        has_wms = len(wms_ids) > 0
        
        # Если нашли ID - создаем интерфейс
        if has_ax or has_wms:
            data_key = storage.generate_key(chat_id, message_id)
            
            # Создание инлайн-кнопки
            keyboard = []
            if has_ax:
                keyboard.append([InlineKeyboardButton("📋 Копировать ID AX", callback_data=f"copy_ax_{data_key}")])
            if has_wms:
                keyboard.append([InlineKeyboardButton("📋 Копировать ID WMS", callback_data=f"copy_wms_{data_key}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Формировка текста ответа
            status_text = ""
            if has_ax:
                status_text += f"📦 ID AX: {len(ax_ids)} шт.\n"
            if has_wms:
                status_text += f"📦 ID WMS: {len(wms_ids)} шт.\n"
            
            # Отправка сообщения с кнопками
            bot_message = await context.bot.send_message(
                chat_id=chat_id,
                text=status_text,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                reply_to_message_id=message_id
            )
            
            # Логирование создания интерфейса
            debug.ui_created(has_ax, has_wms, bot_message.message_id)
            
            # Сохранение данных в хранилище
            storage.store_data(data_key, {
                'ax_ids': ax_ids,
                'wms_ids': wms_ids,
                'current_bot_message_id': bot_message.message_id,
                'original_message_id': message_id,
                'original_message_from': message.from_user.first_name if message.from_user else 'Unknown'
            })
            
            debug.storage_action("STORED", data_key, {
                'ax_ids_count': len(ax_ids),
                'wms_ids_count': len(wms_ids),
                'bot_message_id': bot_message.message_id
            })
            
            debug.bot_action("MESSAGE_SENT", bot_message.message_id)
        
        else:
            debug.info_msg("No IDs found - skipping")
        
        debug.section_end()
        
    except Exception as e:
        debug.error_occurred("handle_supply_message", e)
        logger.error(f"Parser error: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик нажатий инлайн-кнопок
    
    Алгоритм:
        1. Пользователь нажимает кнопку "Копировать ID AX/WMS"
        2. Из callback_data извлекается ключ хранилища
        3. Данные извлекаются из хранилища
        4. Форматируются для копирования
        5. Сообщение с кнопками заменяется на результат
    
    Особенности:
        - callback_data содержит ключ хранилища
        - Данные проверяются на актуальность (TTL)
        - После нажатия кнопки они заменяются результатом
    """
    try:
        query = update.callback_query
        await query.answer()  # Обязательно подтверждаем нажатие
        
        # Извлечение ключа из callback_data
        callback_data = query.data
        
        if callback_data.startswith("copy_ax_"):
            data_key = callback_data.replace("copy_ax_", "")
            action = "ax"
        elif callback_data.startswith("copy_wms_"):
            data_key = callback_data.replace("copy_wms_", "")
            action = "wms"
        else:
            return
        
        # Извлечение ID сообщения из ключа для дебага
        try:
            message_id = int(data_key.split('_')[1])
        except (IndexError, ValueError):
            message_id = None
        
        # Начало секции обработки
        debug.section_start("BUTTON HANDLER", message_id)
        
        # Очистка устаревших данных
        cleaned_count = storage.cleanup_old_data()
        if cleaned_count > 0:
            debug.cleanup_info(cleaned_count, len(storage.store))
        
        
        # Логирование информации о нажатии
        debug.button_action(callback_data, get_user_identifier(query.from_user))
        
        # Определение типа действия
        if action == "ax":
            debug.info_msg(f"Action: copy AX IDs")
        elif action == "wms":
            debug.info_msg(f"Action: copy WMS IDs")
        else:
            debug.info_msg("Unknown callback_data")
            debug.section_end()
            return
        
        # Извлечение данных из хранилища
        data = storage.get_data(data_key)
        if not data:
            debug.info_msg("Data not found in storage")
            await query.edit_message_text("Данные устарели или были очищены")
            debug.section_end()
            return
        
        ax_ids = data.get('ax_ids', [])
        wms_ids = data.get('wms_ids', [])
        
        debug.storage_action("RETRIEVED", data_key, {
            'ax_ids_count': len(ax_ids),
            'wms_ids_count': len(wms_ids)
        })
        
        # Форматирование результата для копирования
        response = ""
        if action == "ax" and ax_ids:
            response = format_ids_for_copy(ax_ids, "ax")
            debug.info_msg(f"Formatted {len(ax_ids)} AX IDs for copy")
        elif action == "wms" and wms_ids:
            response = format_ids_for_copy(wms_ids, "wms")
            debug.info_msg(f"Formatted {len(wms_ids)} WMS IDs for copy")
        else:
            response = "Данные не найдены"
            debug.info_msg("No data found for action")
        
        # Замена сообщения с кнопками на результат
        await query.edit_message_text(
            response,
            parse_mode='MarkdownV2'
        )
        
        debug.bot_action("MESSAGE_EDITED", query.message.message_id, "Replaced buttons with results")
        
        # Обновление ID сообщения бота в хранилище
        storage.update_bot_message_id(data_key, query.message.message_id)
        debug.storage_action("UPDATED", data_key, {'new_message_id': query.message.message_id})
        
        debug.section_end()
        
    except Exception as e:
        debug.error_occurred("button_handler", e)
        logger.error(f"Button handler error: {e}")

async def handle_user_reply_to_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик ответов пользователей на сообщения диспетчера
    
    Алгоритм:
        1. Пользователь отвечает на сообщение бота
        2. Бот удаляет своё сообщение с кнопками
        3. Очищает данные из хранилища
    
    Особенности:
        - Срабатывает только на реплаи (filters.REPLY)
        - Самый приоритетный обработчик
        - Удаляет только сообщения бота
    """
    try:
        message = update.message
        if not message or not message.reply_to_message:
            return
        
        # Получаем ID сообщения на которое ответили
        replied_message_id = message.reply_to_message.message_id
        
        # Начинаем секцию дебага
        debug.section_start("HANDLE USER REPLY", replied_message_id)
        
        chat_id = message.chat_id
        
        # Логируем информацию о реплае
        debug.step(DebugCategory.MESSAGE, f"User reply detected")
        user_identifier = get_user_identifier(message.from_user)
        debug.info_msg(f"User: {user_identifier}")
        debug.info_msg(f"Reply to message_id: {replied_message_id}")
        
        # Генерируем ключ для поиска в хранилище
        data_key = storage.generate_key(chat_id, replied_message_id)
        debug.storage_action("SEARCH", data_key)
        
        # Ищем данные бота для этого сообщения
        data = storage.get_data(data_key)
        
        if data:
            debug.storage_action("FOUND", data_key, data)
            current_bot_message_id = data.get('current_bot_message_id')
            
            if current_bot_message_id:
                try:
                    # Удаление сообщение бота
                    debug.bot_action("DELETE_MESSAGE", current_bot_message_id)
                    
                    await context.bot.delete_message(
                        chat_id=chat_id,
                        message_id=current_bot_message_id
                    )
                    
                    # Логирование успешного удаления
                    debug.info_msg(f"Message {current_bot_message_id} successfully deleted")
                    
                    # Очистка данных из хранилища
                    storage.delete_data(data_key)
                    debug.storage_action("DELETED", data_key)
                    
                except Exception as e:
                    # Логирование ошибки, но всё равно очищается хранилище для оптимизации
                    debug.error_occurred("delete_message", e)
                    storage.delete_data(data_key)
        else:
            debug.info_msg("Bot message not found for deletion")
        
        debug.section_end()
        
    except Exception as e:
        debug.error_occurred("handle_user_reply_to_dispatcher", e)
        logger.error(f"Error handling reply: {e}")

async def debug_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик для отладки всех входящих сообщений
    
    Назначение:
        - Логирование всех типов сообщений
        - Анализ структуры входящих данных
        - Отладка проблем с получением сообщений
    
    Включение/выключение:
        - Управляется через DEBUG_MODE в config.py
        - Добавляется в bot.py только если DEBUG_MODE = True
    """
    if not debug.enabled:
        return
    
    if update.message:
        message = update.message
        # Формировка структурированной информации о сообщении
        info = MessageInfo(
            message_id=message.message_id,
            chat_id=message.chat_id,
            from_user=get_user_identifier(message.from_user),
            is_bot=message.from_user.is_bot if message.from_user else False,
            text=message.text,
            is_reply=bool(message.reply_to_message),
            replied_to_user=message.reply_to_message.from_user.first_name if message.reply_to_message and message.reply_to_message.from_user else None,
            replied_to_bot=message.reply_to_message.from_user.is_bot if message.reply_to_message and message.reply_to_message.from_user else None,
            replied_message_id=message.reply_to_message.message_id if message.reply_to_message else None
        )
        
        # Начало секции дебага с ID сообщения
        debug.section_start("DEBUG ALL MESSAGES", info.message_id)
        debug.message_details(info)
        debug.section_end()