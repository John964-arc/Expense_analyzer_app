"""
database/supabase_db.py
========================
Supabase integration module for AI-Expense.

Provides:
  - A singleton `supabase` client instance.
  - Helper classes (SupabaseUsers, SupabaseExpenses, SupabaseBudgets,
    SupabaseSavings, SupabaseFamily) that mirror every SQLAlchemy model
    and expose clean CRUD operations against Supabase tables.
  - A top-level `get_client()` helper so the rest of the app can always
    import a ready-to-use client without worrying about initialisation.

Usage
-----
    from database.supabase_db import get_client, SupabaseExpenses

    # raw client
    client = get_client()

    # helper
    expenses = SupabaseExpenses.get_by_user(user_id=3)
"""

import os
from supabase import create_client, Client

# ─────────────────────────────────────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────────────────────────────────────

SUPABASE_URL: str = os.environ.get(
    "SUPABASE_URL",
    "https://cedalfajksyophwnbwpb.supabase.co"
)
SUPABASE_KEY: str = os.environ.get(
    "SUPABASE_KEY",
    "sb_publishable_DRcuxp-WHazVTjQMiTksNQ_39uHbfBI"
)

_client: Client | None = None


def get_client() -> Client:
    """Return the singleton Supabase client, creating it on first call."""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# Convenience alias — `from database.supabase_db import supabase`
supabase: Client = get_client()


# ─────────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────────

class SupabaseUsers:
    TABLE = "users"

    @classmethod
    def get_by_id(cls, user_id: int) -> dict | None:
        res = supabase.table(cls.TABLE).select("*").eq("id", user_id).single().execute()
        return res.data

    @classmethod
    def get_by_email(cls, email: str) -> dict | None:
        res = supabase.table(cls.TABLE).select("*").eq("email", email).maybe_single().execute()
        return res.data

    @classmethod
    def get_by_username(cls, username: str) -> dict | None:
        res = supabase.table(cls.TABLE).select("*").eq("username", username).maybe_single().execute()
        return res.data

    @classmethod
    def create(cls, username: str, email: str, password_hash: str,
               base_currency: str = "INR") -> dict:
        payload = {
            "username":      username,
            "email":         email,
            "password_hash": password_hash,
            "base_currency": base_currency,
        }
        res = supabase.table(cls.TABLE).insert(payload).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def update(cls, user_id: int, **fields) -> dict:
        res = supabase.table(cls.TABLE).update(fields).eq("id", user_id).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def delete(cls, user_id: int) -> bool:
        res = supabase.table(cls.TABLE).delete().eq("id", user_id).execute()
        return bool(res.data)


# ─────────────────────────────────────────────────────────────────────────────
# Expenses
# ─────────────────────────────────────────────────────────────────────────────

class SupabaseExpenses:
    TABLE = "expenses"

    @classmethod
    def get_by_user(cls, user_id: int) -> list[dict]:
        res = supabase.table(cls.TABLE).select("*").eq("user_id", user_id).order("date", desc=True).execute()
        return res.data or []

    @classmethod
    def get_by_id(cls, expense_id: int) -> dict | None:
        res = supabase.table(cls.TABLE).select("*").eq("id", expense_id).maybe_single().execute()
        return res.data

    @classmethod
    def get_by_month(cls, user_id: int, year: int, month: int) -> list[dict]:
        start = f"{year}-{month:02d}-01"
        # last day: cheat by going to next month day 1 and using lt
        if month == 12:
            end = f"{year + 1}-01-01"
        else:
            end = f"{year}-{month + 1:02d}-01"
        res = (
            supabase.table(cls.TABLE)
            .select("*")
            .eq("user_id", user_id)
            .gte("date", start)
            .lt("date", end)
            .order("date", desc=True)
            .execute()
        )
        return res.data or []

    @classmethod
    def create(cls, user_id: int, name: str, amount: float,
               category: str = "Other", date: str | None = None,
               description: str = "", currency: str = "INR",
               converted_amount: float | None = None,
               is_recurring: bool = False, recurring_day: int | None = None,
               recurring_type: str = "MONTHLY",
               subscription_name: str | None = None,
               source: str = "manual", import_hash: str | None = None,
               family_id: int | None = None, is_private: bool = True,
               receipt_image: str | None = None) -> dict:
        payload = {
            "user_id":           user_id,
            "name":              name,
            "amount":            amount,
            "category":          category,
            "description":       description,
            "currency":          currency,
            "converted_amount":  converted_amount,
            "is_recurring":      is_recurring,
            "recurring_day":     recurring_day,
            "recurring_type":    recurring_type,
            "subscription_name": subscription_name,
            "source":            source,
            "import_hash":       import_hash,
            "family_id":         family_id,
            "is_private":        is_private,
            "receipt_image":     receipt_image,
        }
        if date:
            payload["date"] = date
        # Strip None values so Supabase uses column defaults
        payload = {k: v for k, v in payload.items() if v is not None}
        res = supabase.table(cls.TABLE).insert(payload).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def update(cls, expense_id: int, **fields) -> dict:
        res = supabase.table(cls.TABLE).update(fields).eq("id", expense_id).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def delete(cls, expense_id: int) -> bool:
        res = supabase.table(cls.TABLE).delete().eq("id", expense_id).execute()
        return bool(res.data)

    @classmethod
    def get_recurring(cls, user_id: int) -> list[dict]:
        res = (
            supabase.table(cls.TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("is_recurring", True)
            .execute()
        )
        return res.data or []

    @classmethod
    def exists_by_hash(cls, import_hash: str) -> bool:
        res = supabase.table(cls.TABLE).select("id").eq("import_hash", import_hash).maybe_single().execute()
        return res.data is not None


# ─────────────────────────────────────────────────────────────────────────────
# Budgets
# ─────────────────────────────────────────────────────────────────────────────

class SupabaseBudgets:
    TABLE = "budgets"

    @classmethod
    def get_by_user_month(cls, user_id: int, month: int, year: int) -> list[dict]:
        res = (
            supabase.table(cls.TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("month", month)
            .eq("year", year)
            .execute()
        )
        return res.data or []

    @classmethod
    def get_by_id(cls, budget_id: int) -> dict | None:
        res = supabase.table(cls.TABLE).select("*").eq("id", budget_id).maybe_single().execute()
        return res.data

    @classmethod
    def upsert(cls, user_id: int, month: int, year: int,
               amount: float, category: str | None = None) -> dict:
        payload = {
            "user_id":  user_id,
            "month":    month,
            "year":     year,
            "amount":   amount,
            "category": category,
        }
        # Check if record exists first
        q = (
            supabase.table(cls.TABLE)
            .select("id")
            .eq("user_id", user_id)
            .eq("month", month)
            .eq("year", year)
        )
        if category:
            q = q.eq("category", category)
        else:
            q = q.is_("category", "null")
        existing = q.maybe_single().execute()

        if existing.data:
            res = supabase.table(cls.TABLE).update({"amount": amount}).eq("id", existing.data["id"]).execute()
        else:
            res = supabase.table(cls.TABLE).insert(payload).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def delete(cls, budget_id: int) -> bool:
        res = supabase.table(cls.TABLE).delete().eq("id", budget_id).execute()
        return bool(res.data)


# ─────────────────────────────────────────────────────────────────────────────
# Savings Goals & Contributions
# ─────────────────────────────────────────────────────────────────────────────

class SupabaseSavings:
    GOALS_TABLE         = "savings_goals"
    CONTRIBUTIONS_TABLE = "savings_contributions"

    # ── Goals ──────────────────────────────────────────────────────────────

    @classmethod
    def get_goals_by_user(cls, user_id: int) -> list[dict]:
        res = supabase.table(cls.GOALS_TABLE).select("*").eq("user_id", user_id).execute()
        return res.data or []

    @classmethod
    def get_goal_by_id(cls, goal_id: int) -> dict | None:
        res = supabase.table(cls.GOALS_TABLE).select("*").eq("id", goal_id).maybe_single().execute()
        return res.data

    @classmethod
    def create_goal(cls, user_id: int, name: str, target_amount: float,
                    saved_amount: float = 0.0, target_date: str | None = None,
                    icon: str = "🎯", color: str = "#6C63FF") -> dict:
        payload = {
            "user_id":       user_id,
            "name":          name,
            "target_amount": target_amount,
            "saved_amount":  saved_amount,
            "icon":          icon,
            "color":         color,
            "is_completed":  False,
        }
        if target_date:
            payload["target_date"] = target_date
        res = supabase.table(cls.GOALS_TABLE).insert(payload).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def update_goal(cls, goal_id: int, **fields) -> dict:
        res = supabase.table(cls.GOALS_TABLE).update(fields).eq("id", goal_id).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def delete_goal(cls, goal_id: int) -> bool:
        res = supabase.table(cls.GOALS_TABLE).delete().eq("id", goal_id).execute()
        return bool(res.data)

    # ── Contributions ──────────────────────────────────────────────────────

    @classmethod
    def add_contribution(cls, goal_id: int, user_id: int,
                         amount: float, note: str | None = None) -> dict:
        payload = {
            "goal_id": goal_id,
            "user_id": user_id,
            "amount":  amount,
            "note":    note,
        }
        res = supabase.table(cls.CONTRIBUTIONS_TABLE).insert(payload).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def get_contributions(cls, goal_id: int) -> list[dict]:
        res = (
            supabase.table(cls.CONTRIBUTIONS_TABLE)
            .select("*")
            .eq("goal_id", goal_id)
            .order("date", desc=True)
            .execute()
        )
        return res.data or []


# ─────────────────────────────────────────────────────────────────────────────
# Family Groups & Members
# ─────────────────────────────────────────────────────────────────────────────

class SupabaseFamily:
    GROUPS_TABLE  = "family_groups"
    MEMBERS_TABLE = "family_members"

    # ── Groups ─────────────────────────────────────────────────────────────

    @classmethod
    def get_group_by_id(cls, group_id: int) -> dict | None:
        res = supabase.table(cls.GROUPS_TABLE).select("*").eq("id", group_id).maybe_single().execute()
        return res.data

    @classmethod
    def get_group_by_invite(cls, invite_code: str) -> dict | None:
        res = supabase.table(cls.GROUPS_TABLE).select("*").eq("invite_code", invite_code).maybe_single().execute()
        return res.data

    @classmethod
    def create_group(cls, name: str, invite_code: str, created_by: int) -> dict:
        payload = {
            "name":        name,
            "invite_code": invite_code,
            "created_by":  created_by,
        }
        res = supabase.table(cls.GROUPS_TABLE).insert(payload).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def delete_group(cls, group_id: int) -> bool:
        res = supabase.table(cls.GROUPS_TABLE).delete().eq("id", group_id).execute()
        return bool(res.data)

    # ── Members ────────────────────────────────────────────────────────────

    @classmethod
    def get_members(cls, group_id: int) -> list[dict]:
        res = supabase.table(cls.MEMBERS_TABLE).select("*").eq("group_id", group_id).execute()
        return res.data or []

    @classmethod
    def get_user_groups(cls, user_id: int) -> list[dict]:
        res = supabase.table(cls.MEMBERS_TABLE).select("*").eq("user_id", user_id).execute()
        return res.data or []

    @classmethod
    def add_member(cls, user_id: int, group_id: int, role: str = "MEMBER") -> dict:
        payload = {
            "user_id":  user_id,
            "group_id": group_id,
            "role":     role,
        }
        res = supabase.table(cls.MEMBERS_TABLE).insert(payload).execute()
        return res.data[0] if res.data else {}

    @classmethod
    def remove_member(cls, user_id: int, group_id: int) -> bool:
        res = (
            supabase.table(cls.MEMBERS_TABLE)
            .delete()
            .eq("user_id", user_id)
            .eq("group_id", group_id)
            .execute()
        )
        return bool(res.data)
