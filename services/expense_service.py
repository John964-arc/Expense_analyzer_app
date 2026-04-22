from datetime import datetime
from utils.db_helper import db
from models.expense_model import Expense
from utils.category_detector import detect_category
from utils.helpers import get_month_range


class ExpenseService:

    @staticmethod
    def add_expense(user_id: int, name: str, amount: float,
                    date_str: str, description: str = '',
                    category: str = None, receipt_image: str = None,
                    currency: str = 'INR', converted_amount: float = None,
                    is_recurring: bool = False, recurring_day: int = None,
                    family_id: int = None, is_private: bool = True) -> Expense:
        """Create and persist a new expense record."""
        if category is None or category == 'auto':
            category = detect_category(name, description)

        try:
            expense_date = datetime.strptime(date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            expense_date = datetime.utcnow()

        expense = Expense(
            user_id          = user_id,
            name             = name.strip(),
            amount           = round(float(amount), 2),
            category         = category,
            date             = expense_date,
            description      = description.strip(),
            receipt_image    = receipt_image,
            currency         = currency or 'INR',
            converted_amount = round(converted_amount, 2) if converted_amount else None,
            is_recurring     = bool(is_recurring),
            recurring_day    = int(recurring_day) if recurring_day else None,
            family_id        = family_id,
            is_private       = is_private
        )
        db.session.add(expense)
        db.session.commit()
        return expense

    @staticmethod
    def get_user_expenses(user_id: int, limit: int = None) -> list:
        """Get all expenses for a user, newest first."""
        query = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def get_expenses_by_month(user_id: int, year: int, month: int) -> list:
        """Get expenses for a specific month."""
        start, end = get_month_range(year, month)
        return Expense.query.filter(
            Expense.user_id == user_id,
            Expense.date >= start,
            Expense.date <= end
        ).order_by(Expense.date.desc()).all()

    @staticmethod
    def delete_expense(expense_id: int, user_id: int) -> bool:
        """Delete an expense (only if it belongs to the user)."""
        expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
        if expense:
            db.session.delete(expense)
            db.session.commit()
            return True
        return False

    @staticmethod
    def update_expense(expense_id: int, user_id: int, **kwargs) -> Expense:
        """Update fields on an existing expense."""
        expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
        if not expense:
            return None
        for key, value in kwargs.items():
            if hasattr(expense, key) and value is not None:
                setattr(expense, key, value)
        db.session.commit()
        return expense

    @staticmethod
    def toggle_recurring(expense_id: int, user_id: int,
                         recurring_day: int = None,
                         recurring_type: str = 'MONTHLY',
                         subscription_name: str = None) -> Expense:
        """Flip the is_recurring flag on an expense."""
        expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
        if not expense:
            return None
        expense.is_recurring = not expense.is_recurring
        if expense.is_recurring:
            if recurring_day:
                expense.recurring_day = recurring_day
            if recurring_type:
                expense.recurring_type = recurring_type
            if subscription_name:
                expense.subscription_name = subscription_name
        else:
            expense.recurring_day = None
            expense.subscription_name = None
        db.session.commit()
        return expense

    @staticmethod
    def get_monthly_totals(user_id: int, num_months: int = 6) -> list:
        """Return list of monthly total floats (oldest first)."""
        from utils.helpers import months_list
        totals = []
        for year, month in months_list(num_months):
            expenses = ExpenseService.get_expenses_by_month(user_id, year, month)
            totals.append(sum(e.amount for e in expenses))
        return totals

    @staticmethod
    def get_category_totals(user_id: int, year: int, month: int) -> dict:
        """Return {category: total_amount} for a given month."""
        expenses = ExpenseService.get_expenses_by_month(user_id, year, month)
        totals = {}
        for e in expenses:
            totals[e.category] = totals.get(e.category, 0) + e.amount
        return {k: round(v, 2) for k, v in sorted(totals.items(), key=lambda x: x[1], reverse=True)}

    @staticmethod
    def get_weekly_totals(user_id: int, year: int, month: int) -> list:
        """Return weekly spending totals within a month."""
        from utils.helpers import get_week_ranges
        expenses = ExpenseService.get_expenses_by_month(user_id, year, month)
        weeks    = get_week_ranges(year, month)
        for week in weeks:
            week['total'] = round(sum(
                e.amount for e in expenses
                if week['start'] <= e.date <= week['end']
            ), 2)
        return weeks

    @staticmethod
    def search(user_id: int, query: str = '', category: str = '',
               sort: str = 'newest', year: int = None, month: int = None) -> list:
        """
        Full-text search across name, description, category.
        Supports optional month/year filter and sort order.
        """
        q = Expense.query.filter(Expense.user_id == user_id)

        # Month filter
        if year and month:
            start, end = get_month_range(year, month)
            q = q.filter(Expense.date >= start, Expense.date <= end)

        # Keyword search (partial, case-insensitive)
        if query:
            term = f'%{query.strip()}%'
            q = q.filter(
                db.or_(
                    Expense.name.ilike(term),
                    Expense.description.ilike(term),
                    Expense.category.ilike(term),
                )
            )

        # Category filter
        if category and category != 'all':
            q = q.filter(Expense.category == category)

        # Sort
        sort_map = {
            'newest':  Expense.date.desc(),
            'oldest':  Expense.date.asc(),
            'highest': Expense.amount.desc(),
            'lowest':  Expense.amount.asc(),
        }
        q = q.order_by(sort_map.get(sort, Expense.date.desc()))

        return q.all()
