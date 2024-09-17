import logging

from sqlalchemy import select, delete, and_, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from assets.misc import generate_name
from services.db.models import User, Job, Deal

logger = logging.getLogger(__name__)


class Repo:
    """Db abstraction layer"""

    def __init__(self, conn):
        self.conn: AsyncSession = conn

    async def add_user(
            self,
            telegram_id: int,
            username: str,
            is_tg_premium: bool,
            role: int = 0,
    ):
        db_user = await self.get_user_by_telegram_id(telegram_id)
        if db_user is not None:
            return db_user

        user = User(
            telegram_id=telegram_id,
            username=username,
            name=generate_name(),
            is_tg_premium=is_tg_premium,
            role=role,
        )

        self.conn.add(user)
        await self.conn.commit()

        logger.info(f"add new user with {telegram_id=}")

        return user

    async def get_users(self) -> list[User]:
        res = await self.conn.execute(
            select(User).options(selectinload(User.job))
        )

        return res.scalars().all()

    async def get_users_telegram_ids(self) -> list[int]:
        res = await self.conn.execute(
            select(User.telegram_id)
        )

        return res.scalars().all()

    async def get_users_ids(self) -> list[int]:
        res = await self.conn.execute(
            select(User.id)
        )

        return res.scalars().all()

    async def get_amount_users(self) -> int:
        res = await self.conn.execute(
            "SELECT COUNT(*) from users"
        )

        return res.scalars().one()

    async def get_amount_tg_premium_users(self) -> int:
        res = await self.conn.execute(
            "SELECT COUNT(*) from users WHERE is_tg_premium = true"
        )

        return res.scalars().one()

    async def get_amount_blocked_users(self) -> int:
        res = await self.conn.execute(
            "SELECT COUNT(*) from users WHERE is_bot_blocked IS TRUE;"
        )

        return res.scalars().one()

    async def get_amount_completed_registration_users(self) -> int:
        res = await self.conn.execute(
            "SELECT COUNT(*) from users WHERE is_completed_registration = true"
        )

        return res.scalars().one()

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        res = await self.conn.execute(
            select(User).options(selectinload(User.job)).where(User.telegram_id == telegram_id)
        )

        return res.scalars().first()


    async def get_user_by_name(self, name: str) -> User | None:
        res = await self.conn.execute(
            select(User).options(selectinload(User.job)).where(User.name == name)
        )

        return res.scalars().first()

    async def get_user_by_id(self, user_id: int) -> User | None:
        res = await self.conn.execute(
            select(User).options(selectinload(User.job)).where(User.id == user_id)
        )

        return res.scalars().first()

    async def update_user(self, telegram_id: int = None, user_id: int = None, job: str | None = None, **kwargs):
        if telegram_id:
            user = await self.get_user_by_telegram_id(telegram_id)
        elif user_id:
            user = await self.get_user_by_id(user_id)
        else:
            raise ValueError(f'Telegram ID or id is required')

        if not user:
            raise ValueError(f'User with id {telegram_id if telegram_id else user_id} doesn\'t exist')

        if job == "":
            user.job = None
            user.job_id = None
        elif job:
            job = await self.get_job_by_title(job)
            user.job = job

        for key, value in kwargs.items():
            if not hasattr(User, key):
                raise ValueError(f'Class `User` doesn\'t have argument {key}')
            setattr(user, key, value)
        await self.conn.commit()
        return user

    async def get_users_usernames(self) -> list[str]:
        res = await self.conn.execute(
            select(User.username)
        )
        return res.scalars().all()

    async def get_users_where(self, **kwargs) -> list[User] | None:
        res = await self.conn.execute(
            select(User)
            .options(selectinload(User.job))
            .where(
                and_(
                    *[User.__table__.columns[k] == v for k, v in kwargs.items()]
                )
            )
        )

        return res.scalars().all()

    async def get_jobs(self) -> list[Job]:
        res = await self.conn.execute(
            select(Job).order_by(Job.title.asc())
        )

        return res.scalars().all()

    async def get_job_by_title(self, title: str) -> Job | None:
        res = await self.conn.execute(
            select(Job).where(Job.title == title)
        )
        return res.scalars().first()

    async def get_job_by_id(self, job_id: int) -> Job | None:
        res = await self.conn.execute(
            select(Job).where(Job.id == job_id)
        )
        return res.scalars().first()

    async def add_job(self, title: str):
        job = Job(
            title=title,
        )
        self.conn.add(job)
        await self.conn.commit()

        logger.info(f"add new job with {title=}")

    async def update_job(self, curr_title: str, **kwargs):
        job = await self.get_job_by_title(curr_title)
        if not job:
            raise ValueError(f'Job with title {curr_title} doesn\'t exist')

        for key, value in kwargs.items():
            if not hasattr(Job, key):
                raise ValueError(f'Class `Job` doesn\'t have argument {key}')
            setattr(job, key, value)
        await self.conn.commit()
        return job

    async def delete_job(self, title: str):
        job = await self.get_job_by_title(title)

        if job is None:
            raise ValueError(f"Job with {title=} doensn't exist")

        await self.conn.delete(job)
        await self.conn.commit()

    async def add_deal(
            self,
            client_id: int,
            executor_id: int,
            amount: int,
            conditions: str,
    ) -> Deal:
        deal = Deal(
            client_id=client_id,
            executor_id=executor_id,
            amount=amount,
            conditions=conditions,
        )

        self.conn.add(deal)
        await self.conn.commit()

        logger.info(f"add new deal with {client_id=} and {executor_id=}")
        return deal

    async def get_deal_by_id(self, deal_id: int) -> Deal | None:
        res = await self.conn.execute(
            select(Deal).where(
                Deal.id == deal_id,
            )
        )

        return res.scalars().first()

    async def get_user_deals(self, user_id: int) -> list[Deal]:
        res = await self.conn.execute(
            select(Deal).where(
                or_(
                    Deal.executor_id == user_id,
                    Deal.client_id == user_id,
                )
            )
        )

        return res.scalars().all()

    async def get_user_executor_completed_deals(self, user_id: int) -> list[Deal]:
        res = await self.conn.execute(
            select(Deal).where(
                and_(
                    Deal.executor_id == user_id,
                    Deal.is_completed == True,
                )
            )
        )

        return res.scalars().all()

    async def update_deal(self, deal_id: int, **kwargs) -> Deal | None:
        deal = await self.get_deal_by_id(deal_id)
        if not deal:
            return

        for key, value in kwargs.items():
            if not hasattr(Deal, key):
                raise ValueError(f'Class `Deal` doesn\'t have argument {key}')
            setattr(deal, key, value)
        await self.conn.commit()
        return deal
