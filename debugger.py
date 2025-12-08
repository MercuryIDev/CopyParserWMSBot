"""
debugger.py - Модуль для структурированной отладки бота

Назначение:
- Единый формат вывода отладочной информации
- Группировка логов по сообщениям
- Удобный поиск и анализ работы бота
- Визуальное структурирование с отступами

Формат вывода:
[ВРЕМЯ] [DEBUG] [ID:XXX] [КАТЕГОРИЯ]   Сообщение

Пример:
[14:30:15] [DEBUG] [ID:456] [PARSE] AX IDs found: 5
[14:30:15] [DEBUG] [ID:456] [PARSE]   AX IDs: ['ЗП-370751234', 'ЗП-370751235']

Особенности:
- Все выводы начинаются с [DEBUG]
- Автоматическая привязка к ID сообщения
- Иерархические отступы для вложенной информации
- Человекочитаемые временные форматы (2h 30m вместо секунд)
- Категоризация сообщений для фильтрации

Архитектура:
- DebugCategory: Enum категорий сообщений
- MessageInfo: dataclass для структурирования информации о сообщении
- DebugPrinter: основной класс с методами для разных типов отладки
- Глобальный экземпляр debug для использования во всех модулях
"""

import time
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from config import DEBUG_MODE, DATA_CLEANUP_INTERVAL

class DebugCategory(Enum):
    """
    Категории отладочных сообщений
    
    Назначение:
        - Классификация типов отладочной информации
        - Визуальное разделение в выводе
        - Возможность фильтрации по категориям
    
    Категории:
        MESSAGE  - Получение и базовая информация о сообщениях
        REPLY    - Обработка ответов (реплаев) на сообщения
        PARSE    - Парсинг данных из текста сообщений
        BUTTON   - Взаимодействие с инлайн-кнопками
        STORAGE  - Операции с временным хранилищем данных
        CLEANUP  - Очистка устаревших данных
        ERROR    - Ошибки и исключения
        INFO     - Общая информационная информация
        UI       - Создание и управление пользовательским интерфейсом
        BOT      - Действия бота (отправка, удаление, редактирование сообщений)
    """
    MESSAGE = "MESSAGE"        # Получение сообщения
    REPLY = "REPLY"            # Обработка реплая
    PARSE = "PARSE"            # Парсинг
    BUTTON = "BUTTON"          # Нажатие кнопки
    STORAGE = "STORAGE"        # Работа с хранилищем
    CLEANUP = "CLEANUP"        # Очистка данных
    ERROR = "ERROR"            # Ошибки
    INFO = "INFO"              # Информация
    UI = "UI"                  # Интерфейс (кнопки)
    BOT = "BOT"                # Действия бота

@dataclass
class MessageInfo:
    """
    Структура для хранения информации о сообщении
    
    Назначение:
        - Единый формат передачи данных о сообщении между модулями
        - Упрощение отладки и логирования
        - Изоляция логики работы с сообщениями
    
    Поля:
        message_id:         Уникальный идентификатор сообщения в Telegram
        chat_id:            Идентификатор чата
        from_user:          Имя отправителя (или "None" если недоступно)
        is_bot:             Отправлено ли сообщение ботом
        text:               Текст сообщения (первые 100 символов для превью)
        is_reply:           Является ли сообщение ответом на другое
        replied_to_user:    Имя пользователя, которому ответили
        replied_to_bot:     Является ли получатель ответа ботом
        replied_message_id: ID сообщения, на которое ответили
    """
    message_id: int
    chat_id: int
    from_user: str
    is_bot: bool
    text: Optional[str]
    is_reply: bool
    replied_to_user: Optional[str]
    replied_to_bot: Optional[bool]
    replied_message_id: Optional[int]

class DebugPrinter:
    """
    Основной класс для структурированного вывода отладочной информации
    
    Архитектура:
        - Singleton паттерн (один экземпляр на всё приложение)
        - Состояние: текущий ID сообщения, уровень отступа, счетчики
        - Методы для разных типов отладочной информации
        - Автоматическое управление форматированием
    
    Принцип работы:
        1. Устанавливается текущий ID сообщения
        2. Все последующие выводы помечаются этим ID
        3. Отступы автоматически увеличиваются/уменьшаются
        4. Время форматируется в читаемый вид
    
    Особенности:
        - enabled: управляется через DEBUG_MODE в config.py
        - current_message_id: привязка всех выводов к конкретному сообщению
        - indent: иерархические отступы для вложенной информации
    """
    
    def __init__(self, enabled: bool = DEBUG_MODE):
        """
        Инициализация дебаггера
        
        Args:
            enabled: Включен ли режим отладки (берется из DEBUG_MODE)
        
        Состояние:
            enabled:            Флаг активности дебаггера
            section_num:        Счетчик секций для нумерации
            step_counter:       Счетчики шагов внутри секций
            indent:             Текущий уровень отступа
            current_message_id: ID текущего обрабатываемого сообщения
        """
        self.enabled = enabled
        self.section_num = 0
        self.step_counter = {}
        self.indent = 0
        self.current_message_id = None
    
    def _print(self, category: DebugCategory, message: str):
        """
        Внутренний метод форматированного вывода
        
        Args:
            category: Категория сообщения (из DebugCategory)
            message:  Текст сообщения для вывода
        
        Форматирование:
            [ВРЕМЯ] [DEBUG] [ID:XXX] [КАТЕГОРИЯ]   Сообщение
            Пример: [14:30:15] [DEBUG] [ID:123] [PARSE] AX IDs found: 5
        
        Особенности:
            - Время в формате HH:MM:SS
            - ID сообщения добавляется только если установлен
            - Автоматические отступы на основе self.indent
            - Проверка enabled перед выводом
        """
        if not self.enabled:
            return
        
        # Форматирование времени
        timestamp = time.strftime('%H:%M:%S')
        
        # Форматирование отступов (2 пробела на уровень)
        indent_str = "  " * self.indent
        
        # Добавление ID сообщения если он установлен
        if self.current_message_id:
            id_prefix = f"[ID:{self.current_message_id}] "
        else:
            id_prefix = ""
        
        # Вывод сформированной строки
        print(f"[{timestamp}] [DEBUG] {id_prefix}[{category.value}] {indent_str}{message}")
    
    def set_message_id(self, message_id: Optional[int]):
        """
        Установить текущий ID сообщения для всех последующих выводов
        
        Args:
            message_id: ID сообщения или None для очистки
        
        Назначение:
            - Привязка всех последующих отладочных сообщений к конкретному сообщению
            - Используется при начале обработки нового сообщения
            - Автоматически добавляется ко всем вызовам _print()
        """
        self.current_message_id = message_id
    
    def clear_message_id(self):
        """
        Очистить текущий ID сообщения
        
        Назначение:
            - Сброс привязки к сообщению
            - Используется при завершении обработки сообщения
            - Предотвращает "залипание" ID в последующих вызовах
        """
        self.current_message_id = None
    
    def section_start(self, name: str, message_id: Optional[int] = None):
        """
        Начало новой секции отладки с визуальным разделителем
        
        Args:
            name: Название секции (например, "HANDLE SUPPLY MESSAGE")
            message_id: ID сообщения для привязки секции (опционально)
        
        Действия:
            1. Увеличивает счетчик секций
            2. Сбрасывает счетчик шагов для этой секции
            3. Устанавливает message_id если передан
            4. Выводит визуальный разделитель с названием секции
        
        Использование:
            debug.section_start("BUTTON HANDLER", message_id=123)
        """
        if not self.enabled:
            return
        
        self.section_num += 1
        self.step_counter[name] = 1
        self.indent = 0
        
        # Устанавливаем ID сообщения для секции
        if message_id:
            self.current_message_id = message_id
        
        # Визуальное разделение секций
        print(f"\n{'='*70}")
        
        if self.current_message_id:
            print(f"[DEBUG] [ID:{self.current_message_id}] SECTION: {name}")
        else:
            print(f"[DEBUG] SECTION: {name}")
        
        print(f"{'='*70}")
    
    def section_end(self):
        """
        Завершение текущей секции отладки
        
        Действия:
            1. Очищает ID сообщения
            2. Выводит разделитель конца секции
            3. Сбрасывает состояние для следующей секции
        
        Важно:
            Всегда должен вызываться после section_start
            для корректного завершения секции
        """
        if not self.enabled:
            return
        
        # Очищаем ID сообщения после завершения секции
        self.clear_message_id()
        print(f"[DEBUG] SECTION END")
        print(f"{'='*70}\n")
    
    def step(self, category: DebugCategory, message: str):
        """
        Вывод шага отладки в текущей секции
        
        Args:
            category: Категория шага
            message:  Текст шага
        
        Особенности:
            - Базовый метод для вывода отладочной информации
            - Использует текущие настройки форматирования
            - Не управляет нумерацией шагов (для этого есть специализированные методы)
        """
        self._print(category, message)
    
    def indent_increase(self):
        """
        Увеличить уровень отступа
        
        Назначение:
            - Создание иерархической структуры вывода
            - Визуальное выделение вложенной информации
            - Используется перед выводом деталей
        
        Пример:
            debug.step(DebugCategory.STORAGE, "Storage operation:")
            debug.indent_increase()
            debug.step(DebugCategory.STORAGE, "key: chat_id_message_id")
            debug.step(DebugCategory.STORAGE, "data_count: 5")
            debug.indent_decrease()
        """
        self.indent += 1
    
    def indent_decrease(self):
        """
        Уменьшить уровень отступа
        
        Назначение:
            - Возврат к предыдущему уровню иерархии
            - Завершение блока вложенной информации
            - Всегда должен соответствовать indent_increase
        
        Важно:
            Не уменьшает отступ ниже 0
            Для каждого indent_increase должен быть соответствующий indent_decrease
        """
        if self.indent > 0:
            self.indent -= 1
    
    def message_details(self, info: MessageInfo):
        """
        Вывод детальной информации о сообщении
        
        Args:
            info: Объект MessageInfo с данными о сообщении
        
        Формат вывода:
            [MESSAGE] Message received:
              message_id: 123
              chat_id: -100123456789
              from_user: Username (бот: нет)
              text: Превив текста...
              is_reply: True/False
              [если реплай] replied_to: Username
              [если реплай] replied_message_id: 122
        
        Использование:
            После получения сообщения для его анализа
        """
        if not self.enabled:
            return
        
        # Установка ID текущего сообщения
        self.set_message_id(info.message_id)
        
        self._print(DebugCategory.MESSAGE, f"Message received:")
        self.indent_increase()
        
        # Базовая информация о сообщении
        self._print(DebugCategory.MESSAGE, f"message_id: {info.message_id}")
        self._print(DebugCategory.MESSAGE, f"chat_id: {info.chat_id}")
        self._print(DebugCategory.MESSAGE, f"from_user: {info.from_user}")
        self._print(DebugCategory.MESSAGE, f"is_bot: {info.is_bot}")
        
        # Текст сообщения (обрезанный для читаемости)
        if info.text:
            text_preview = info.text[:100] + "..." if len(info.text) > 100 else info.text
            self._print(DebugCategory.MESSAGE, f"text: {text_preview}")
        
        # Информация о реплае
        if info.is_reply:
            self._print(DebugCategory.MESSAGE, f"is_reply: True")
            self._print(DebugCategory.MESSAGE, f"replied_to: {info.replied_to_user}")
            self._print(DebugCategory.MESSAGE, f"replied_to_bot: {info.replied_to_bot}")
            self._print(DebugCategory.MESSAGE, f"replied_message_id: {info.replied_message_id}")
        else:
            self._print(DebugCategory.MESSAGE, f"is_reply: False")
        
        self.indent_decrease()
    
    def _format_timestamp(self, timestamp: float) -> str:
        """
        Внутренний метод форматирования временной метки
        
        Args:
            timestamp: Временная метка в секундах (time.time())
        
        Returns:
            str: Человекочитаемое представление возраста
        
        Форматы:
            - Меньше минуты: "15s ago"
            - Меньше часа: "5m 30s ago"
            - Меньше дня: "2h 15m ago"
            - Больше дня: "1d 5h ago"
            - timestamp = 0: "not set"
        
        Используется для:
            - Отображения возраста данных в хранилище
            - Дебага TTL механизма
        """
        if timestamp == 0:
            return "not set"
        
        current_time = time.time()
        age_seconds = current_time - timestamp
        
        # Если меньше минуты
        if age_seconds < 60:
            return f"{int(age_seconds)}s ago"
        
        # Если меньше часа
        elif age_seconds < 3600:
            minutes = int(age_seconds // 60)
            seconds = int(age_seconds % 60)
            return f"{minutes}m {seconds}s ago"
        
        # Если меньше дня
        elif age_seconds < 86400:
            hours = int(age_seconds // 3600)
            minutes = int((age_seconds % 3600) // 60)
            return f"{hours}h {minutes}m ago"
        
        # Больше дня
        else:
            days = int(age_seconds // 86400)
            hours = int((age_seconds % 86400) // 3600)
            return f"{days}d {hours}h ago"
    
    def _format_ttl(self, seconds: int) -> str:
        """
        Внутренний метод форматирования TTL
        
        Args:
            seconds: Количество секунд
        
        Returns:
            str: Человекочитаемое представление времени
        
        Форматы:
            - Меньше минуты: "45s"
            - Меньше часа: "5m 30s"
            - Меньше дня: "2h 0m"
            - Больше дня: "1d 5h"
        
        Используется для:
            - Отображения TTL хранилища в дебаге
        """
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
    
    def storage_action(self, action: str, key: str, data: Optional[Dict] = None):
        """
        Вывод информации о действии с хранилищем
        
        Args:
            action: Тип действия ("SEARCH", "FOUND", "STORED", "RETRIEVED", "DELETED", "UPDATED")
            key:    Ключ в хранилище (формат: chat_id_message_id)
            data:   Данные из хранилища (опционально)
        
        Формат вывода:
            [STORAGE] Storage ACTION:
              key: chat_id_message_id
              [если data] ax_ids_count: 5
              [если data] wms_ids_count: 3
              [если data] age: 5m 30s ago
              [если data] TTL: 2h 0m
        
        Примеры действий:
            - SEARCH: Поиск данных по ключу
            - FOUND:  Данные найдены
            - STORED: Данные сохранены
            - RETRIEVED: Данные извлечены
            - DELETED: Данные удалены
            - UPDATED: Данные обновлены
        """
        if not self.enabled:
            return
        
        self._print(DebugCategory.STORAGE, f"Storage {action}:")
        self.indent_increase()
        self._print(DebugCategory.STORAGE, f"key: {key}")
        
        if data:
            # Количество найденных ID
            if 'ax_ids' in data:
                self._print(DebugCategory.STORAGE, f"ax_ids_count: {len(data['ax_ids'])}")
            if 'wms_ids' in data:
                self._print(DebugCategory.STORAGE, f"wms_ids_count: {len(data['wms_ids'])}")
            
            # Информация о времени
            if 'timestamp' in data:
                age = self._format_timestamp(data['timestamp'])
                self._print(DebugCategory.STORAGE, f"age: {age}")
                self._print(DebugCategory.STORAGE, f"TTL: {self._format_ttl(DATA_CLEANUP_INTERVAL)}")
        
        self.indent_decrease()
    
    def parsing_results(self, ax_ids: list, wms_ids: list):
        """
        Вывод результатов парсинга
        
        Args:
            ax_ids:  Список найденных ID AX
            wms_ids: Список найденных ID WMS
        
        Формат вывода:
            [PARSE] Parsing results:
              AX IDs found: 5
              AX IDs: ['ЗП-370751234', 'ЗП-370751235', ...]
              WMS IDs found: 3
              WMS IDs: ['0000123456', '0000123457', ...]
        
        Особенности:
            - Показывает количество найденных ID
            - Показывает первые 5 ID каждого типа (для компактности)
            - Добавляет "..." если ID больше 5
        """
        if not self.enabled:
            return
        
        self._print(DebugCategory.PARSE, f"Parsing results:")
        self.indent_increase()
        
        # ID AX
        self._print(DebugCategory.PARSE, f"AX IDs found: {len(ax_ids)}")
        if ax_ids:
            self._print(DebugCategory.PARSE, f"AX IDs: {ax_ids[:5]}{'...' if len(ax_ids) > 5 else ''}")
        
        # ID WMS
        self._print(DebugCategory.PARSE, f"WMS IDs found: {len(wms_ids)}")
        if wms_ids:
            self._print(DebugCategory.PARSE, f"WMS IDs: {wms_ids[:5]}{'...' if len(wms_ids) > 5 else ''}")
        
        self.indent_decrease()
    
    def button_action(self, callback_data: str, user_id: int):
        """
        Вывод информации о нажатии кнопки
        
        Args:
            callback_data: Данные из callback_data кнопки
            user_id:       ID пользователя, нажавшего кнопку
        
        Формат вывода:
            [BUTTON] Button clicked:
              callback_data: copy_ax_chatid_messageid
              user_id: 123456789
        
        Информация:
            - callback_data: содержит ключ хранилища и тип действия
            - user_id: идентификатор пользователя для отслеживания
        """
        if not self.enabled:
            return
        
        self._print(DebugCategory.BUTTON, f"Button clicked:")
        self.indent_increase()
        self._print(DebugCategory.BUTTON, f"callback_data: {callback_data}")
        self._print(DebugCategory.BUTTON, f"User: {user_id}")
        self.indent_decrease()
    
    def bot_action(self, action: str, message_id: Optional[int] = None, details: str = ""):
        """
        Вывод информации о действии бота
        
        Args:
            action:    Тип действия ("SEND_MESSAGE", "EDIT_MESSAGE", "DELETE_MESSAGE")
            message_id: ID сообщения (если применимо)
            details:   Дополнительные детали
        
        Формат вывода:
            [BOT] Bot action: ACTION
              message_id: 123
              details: Additional information
        
        Примеры действий:
            - MESSAGE_SENT: Сообщение отправлено
            - MESSAGE_EDITED: Сообщение отредактировано
            - DELETE_MESSAGE: Попытка удаления сообщения
            - MESSAGE_DELETED: Сообщение успешно удалено
        """
        if not self.enabled:
            return
        
        self._print(DebugCategory.BOT, f"Bot action: {action}")
        self.indent_increase()
        
        if message_id:
            self._print(DebugCategory.BOT, f"message_id: {message_id}")
        
        if details:
            self._print(DebugCategory.BOT, f"details: {details}")
        
        self.indent_decrease()
    
    def ui_created(self, has_ax: bool, has_wms: bool, bot_message_id: int):
        """
        Вывод информации о создании пользовательского интерфейса
        
        Args:
            has_ax:        Создана ли кнопка для ID AX
            has_wms:       Создана ли кнопка для ID WMS
            bot_message_id: ID сообщения бота с кнопками
        
        Формат вывода:
            [UI] UI created:
              has_ax_button: True
              has_wms_button: False
              bot_message_id: 123
        
        Назначение:
            - Отслеживание создания интерактивных элементов
            - Дебаг логики отображения кнопок
            - Связывание сообщения бота с исходными данными
        """
        if not self.enabled:
            return
        
        self._print(DebugCategory.UI, f"UI created:")
        self.indent_increase()
        self._print(DebugCategory.UI, f"has_ax_button: {has_ax}")
        self._print(DebugCategory.UI, f"has_wms_button: {has_wms}")
        self._print(DebugCategory.UI, f"bot_message_id: {bot_message_id}")
        self.indent_decrease()
    
    def error_occurred(self, func_name: str, error: Exception):
        """
        Вывод информации об ошибке
        
        Args:
            func_name: Имя функции, в которой произошла ошибка
            error:     Объект исключения
        
        Формат вывода:
            [ERROR] Error in FUNCTION_NAME:
              type: TypeError
              message: 'NoneType' object is not subscriptable
        
        Назначение:
            - Структурированное логирование ошибок
            - Упрощение отладки исключений
            - Отделение ошибок от обычных отладочных сообщений
        """
        if not self.enabled:
            return
        
        self._print(DebugCategory.ERROR, f"Error in {func_name}:")
        self.indent_increase()
        self._print(DebugCategory.ERROR, f"type: {type(error).__name__}")
        self._print(DebugCategory.ERROR, f"message: {str(error)}")
        self.indent_decrease()
    
    def info_msg(self, message: str):
        """
        Вывод информационного сообщения
        
        Args:
            message: Текст информационного сообщения
        
        Назначение:
            - Общие информационные сообщения
            - Сообщения о ходе выполнения
            - Не критичные уведомления
        
        Отличия от других категорий:
            - INFO: общая информация
            - MESSAGE: информация о сообщениях Telegram
            - PARSE: конкретно о парсинге
        """
        self._print(DebugCategory.INFO, message)
    
    def cleanup_info(self, cleaned_count: int, total_count: int):
        """
        Вывод информации об очистке данных
        
        Args:
            cleaned_count: Количество удаленных записей
            total_count:   Общее количество записей до очистки
        
        Формат вывода:
            [CLEANUP] Cleanup performed:
              cleaned_records: 2
              total_records: 10
              TTL: 2h 0m
        
        Назначение:
            - Мониторинг работы механизма TTL
            - Отслеживание эффективности очистки
            - Дебаг управления памятью
        """
        if not self.enabled:
            return
        
        self._print(DebugCategory.CLEANUP, f"Cleanup performed:")
        self.indent_increase()
        self._print(DebugCategory.CLEANUP, f"cleaned_records: {cleaned_count}")
        self._print(DebugCategory.CLEANUP, f"total_records: {total_count}")
        self._print(DebugCategory.CLEANUP, f"TTL: {self._format_ttl(DATA_CLEANUP_INTERVAL)}")
        self.indent_decrease()

# ==================== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ====================
"""
Создание глобального экземпляра дебаггера для использования во всех модулях.

Принцип:
    - Singleton: один экземпляр на всё приложение
    - Глобальный доступ: from debugger import debug
    - Конфигурируемость: через DEBUG_MODE в config.py

Использование:
    from debugger import debug
    debug.info_msg("Processing started")
    debug.section_start("HANDLE MESSAGE", message_id=123)
"""

# Глобальный экземпляр дебаггера
debug = DebugPrinter()