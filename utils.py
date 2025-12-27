"""
utils.py - Вспомогательные функции бота

Назначение:
- Общие функции, используемые в нескольких модулях
- Парсинг данных
- Валидация
- Форматирование

Принцип:
- Чистые функции (без side effects)
- Переиспользуемый код
- Логическое группирование
"""

import re
import logging
import time
from config import DEBUG_MODE, AX_ID_PATTERN, WMS_ID_PATTERN, MAX_IDS_PER_MESSAGE, BOT_START_TIME

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
# Основной логгер для ошибок и информации
# Не путать с дебаггером (debugger.py) для отладочных сообщений
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def debug_print(*args, **kwargs):
    """
    Простая функция печати для отладки
    
    Использование:
        - Для быстрой отладки в процессе разработки
        - Альтернатива полноценному дебаггеру
        - Управляется через DEBUG_MODE
    
    Примечание:
        В основном коде используем debug из debugger.py
        Эта функция для простых случаев
    """
    if DEBUG_MODE:
        print(*args, **kwargs)

def parse_supply_ids(text: str):
    """
    Парсинг ID AX и ID WMS из текста сообщения
    
    Args:
        text (str): текст сообщения для парсинга
    
    Returns:
        tuple: (ax_ids, wms_ids) - два списка найденных ID
    
    Алгоритм:
        1. Ищет ID AX по паттерну AX_ID_PATTERN
        2. Ищет ID WMS по паттерну WMS_ID_PATTERN
        3. Ограничивает количество MAX_IDS_PER_MESSAGE
        4. Возвращает кортеж списков
    
    Пример:
        text = "ID AX: ЗП-370751234, ID WMS: 0000123456"
        returns (['ЗП-370751234'], ['0000123456'])
    """
    # Поиск ID AX: "ЗП-37075" + 4 цифры
    ax_ids = re.findall(AX_ID_PATTERN, text)
    
    # Поиск ID WMS: "0000" + 6 цифр
    wms_ids = re.findall(WMS_ID_PATTERN, text)
    
    # Ограничение количества для защиты от переполнения
    if len(ax_ids) > MAX_IDS_PER_MESSAGE:
        ax_ids = ax_ids[:MAX_IDS_PER_MESSAGE]
    
    if len(wms_ids) > MAX_IDS_PER_MESSAGE:
        wms_ids = wms_ids[:MAX_IDS_PER_MESSAGE]
    
    return ax_ids, wms_ids

def format_ids_for_copy(ids: list, id_type: str) -> str:
    """
    Форматирование списка ID для удобного копирования
    
    Args:
        ids (list): список ID для форматирования
        id_type (str): тип ID ('ax' или 'wms')
    
    Returns:
        str: отформатированная строка в MarkdownV2
    
    Формат:
        ID AX для копирования (5 шт.):
        ```
        ЗП-370751234-
        ЗП-370751235-
        ...
        ```
    
    Особенности:
        - Каждый ID на новой строке
        - Добавляется дефис в конце каждой строки
        - Используется MarkdownV2 для форматирования в Telegram
        - Экранирование специальных символов для MarkdownV2
    """
    if not ids:
        return ""
    
    # Каждый ID на новой строке с дефисом
    result_text = '\n'.join([f"{id}-" for id in ids])
    
    # Форматирование в MarkdownV2
    return f"```\n{result_text}\n```"

def validate_chat_id(chat_id: int, target_chat_id: str) -> bool:
    """
    Проверка, что сообщение пришло из целевого чата
    
    Args:
        chat_id (int): ID чата из сообщения
        target_chat_id (str): целевой ID чата из конфигурации
    
    Returns:
        bool: True если чат совпадает, False если нет
    
    Примечание:
        - target_chat_id хранится как строка в .env
        - chat_id приходит как int из Telegram API
        - Приводим к строке для сравнения
    """
    return str(chat_id) == target_chat_id

def get_user_identifier(user) -> str:
    """
    Получение идентификатора пользователя для логирования
    
    Args:
        user: Объект пользователя из Telegram (User или None)
    
    Returns:
        str: Идентификатор в формате:
            - @username если есть username
            - id:123456789 если нет username
            - 'Unknown' если user отсутствует
    """
    if not user:
        return "Unknown"
    
    # Получние username
    if hasattr(user, 'username') and user.username:
        return f"@{user.username}"
    
    # Если нет username - используется ID
    if hasattr(user, 'id'):
        return f"id:{user.id}"
    
    # Если неожиданный формат
    return "Unknown"

def is_message_after_start(message_date: float) -> bool:
    """
    Проверяет, было ли сообщение отправлено ПОСЛЕ запуска бота
    
    Args:
        message_date: Unix timestamp даты сообщения
    
    Returns:
        bool: True если сообщение отправлено после запуска бота
    """
    # message_date - время отправки сообщения
    # BOT_START_TIME - время запуска бота
    # Добавляем 5 секунд буфера (на случай рассинхронизации часов)
    return message_date > (BOT_START_TIME - 5)

def format_timestamp(timestamp: float) -> str:
    """
    Форматирует timestamp в читаемый вид
    """
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))