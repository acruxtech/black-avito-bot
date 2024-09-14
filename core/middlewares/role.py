from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware

from services.db.services.repository import Repo
from core.models.role import UserRole


class RoleMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ["error", "update"]

    def __init__(self, owner_ids: list[int]):
        super().__init__()
        self.owner_ids = owner_ids

    async def pre_process(self, obj, data, *args):
        if not getattr(obj, "from_user", None):
            data["role"] = None
            return

        repo: Repo = data["repo"]
        user = await repo.get_user_by_telegram_id(obj.from_user.id)
        data["role"] = UserRole(user.role if user else 0)

        if obj.from_user.id in self.owner_ids:
            data["role"] = UserRole.OWNER

    async def post_process(self, obj, data, *args):
        del data["role"]
