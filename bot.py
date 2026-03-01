"""
bot.py - Главный модуль запуска и конфигурации бота

Назначение:
- Точка входа в приложение
- Конфигурация и инициализация бота
- Регистрация обработчиков сообщений
- Управление жизненным циклом бота

Архитектура:
1. Настройка логирования
2. Валидация конфигурации
3. Создание экземпляра приложения
4. Регистрация обработчиков в правильном порядке
5. Запуск бота в режиме polling

Ключевые принципы:
- Минимальная логика в main() функции
- Четкое разделение ответственности
- Обработка ошибок на уровне приложения
- Конфигурируемость через config.py
"""

import logging
import time
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters
from config import PARSER_BOT_TOKEN, validate_config, DEBUG_MODE, BOT_START_TIME
from handlers import (
    debug_all_messages,
    handle_user_reply_to_dispatcher,
    handle_supply_message,
    button_handler
)
from debugger import debug

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
"""
Настройка системы логирования для всего приложения.

Почему это важно:
- Отслеживание работы бота в production
- Диагностика ошибок
- Мониторинг активности
- Отделение системных логов от пользовательских

Уровни логирования:
- ERROR: Критические ошибки
- WARNING: Предупреждения
- INFO: Информационные сообщения
- DEBUG: Детальная отладка (только при DEBUG_MODE)

Отключаем:
- httpx: HTTP запросы библиотеки Telegram
- telegram: внутренние логи python-telegram-bot
Эти логи слишком шумные для production.
"""

# Отключение шумных логов HTTP запросов
logging.getLogger("httpx").setLevel(logging.WARNING)

# Отключение внутренних логов python-telegram-bot
logging.getLogger("telegram").setLevel(logging.WARNING)

# Настройка основного логгера
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Создание логгера для этого модуля
logger = logging.getLogger(__name__)

def main():
    """
    Основная функция запуска бота
    
    Алгоритм работы:
        1. Валидация конфигурации
        2. Информирование о режиме отладки
        3. Создание экземпляра Application
        4. Регистрация обработчиков в правильном порядке
        5. Запуск бота в режиме long-polling
    """
    
    print("Starting parser bot...")
    print("=" * 50)
    
    # ==================== 1. ВАЛИДАЦИЯ КОНФИГУРАЦИИ ====================
    """
    Проверка обязательных параметров конфигурации.
    
    Что проверяется:
    - PARSER_BOT_TOKEN: Токен бота 
    - CHAT_ID: ID целевого чата 
    """
    if not validate_config():
        print("Configuration validation failed. Exiting...")
        exit(1)
    
    # ==================== 2. ИНФОРМИРОВАНИЕ О РЕЖИМЕ ОТЛАДКИ ====================
    """
    Информирование о текущем режиме работы.
    
    DEBUG_MODE влияет на:
    - Детальность вывода в консоль
    - Включение дополнительных обработчиков
    - Уровень детализации в дебаггере
    """
    if DEBUG_MODE:
        print("[DEBUG] Debug mode is ENABLED")
        print("[DEBUG] Detailed logging will be displayed")
    else:
        print("[DEBUG] Debug mode is DISABLED")
        print("[DEBUG] Only essential logs will be shown")
        
    # Важная информация о фильтрации сообщений
    print(f"\n[INFO] Bot will process messages sent AFTER:")
    print(f"[INFO] {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(BOT_START_TIME))}")
    print(f"[INFO] Messages before this time will be ignored")
    
    # ==================== 3. СОЗДАНИЕ ЭКЗЕМПЛЯРА ПРИЛОЖЕНИЯ ====================
    """
    Создание экземпляра Application - основного класса бота.
    
    Application:
    - Центральный класс python-telegram-bot
    - Управляет всеми обработчиками
    - Обрабатывает обновления от Telegram
    - Предоставляет контекст для обработчиков
    """
    try:
        application = Application.builder().token(PARSER_BOT_TOKEN).build()
        print("[OK] Application instance created successfully")
    except Exception as e:
        logger.error(f"Failed to create application: {e}")
        exit(1)
    
    # ==================== 4. РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ====================
    """
    Регистрация обработчиков в ПРАВИЛЬНОМ ПОРЯДКЕ.
    
    Порядок ВАЖЕН! Определяет приоритет обработки:
    
    1. РЕПЛАИ (САМЫЙ ВЫСОКИЙ ПРИОРИТЕТ)
       Почему: Если пользователь отвечает на сообщение бота,
       мы должны сначала удалить это сообщение, а не парсить его.
    
    2. ТЕКСТОВЫЕ СООБЩЕНИЯ (ОСНОВНАЯ ЛОГИКА)
       Почему: Основная функция бота - парсинг сообщений с поставками.
    
    3. НАЖАТИЯ КНОПОК (ИНТЕРАКТИВ)
       Почему: Обработка пользовательского взаимодействия с интерфейсом.
    
    4. ДЕБАГ ВСЕХ СООБЩЕНИЙ (САМЫЙ НИЗКИЙ ПРИОРИТЕТ)
       Почему: Только для отладки, не должен мешать основной логике.
       Добавляется только если DEBUG_MODE = True.
    """
    
    print("\n[REGISTERING HANDLERS]")
    print("-" * 30)
    
    # 4.1. ОБРАБОТЧИК РЕПЛАЕВ (ПРИОРИТЕТ 1)
    """
    Обработка ответов пользователей на сообщения бота.
    
    Условия срабатывания:
    - Сообщение является ответом (reply)
    - Сообщение содержит текст
    """
    application.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY, 
        handle_user_reply_to_dispatcher
    ))
    print("[OK] Reply handler registered (Priority 1)")
    
    # 4.2. ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (ПРИОРИТЕТ 2)
    """
    Основной парсинг сообщений с поставками.
    
    Условия срабатывания:
    - Текстовое сообщение
    - НЕ команда (чтобы бот не реагировал на /start и т.д.)
    """
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_supply_message
    ))
    print("[OK] Text message handler registered (Priority 2)")
    
    # 4.3. ОБРАБОТЧИК НАЖАТИЙ КНОПОК (ПРИОРИТЕТ 3)
    """
    Обработка интерактивных кнопок в сообщениях.
    
    Особенности:
    - CallbackQueryHandler для inline-кнопок
    - query.answer() обязателен для подтверждения нажатия
    """
    application.add_handler(CallbackQueryHandler(button_handler))
    print("[OK] Button handler registered (Priority 3)")
    
    # 4.4. ДЕБАГ-ОБРАБОТЧИК (ПРИОРИТЕТ 4 - ТОЛЬКО ЕСЛИ ВКЛЮЧЕН)
    """
    Детальная отладка всех входящих сообщений.
    
    Добавляется только при DEBUG_MODE = True
    Обрабатывает ВСЕ типы сообщений (filters.ALL)
    Самый низкий приоритет - не мешает основной логике
    """
    if DEBUG_MODE:
        application.add_handler(MessageHandler(
            filters.ALL, 
            debug_all_messages
        ))
        print("[OK] Debug handler registered (Priority 4)")
    else:
        print("[SKIP] Debug handler not registered (DEBUG_MODE = False)")
    
    print("-" * 30)
    print("[OK] All handlers registered successfully")
    
    # ==================== 5. ЗАПУСК БОТА ====================
    """
    Запуск бота в режиме long-polling.
    
    Режим polling:
    - Бот периодически опрашивает сервер Telegram на наличие обновлений
    - Простая настройка, не требует webhook
    
    Особенности:
    - run_polling() блокирует выполнение до остановки бота
    - Обработка KeyboardInterrupt для graceful shutdown
    """
    print("\n" + "=" * 50)
    print("Bot started successfully")
    print("=" * 50)
    print("\n[STATUS] Bot is running...")
    print("=" * 50)
    
    try:
        # Основной цикл работы бота
        application.run_polling()
        
    except KeyboardInterrupt:
        # Graceful shutdown при нажатии Ctrl+C
        print("\n" + "=" * 50)
        print("[INFO] Bot stopped by user (Ctrl+C)")
        print("[INFO] Performing cleanup...")
        print("=" * 50)
        
    except Exception as e:
        # Обработка неожиданных ошибок
        logger.error(f"Unexpected error in main loop: {e}")
        print(f"\nUnexpected error: {e}")
        print("[INFO] Bot stopped due to error")
        
    finally:
        # Финальные действия при остановке
        print("\n" + "=" * 50)
        print("[INFO] Bot shutdown")
        print("=" * 50)

# ==================== ТОЧКА ВХОДА ====================
"""
Стандартная точка входа Python приложения.

if __name__ == "__main__": гарантирует, что код
выполняется только при прямом запуске файла,
а не при импорте как модуля.
"""
if __name__ == "__main__":
    main()