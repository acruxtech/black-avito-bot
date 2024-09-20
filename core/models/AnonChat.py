from dataclasses import dataclass


@dataclass
class AnonChat:
    from_user_telegram_id: int
    from_user_name: str
    amount_unreads: int
