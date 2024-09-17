from aiogram import Bot
from apscheduler.jobstores.mongodb import MongoDBJobStore, MongoClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiocryptopay import AioCryptoPay, Networks

from config import load_config
from LOLZTEAM.API import Market
from services.api.lolzapi import LolzteamApi

config = load_config("config.ini")

job_defaults = {
    "max_instances": 10000
}
jobstores = {
    'mongo': MongoDBJobStore(client=MongoClient())
}

client = MongoClient()
scheduler = AsyncIOScheduler(job_defaults=job_defaults, jobstores=jobstores)

crypto = AioCryptoPay(token=config.crypto.token, network=Networks.TEST_NET)
# crypto = AioCryptoPay(token=config.crypto.token, network=Networks.MAIN_NET)
bot = Bot(token=config.tg_bot.token)

lolz = LolzteamApi(config.lolz.token, config.lolz.lolz_id)
