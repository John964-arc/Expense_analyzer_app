"""
budget_service.py
─────────────────────────────────────────
CRUD + analysis for monthly budgets.
"""
from datetime import datetime
from utils.db_helper import db
from models.expense_model import Budget
from services.expense_service import ExpenseService


class BudgetService:

    @staticmethod
    def set_budget(user_id: int, amount: float, month: int, year: int,
                   category: str = None) -> Budget:
        """Create or update a budget for a month (overall or per-category)."""
        # Normalise: overall budget uses category=None
        category = category if category and category != 'overall' else None

        existing = Budget.query.filter_by(
            user_id=user_id, category=category, month=month, year=year
        ).first()

        if existing:
            existing.amount = round(float(amount), 2)
            db.session.commit()
            return existing

        budget = Budget(
            user_id  = user_id,
            category = category,
            month    = month,
            year     = year,
            amount   = round(float(amount), 2),
        )
        db.session.add(budget)
        db.session.commit()
        return budget

    @staticmethod
    def delete_budget(budget_id: int, user_id: int) -> bool:
        b = Budget.query.filter_by(id=budget_id, user_id=user_id).first()
        if b:
            db.session.delete(b)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_budgets(user_id: int, year: int, month: int) -> list:
        """Return all Budget rows for a given month."""
        return Budget.query.filter_by(
            user_id=user_id, month=month, year=year
        ).all()

    @staticmethod
    def get_budget_status(user_id: int, year: int, month: int) -> list:
        """
        Return a rich status list, one item per budget set for the month.
        Each item includes spent, remaining, pct, and alert_level.
        """
        budgets       = BudgetService.get_budgets(user_id, year, month)
        category_totals = ExpenseService.get_category_totals(user_id, year, month)
        monthly_total   = sum(category_totals.values())

        status = []
        for b in budgets:
            if b.category is None:
                spent = monthly_total
                label = 'Overall'
            else:
                spent = category_totals.get(b.category, 0.0)
                label = b.category

            pct       = (spent / b.amount * 100) if b.amount > 0 else 0
            remaining = max(b.amount - spent, 0.0)
            overspent = spent > b.amount

            if overspent:
                alert = 'danger'
            elif pct >= 90:
                alert = 'critical'
            elif pct >= 75:
                alert = 'warning'
            elif pct >= 50:
                alert = 'moderate'
            else:
                alert = 'ok'

            status.append({
                'id':        b.id,
                'label':     label,
                'category':  b.category,
                'budget':    b.amount,
                'spent':     round(spent, 2),
                'remaining': round(remaining, 2),
                'pct':       round(min(pct, 100), 1),
                'overspent': overspent,
                'alert':     alert,
            })

        return sorted(status, key=lambda x: x['pct'], reverse=True)

    @staticmethod
    def get_dashboard_warnings(user_id: int) -> list:
        """Return budget items that are at ≥50 % for the current month."""
        now    = datetime.now()
        status = BudgetService.get_budget_status(user_id, now.year, now.month)
        return [s for s in status if s['alert'] not in ('ok',)]
