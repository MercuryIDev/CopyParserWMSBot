"""
config.py - Конфигурационный модуль бота

Назначение:
- Загрузка переменных окружения
- Хранение констант и настроек
- Валидация конфигурации

Использование:
- Все настройки бота хранятся здесь
- Изменение параметров только в этом файле
- .env файл для чувствительных данных (токены)
"""

import os
import time
import re  
from dotenv import load_dotenv


# ==================== ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ====================
load_dotenv()

# ==================== КОНФИГУРАЦИЯ БОТА ====================
PARSER_BOT_TOKEN = os.getenv('CopyParserWMSBot')
CHAT_ID = os.getenv('CHAT_ID')
CHAT_NAME = '[TEST] CopyParserWMSBot Sandbox'

# ==================== НАСТРОЙКИ ПАРСЕРА ====================
MAX_IDS_PER_MESSAGE = 100
DATA_CLEANUP_INTERVAL = 43200
DEBUG_MODE = True

# ==================== ВРЕМЯ ЗАПУСКА БОТА ====================
# Фиксирование тайминга запуска бота при импорте
BOT_START_TIME = time.time()

# ==================== РЕГУЛЯРНЫЕ ВЫРАЖЕНИЯ ====================
AX_ID_PATTERN = r'ID AX:\s*(ЗП-37075\d{4})'
WMS_ID_PATTERN = r'ID WMS:\s*(0000\d{6})'


# Скомпилированное регулярное выражение для номеров машин
CAR_NUM_PATTERN = re.compile(
    r'\b'  # граница слова
    r'([АВЕКМНОРСТУХABEKMHOPCTYX])'  # первая буква
    r'\s*'  # возможные пробелы
    r'(\d{3})'  # три цифры
    r'\s*'  # возможные пробелы
    r'([АВЕКМНОРСТУХABEKMHOPCTYX]{2})'  # две буквы
    r'\s*'  # возможные пробелы
    r'(\d{2,3})?'  # две или три цифры (опционально)
    r'\b',  # граница слова
    re.IGNORECASE | re.UNICODE  # игнорировать регистр и работать с юникодом
)

# ============== КОНВЕРТАЦИЯ ВРЕМЕНИ В ФОРМАТ ==============
def seconds_to_hhmm_extended(seconds):
    """Преобразует секунды в формат ЧЧ:ММ, где ЧЧ может быть больше 24"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

# ==================== ВАЛИДАЦИЯ КОНФИГУРАЦИИ ====================
def validate_config():
    """
    Проверка корректности загруженной конфигурации
    """
    if not PARSER_BOT_TOKEN or not CHAT_ID:
        print("    Ошибка: Не найдены переменные в .env файле")
        print(f"   PARSER_BOT_TOKEN: {'[OK]' if PARSER_BOT_TOKEN else '[ERROR]'}")
        print(f"   CHAT_ID: {'[OK]' if CHAT_ID else '[ERROR]'}")
        return False
    
    # Успешная загрузка конфигурации
    print(f"   CONFIG_LOADED: [OK]")
    print(f"   PARSER_BOT_TOKEN: [OK]")
    print(f"   CHAT_ID: {CHAT_ID}")
    print(f"   DEBUG_MODE: {DEBUG_MODE}")
    print(f"   BOT_START_TIME: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(BOT_START_TIME))}")
    print(f"   TTL: {(seconds_to_hhmm_extended(DATA_CLEANUP_INTERVAL))} h")
    return True