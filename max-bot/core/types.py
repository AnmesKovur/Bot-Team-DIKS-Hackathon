from typing import Any, TypeAlias

from .schemas import Button


# Типы для flow
Flow: TypeAlias = dict[str, Any]
Flows: TypeAlias = list[Flow]

# Типы для меню
Menu: TypeAlias = list[Button]
Menus: TypeAlias = dict[str, Menu]

