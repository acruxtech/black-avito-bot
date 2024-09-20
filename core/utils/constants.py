FEE = 0.05
TECH_WORK_START_HOUR = 0
TECH_WORK_START_MINUTE = 0
TECH_WORK_END_HOUR = 0
TECH_WORK_END_MINUTE = 20
START_BET = 1
NEXT_BET_COEFFICIENT = 1.2
HIGHLIGHT_PRICE = 0.5

PRICE_MAPPER = {"s": 0, "m": 1, "l": 2}

TEXTS = {
    "start": """
Это бот для поиска заказчиков и исполнителей.
Выбери действие ниже
""",

    "deal_info": """
<b>id:</b> <code>{id}</code> ({is_confirmed_by_executor})
<b>Заказчик🛍️:</b> <code>{client_name}</code>
<b>Исполнитель👩‍💼:</b> <code>{executor_name}</code> 

<b>Сумма:</b> ${amount}
<b>Условия:</b>
{conditions}

<b>Выполнена:</b> {is_completed}
""",

    "support": """
Контакты тех. поддержки:
@...
    """
}
