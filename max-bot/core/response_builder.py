from typing import Any


def card_from_json(card: dict[str, Any], current_page: int, total_pages: int) -> str:
    """
    Создать текстовое представление карточки
    
    Args:
        card: Данные карточки
        current_page: Текущая страница
        total_pages: Всего страниц
        
    Returns:
        str: Текстовое представление карточки
    """
    lines = []
    
    # Заголовок с номером страницы
    lines.append(f"📄 Результат {current_page + 1} из {total_pages + 1}\n")
    
    # Название
    if "name" in card:
        lines.append(f"*{card['name']}*\n")
    elif "title" in card:
        lines.append(f"*{card['title']}*\n")
    
    # Описание
    if "description" in card:
        lines.append(f"{card['description']}\n")
    
    # Дополнительные поля
    if "company" in card:
        lines.append(f"🏢 Компания: {card['company']}")
    
    if "category" in card:
        lines.append(f"📂 Категория: {card['category']}")
    
    if "location" in card:
        lines.append(f"📍 Местоположение: {card['location']}")
    
    if "contact" in card:
        lines.append(f"📞 Контакт: {card['contact']}")
    
    if "url" in card:
        lines.append(f"🔗 [Подробнее]({card['url']})")
    
    return "\n".join(lines)

