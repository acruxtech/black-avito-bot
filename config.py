import configparser
from dataclasses import dataclass


@dataclass
class DbConfig:
    user: str
    password: str
    address: str
    name: str


@dataclass
class TgBot:
    token: str
    admin_ids: list[int]


@dataclass
class Crypto:
    token: str


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    crypto: Crypto


def cast_bool(value: str) -> bool:
    if not value:
        return False
    return value.lower() in ("true", "t", "1", "yes", "y")


def load_config(path: str):
    config_ = configparser.ConfigParser()
    config_.read(path)

    tg_bot = config_["tg_bot"]

    return Config(
        tg_bot=TgBot(
            token=tg_bot["token"],
            admin_ids=list(map(int, tg_bot["admin_ids"].split(", "))),
        ),
        db=DbConfig(**config_["db"]),
        crypto=Crypto(**config_["crypto"]),
    )


config = load_config("config.ini")
