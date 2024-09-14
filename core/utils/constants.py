FEE = 0.05

PRICE_MAPPER = {"s": 0, "m": 1, "l": 2}

TEXTS = {
    "start": """
Это бот для поиска заказчиков и исполнителей.
Выбери действие ниже
""",

    "deal_info": """
<b>id:</b> <code>{id}</code> ({is_confirmed_by_executor})
<b>Заказчик:</b> <code>{client_id}</code>
<b>Исполнитель:</b> <code>{executor_id}</code> 

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
