from typing import Any

from .schemas import Button, InlineButton


def build_keyboard(buttons: list[Button], vip_status: bool) -> dict[str, Any]:
    """
    Построить клавиатуру для MAX (inline keyboard)
    
    В MAX API reply-клавиатуры могут не поддерживаться,
    поэтому преобразуем их в inline-кнопки.
    
    Args:
        buttons: Список кнопок
        vip_status: VIP статус пользователя
        
    Returns:
        dict[str, Any]: Inline клавиатура в формате MAX API
    """
    button_rows = []
    
    # Карта специальных кнопок (имя кнопки -> callback payload)
    special_buttons = {
        "Назад": "exit_callback",
    }
    
    for button in buttons:
        # Если кнопка привилегированная и пользователь не VIP - пропускаем
        if button.privileged and not vip_status:
            continue
        
        # Определяем payload: для специальных кнопок используем их callback,
        # для обычных - имя кнопки (совпадает с именем flow для навигации)
        payload = special_buttons.get(button.name, button.name)
        
        btn_dict = {
            "text": button.name,
            "type": "callback",
            "payload": payload,
        }
        
        # Каждая кнопка в отдельной строке
        button_rows.append([btn_dict])
    
    # Возвращаем в формате MAX API attachments
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": button_rows
        }
    }


def build_inline_keyboard(
    buttons: list[InlineButton] | list[list[InlineButton]],
) -> dict[str, Any]:
    """
    Построить inline-клавиатуру для MAX API
    
    Args:
        buttons: Список кнопок или список списков кнопок
        
    Returns:
        dict[str, Any]: Inline клавиатура в формате MAX API attachments
    """
    button_rows = []
    
    # Если передан плоский список, делаем из него матрицу
    if buttons and isinstance(buttons[0], InlineButton):
        buttons = [[btn] for btn in buttons]  # type: ignore
    
    for row in buttons:
        keyboard_row = []
        for button in row:
            btn_dict: dict[str, str] = {
                "text": button.name,
            }
            
            if button.url:
                # Кнопка-ссылка
                btn_dict["type"] = "link"
                btn_dict["url"] = button.url
            elif button.pattern:
                # Кнопка с callback
                btn_dict["type"] = "callback"
                btn_dict["payload"] = button.pattern
            
            # Опционально: intent для MAX API (раскомментируйте если нужно)
            # btn_dict["intent"] = "default"
            
            keyboard_row.append(btn_dict)
        
        if keyboard_row:
            button_rows.append(keyboard_row)
    
    # Возвращаем в формате MAX API attachments
    return {
        "type": "inline_keyboard",
        "payload": {
            "buttons": button_rows
        }
    }


def add_button_to_inline_markup(
    markup: dict[str, Any],
    button: InlineButton,
) -> dict[str, Any]:
    """
    Добавить кнопку к inline-клавиатуре
    
    Args:
        markup: Существующая клавиатура
        button: Кнопка для добавления
        
    Returns:
        dict[str, Any]: Обновленная клавиатура
    """
    btn_dict: dict[str, str] = {"text": button.name}
    
    if button.url:
        btn_dict["url"] = button.url
    elif button.pattern:
        btn_dict["callback_data"] = button.pattern
    
    # Добавляем кнопку в новую строку
    if "inline_keyboard" not in markup:
        markup["inline_keyboard"] = []
    
    markup["inline_keyboard"].append([btn_dict])
    
    return markup

