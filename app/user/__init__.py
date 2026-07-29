"""User Platform package — fixtures, memory persistence, and future adapters."""

from app.user.fixtures import DEMO_PASSWORD, DEMO_USERS, list_demo_users, seed_demo_users

__all__ = ["DEMO_USERS", "DEMO_PASSWORD", "list_demo_users", "seed_demo_users"]
