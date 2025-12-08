"""
storage.py - Модуль для управления временным хранилищем данных

Назначение:
- Хранение данных парсинга в памяти
- Изоляция данных разных сообщений
- Автоочистка устаревших данных

Структура хранилища:
{
    "chat_id_message_id": {
        "ax_ids": ["ЗП-370751234", ...],
        "wms_ids": ["0000123456", ...],
        "timestamp": 1234567890.123,
        "current_bot_message_id": 123,
        "original_message_id": 456,
        "original_message_from": "User Name"
    }
}

Особенности:
- Данные хранятся только в памяти (перезагрузка бота очищает всё)
- Ключ: комбинация chat_id + message_id
- TTL: 2 часа (настраивается в config.py - DATA_CLEANUP_INTERVAL)
"""

import time
from typing import Dict, Any, Optional
from config import DATA_CLEANUP_INTERVAL
from debugger import debug

class DataStorage:
    """
    Класс для управления временным хранилищем данных
    
    Принцип работы:
    1. При парсинге сообщения данные сохраняются с ключом chat_id_message_id
    2. При нажатии кнопки данные извлекаются по этому ключу
    3. При реплае на сообщение бота - данные удаляются
    4. Регулярно очищаются устаревшие записи (старше TTL)
    """
    
    def __init__(self):
        """Инициализация пустого хранилища"""
        # Основное хранилище: словарь ключ->данные
        self.store: Dict[str, Dict[str, Any]] = {}
    
    def generate_key(self, chat_id: int, message_id: int) -> str:
        """
        Генерация уникального ключа для хранения данных
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения
        
        Returns:
            str: ключ в формате "chat_id + message_id"
        
        Пример: "-100123456789(id чата)_123(id сообщения)" -> уникальный ключ для этого сообщения
        """
        return f"{chat_id}_{message_id}"
    
    def store_data(self, key: str, data: Dict[str, Any]) -> None:
        """
        Сохранение данных с временной меткой
        
        Args:
            key: уникальный ключ
            data: словарь с данными
        
        Действия:
            - Добавляет временную метку
            - Сохраняет в хранилище
        """
        # Добавляем timestamp для TTL проверки
        data['timestamp'] = time.time()
        self.store[key] = data
    
    def get_data(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Получение данных по ключу
        
        Args:
            key: уникальный ключ
        
        Returns:
            Optional[Dict]: данные или None если не найдены
        """
        return self.store.get(key)
    
    def delete_data(self, key: str) -> bool:
        """
        Удаление данных по ключу
        
        Args:
            key: уникальный ключ
        
        Returns:
            bool: True если данные удалены, False если не найдены
        
        Используется при:
            - Ручном удалении сообщения бота
            - Очистке устаревших данных
        """
        if key in self.store:
            del self.store[key]
            return True
        return False
    
    def cleanup_old_data(self) -> int:
        """
        Очистка устаревших данных (старше TTL)
        
        Returns:
            int: количество удаленных записей
        
        Алгоритм:
            1. Проходит по всем записям в хранилище
            2. Проверяет возраст каждой записи
            3. Удаляет записи старше DATA_CLEANUP_INTERVAL - 
        """
        current_time = time.time()
        expired_keys = []
        
        # Поиск устаревших записей
        for key, data in self.store.items():
            if current_time - data.get('timestamp', 0) > DATA_CLEANUP_INTERVAL:
                expired_keys.append(key)
        
        # Удаление устаревших записей
        for key in expired_keys:
            del self.store[key]
        
        return len(expired_keys)
    
    def update_bot_message_id(self, key: str, message_id: int) -> bool:
        """
        Обновление ID сообщения бота в хранилище
        
        Args:
            key: уникальный ключ
            message_id: новый ID сообщения бота
        
        Returns:
            bool: True если обновлено, False если ключ не найден
        
        Используется при:
            - Редактировании сообщения бота (после нажатия кнопки)
        """
        if key in self.store:
            self.store[key]['current_bot_message_id'] = message_id
            return True
        return False

# ==================== ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ====================
# Создаем единственный экземпляр хранилища
# Все модули работают с этим экземпляром
storage = DataStorage()