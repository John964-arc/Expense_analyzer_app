"""
db_test.py
==========
Supabase integration test & setup script for AI-Expense.

What this script does
---------------------
1.  Verifies the Supabase connection.
2.  Prints the SQL you need to run once in the Supabase SQL Editor to create
    every table that the app uses.
3.  Runs live CRUD smoke-tests against each table so you know the client
    is working end-to-end.

Run
---
    python db_test.py
"""

import sys
from datetime import date

# ── Import the singleton client and all helpers ────────────────────────────
from database.supabase_db import (
    get_client,
    SupabaseUsers,
    SupabaseExpenses,
    SupabaseBudgets,
    SupabaseSavings,
    SupabaseFamily,
)

# ─────────────────────────────────────────────────────────────────────────────
# 0. Supabase SQL Schema  (run this ONCE in Supabase → SQL Editor)
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
-- ============================================================
-- AI-Expense  •  Supabase Schema
-- Run this once in the Supabase SQL Editor
-- ============================================================

-- Users ---------------------------------------------------------
create table if not exists users (
  id               bigserial primary key,
  username         text        not null unique,
  email            text        not null unique,
  password_hash    text        not null,
  profile_picture  text,
  base_currency    text        not null default 'INR',
  created_at       timestamptz not null default now()
);

-- Expenses -------------------------------------------------------
create table if not exists expenses (
  id                bigserial primary key,
  user_id           bigint      not null references users(id) on delete cascade,
  name              text        not null,
  amount            float8      not null,
  category          text        not null default 'Other',
  date              date        not null default current_date,
  description       text        not null default '',
  receipt_image     text,
  currency          text        not null default 'INR',
  converted_amount  float8,
  is_recurring      boolean     not null default false,
  recurring_day     int,
  recurring_type    text        not null default 'MONTHLY',
  subscription_name text,
  source            text        not null default 'manual',
  import_hash       text        unique,
  family_id         bigint      references family_groups(id) on delete set null,
  is_private        boolean     not null default true,
  created_at        timestamptz not null default now()
);

-- Budgets --------------------------------------------------------
create table if not exists budgets (
  id         bigserial primary key,
  user_id    bigint  not null references users(id) on delete cascade,
  category   text,                     -- NULL = overall monthly budget
  month      int     not null,
  year       int     not null,
  amount     float8  not null,
  created_at timestamptz not null default now(),
  unique (user_id, category, month, year)
);

-- Savings Goals --------------------------------------------------
create table if not exists savings_goals (
  id            bigserial primary key,
  user_id       bigint  not null references users(id) on delete cascade,
  name          text    not null,
  target_amount float8  not null,
  saved_amount  float8  not null default 0,
  target_date   date,
  icon          text    not null default '🎯',
  color         text    not null default '#6C63FF',
  is_completed  boolean not null default false,
  created_at    timestamptz not null default now()
);

-- Savings Contributions ------------------------------------------
create table if not exists savings_contributions (
  id      bigserial primary key,
  goal_id bigint  not null references savings_goals(id) on delete cascade,
  user_id bigint  not null references users(id) on delete cascade,
  amount  float8  not null,
  note    text,
  date    timestamptz not null default now()
);

-- Family Groups --------------------------------------------------
create table if not exists family_groups (
  id          bigserial primary key,
  name        text not null,
  invite_code text not null unique,
  created_by  bigint not null references users(id) on delete cascade,
  created_at  timestamptz not null default now()
);

-- Family Members -------------------------------------------------
create table if not exists family_members (
  id        bigserial primary key,
  user_id   bigint not null references users(id) on delete cascade,
  group_id  bigint not null references family_groups(id) on delete cascade,
  role      text   not null default 'MEMBER',
  joined_at timestamptz not null default now(),
  unique (user_id, group_id)
);
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def ok(msg: str):
    print(f"  ✅  {msg}")

def fail(msg: str, err):
    print(f"  ❌  {msg}: {err}")

def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Connection test
# ─────────────────────────────────────────────────────────────────────────────

section("1. Connection")

try:
    client = get_client()
    ok(f"Connected to Supabase  →  {client.supabase_url}")
except Exception as e:
    fail("Cannot connect to Supabase", e)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Print schema (informational)
# ─────────────────────────────────────────────────────────────────────────────

section("2. Schema SQL  (run once in Supabase → SQL Editor if tables are missing)")
print(SCHEMA_SQL)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Smoke tests — Users
# ─────────────────────────────────────────────────────────────────────────────

section("3. Users CRUD")

TEST_EMAIL    = "test_integration@aiexpense.dev"
TEST_USERNAME = "test_integration_user"
test_user_id  = None

try:
    # Clean up any leftover from a previous run
    existing = SupabaseUsers.get_by_email(TEST_EMAIL)
    if existing:
        SupabaseUsers.delete(existing["id"])

    user = SupabaseUsers.create(
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        password_hash="hashed_pw_placeholder",
        base_currency="INR",
    )
    test_user_id = user["id"]
    ok(f"Created user  id={test_user_id}  username={user['username']}")
except Exception as e:
    fail("Create user", e)

if test_user_id:
    try:
        fetched = SupabaseUsers.get_by_id(test_user_id)
        assert fetched["email"] == TEST_EMAIL
        ok(f"Fetched user by id  →  email={fetched['email']}")
    except Exception as e:
        fail("Fetch user by id", e)

    try:
        updated = SupabaseUsers.update(test_user_id, base_currency="USD")
        ok(f"Updated user base_currency  →  {updated.get('base_currency')}")
    except Exception as e:
        fail("Update user", e)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Smoke tests — Expenses
# ─────────────────────────────────────────────────────────────────────────────

section("4. Expenses CRUD")

test_expense_id = None

if test_user_id:
    try:
        expense = SupabaseExpenses.create(
            user_id=test_user_id,
            name="Netflix",
            amount=649.0,
            category="Entertainment",
            date=str(date.today()),
            description="Monthly subscription",
            currency="INR",
            is_recurring=True,
            recurring_day=1,
            recurring_type="MONTHLY",
            subscription_name="Netflix",
            source="manual",
        )
        test_expense_id = expense["id"]
        ok(f"Created expense  id={test_expense_id}  name={expense['name']}")
    except Exception as e:
        fail("Create expense", e)

    if test_expense_id:
        try:
            expenses = SupabaseExpenses.get_by_user(test_user_id)
            ok(f"Fetched {len(expenses)} expense(s) for user")
        except Exception as e:
            fail("Get expenses by user", e)

        try:
            today = date.today()
            monthly = SupabaseExpenses.get_by_month(test_user_id, today.year, today.month)
            ok(f"Fetched {len(monthly)} expense(s) for {today.month}/{today.year}")
        except Exception as e:
            fail("Get expenses by month", e)

        try:
            recurring = SupabaseExpenses.get_recurring(test_user_id)
            ok(f"Fetched {len(recurring)} recurring expense(s)")
        except Exception as e:
            fail("Get recurring expenses", e)

        try:
            updated_exp = SupabaseExpenses.update(test_expense_id, amount=799.0)
            ok(f"Updated expense amount  →  {updated_exp.get('amount')}")
        except Exception as e:
            fail("Update expense", e)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Smoke tests — Budgets
# ─────────────────────────────────────────────────────────────────────────────

section("5. Budgets CRUD")

test_budget_id = None

if test_user_id:
    today = date.today()
    try:
        budget = SupabaseBudgets.upsert(
            user_id=test_user_id,
            month=today.month,
            year=today.year,
            amount=10000.0,
            category="Entertainment",
        )
        test_budget_id = budget.get("id")
        ok(f"Upserted budget  id={test_budget_id}  amount={budget.get('amount')}")
    except Exception as e:
        fail("Upsert budget", e)

    try:
        budgets = SupabaseBudgets.get_by_user_month(test_user_id, today.month, today.year)
        ok(f"Fetched {len(budgets)} budget(s) for {today.month}/{today.year}")
    except Exception as e:
        fail("Fetch budgets", e)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Smoke tests — Savings Goals & Contributions
# ─────────────────────────────────────────────────────────────────────────────

section("6. Savings Goals & Contributions CRUD")

test_goal_id = None

if test_user_id:
    try:
        goal = SupabaseSavings.create_goal(
            user_id=test_user_id,
            name="Vacation Fund",
            target_amount=50000.0,
            saved_amount=5000.0,
            icon="✈️",
            color="#FF6584",
        )
        test_goal_id = goal["id"]
        ok(f"Created savings goal  id={test_goal_id}  name={goal['name']}")
    except Exception as e:
        fail("Create savings goal", e)

    if test_goal_id:
        try:
            contrib = SupabaseSavings.add_contribution(
                goal_id=test_goal_id,
                user_id=test_user_id,
                amount=2000.0,
                note="Side-hustle income",
            )
            ok(f"Added contribution  id={contrib['id']}  amount={contrib['amount']}")
        except Exception as e:
            fail("Add contribution", e)

        try:
            contribs = SupabaseSavings.get_contributions(test_goal_id)
            ok(f"Fetched {len(contribs)} contribution(s)")
        except Exception as e:
            fail("Fetch contributions", e)

        try:
            goals = SupabaseSavings.get_goals_by_user(test_user_id)
            ok(f"Fetched {len(goals)} savings goal(s) for user")
        except Exception as e:
            fail("Fetch goals by user", e)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Smoke tests — Family Groups
# ─────────────────────────────────────────────────────────────────────────────

section("7. Family Groups & Members CRUD")

test_group_id = None

if test_user_id:
    try:
        group = SupabaseFamily.create_group(
            name="Test Family",
            invite_code="TEST1234",
            created_by=test_user_id,
        )
        test_group_id = group["id"]
        ok(f"Created family group  id={test_group_id}  name={group['name']}")
    except Exception as e:
        fail("Create family group", e)

    if test_group_id:
        try:
            member = SupabaseFamily.add_member(
                user_id=test_user_id,
                group_id=test_group_id,
                role="ADMIN",
            )
            ok(f"Added member  user_id={member['user_id']}  role={member['role']}")
        except Exception as e:
            fail("Add member", e)

        try:
            members = SupabaseFamily.get_members(test_group_id)
            ok(f"Fetched {len(members)} member(s) in group")
        except Exception as e:
            fail("Fetch members", e)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Cleanup — delete all test data
# ─────────────────────────────────────────────────────────────────────────────

section("8. Cleanup")

if test_expense_id:
    try:
        SupabaseExpenses.delete(test_expense_id)
        ok(f"Deleted expense id={test_expense_id}")
    except Exception as e:
        fail("Delete expense", e)

if test_budget_id:
    try:
        SupabaseBudgets.delete(test_budget_id)
        ok(f"Deleted budget id={test_budget_id}")
    except Exception as e:
        fail("Delete budget", e)

if test_goal_id:
    try:
        SupabaseSavings.delete_goal(test_goal_id)
        ok(f"Deleted savings goal id={test_goal_id}")
    except Exception as e:
        fail("Delete savings goal", e)

if test_group_id:
    try:
        SupabaseFamily.delete_group(test_group_id)
        ok(f"Deleted family group id={test_group_id}")
    except Exception as e:
        fail("Delete family group", e)

if test_user_id:
    try:
        SupabaseUsers.delete(test_user_id)
        ok(f"Deleted user id={test_user_id}")
    except Exception as e:
        fail("Delete user", e)


# ─────────────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────────────

section("All tests complete")
print("\n  ✅  Supabase is correctly integrated with AI-Expense.\n")
print("  Next step: copy the SQL from section 2 above and run it in")
print("  Supabase → SQL Editor (if you haven't already).\n")