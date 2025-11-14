import re


class Sentinels:
    """Класс с константами-сентинелами"""
    EMPTY_STR: str = ""
    EMPTY_INT: int = -1


def escape_markdown_v2(text: str) -> str:
    """
    Экранирует специальные символы для Markdown V2
    
    Args:
        text: Текст для экранирования
        
    Returns:
        str: Экранированный текст
    """
    # Символы, которые нужно экранировать в Markdown V2
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    
    # Экранируем каждый специальный символ
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    
    return text


def format_message_for_max(text: str) -> str:
    """
    Форматирует сообщение для MAX мессенджера
    Поддерживает базовую разметку
    
    Args:
        text: Текст сообщения
        
    Returns:
        str: Отформатированный текст
    """
    # MAX поддерживает простой Markdown
    # Конвертируем из Markdown V2 в обычный Markdown если нужно
    text = text.replace("\\*", "*")
    text = text.replace("\\_", "_")
    
    return text

