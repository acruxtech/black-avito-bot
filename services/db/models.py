from datetime import datetime

from sqlalchemy import Column, BigInteger, Integer, DateTime, Boolean, Text, ForeignKey, Float
from sqlalchemy.orm import relationship, Mapped

from services.db.base import Base


class BaseCommon(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)
    created_on = Column(DateTime, default=datetime.now)
    updated_on = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class User(BaseCommon):
    __tablename__ = "users"

    telegram_id = Column(BigInteger)
    username = Column(Text)
    is_bot_blocked = Column(Boolean, default=False)
    is_completed_registration = Column(Boolean, default=False)
    is_tg_premium = Column(Boolean)
    role = Column(Integer)
    balance = Column(Float, default=0)
    is_shadow_ban = Column(Boolean, default=False)

    # личная информация
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    job = relationship("Job", back_populates="users")
    skills = Column(Text, nullable=True)
    price = Column(Integer, nullable=True)
    show_completed_deals = Column(Boolean, default=True)


class Job(BaseCommon):
    __tablename__ = "jobs"

    title = Column(Text)
    users = relationship("User", back_populates="job")


class Deal(BaseCommon):
    __tablename__ = "deals"

    client_id = Column(BigInteger)
    executor_id = Column(BigInteger)
    is_confirmed_by_executor = Column(Boolean, default=False)
    amount = Column(Integer)
    conditions = Column(Text)
    is_completed = Column(Boolean, default=False)
