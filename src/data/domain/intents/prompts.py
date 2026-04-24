from data.domain.users.models import User


class Prompt:
    @staticmethod
    def get(key, default=None, user: User | None = None):
        return default
