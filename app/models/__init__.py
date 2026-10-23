"""Реэкспорт всех ORM-моделей.

Важно: импорт этого пакета регистрирует модели в Base.metadata. Без него
Alembic не увидит таблицы при автогенерации миграций.
"""

from app.models.purchase import Purchase
from app.models.question import PurchaseQuestion
from app.models.specification import SpecAssumption, Specification
from app.models.user import User

__all__ = [
    "Purchase",
    "PurchaseQuestion",
    "SpecAssumption",
    "Specification",
    "User",
]
