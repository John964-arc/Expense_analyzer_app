"""
services/admin_service.py
=========================
Admin-only service layer for system-wide management.
Provides dashboard stats, user management, and global expense operations.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, desc
from utils.db_helper import db
from models.expense_model import (
    User, Expense, Budget, SavingsGoal, SavingsContribution,
    FamilyGroup, FamilyMember
)


class AdminService:

    # ── Dashboard Stats ────────────────────────────────────────────────────

    @staticmethod
    def get_dashboard_stats() -> dict:
        """Return high-level KPI stats for the admin dashboard."""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        total_users = db.session.query(func.count(User.id)).scalar() or 0
        total_expenses = db.session.query(func.count(Expense.id)).scalar() or 0
        total_amount = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).scalar()

        # This month's stats
        month_expenses = db.session.query(func.count(Expense.id)).filter(
            Expense.date >= month_start
        ).scalar() or 0
        month_amount = db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        ).filter(Expense.date >= month_start).scalar()

        # Last month's stats for comparison
        prev_month_amount = db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        ).filter(
            Expense.date >= prev_month_start,
            Expense.date < month_start
        ).scalar()

        # Active users this month (users who added expenses)
        active_users = db.session.query(
            func.count(func.distinct(Expense.user_id))
        ).filter(Expense.date >= month_start).scalar() or 0

        # New users this month
        new_users = db.session.query(func.count(User.id)).filter(
            User.created_at >= month_start
        ).scalar() or 0

        # Month-over-month change
        if prev_month_amount and prev_month_amount > 0:
            mom_change = round(((month_amount - prev_month_amount) / prev_month_amount) * 100, 1)
        else:
            mom_change = 0

        # Savings goals stats
        total_goals = db.session.query(func.count(SavingsGoal.id)).scalar() or 0
        total_saved = db.session.query(
            func.coalesce(func.sum(SavingsGoal.saved_amount), 0)
        ).scalar()

        # Budget count
        total_budgets = db.session.query(func.count(Budget.id)).scalar() or 0

        # Family groups
        total_families = db.session.query(func.count(FamilyGroup.id)).scalar() or 0

        return {
            'total_users': total_users,
            'total_expenses': total_expenses,
            'total_amount': round(total_amount, 2),
            'month_expenses': month_expenses,
            'month_amount': round(month_amount, 2),
            'prev_month_amount': round(prev_month_amount, 2),
            'mom_change': mom_change,
            'active_users': active_users,
            'new_users': new_users,
            'total_goals': total_goals,
            'total_saved': round(total_saved, 2),
            'total_budgets': total_budgets,
            'total_families': total_families,
        }

    # ── System Analytics (Charts) ──────────────────────────────────────────

    @staticmethod
    def get_system_analytics() -> dict:
        """Return chart-ready data for admin dashboard."""
        now = datetime.utcnow()

        # Monthly expense totals (last 6 months)
        monthly_labels = []
        monthly_totals = []
        monthly_counts = []
        for i in range(5, -1, -1):
            dt = now - timedelta(days=30 * i)
            start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if dt.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)

            total = db.session.query(
                func.coalesce(func.sum(Expense.amount), 0)
            ).filter(Expense.date >= start, Expense.date < end).scalar()

            count = db.session.query(func.count(Expense.id)).filter(
                Expense.date >= start, Expense.date < end
            ).scalar() or 0

            monthly_labels.append(start.strftime('%b %Y'))
            monthly_totals.append(round(total, 2))
            monthly_counts.append(count)

        # User growth (last 6 months)
        user_growth_labels = []
        user_growth_data = []
        for i in range(5, -1, -1):
            dt = now - timedelta(days=30 * i)
            start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if dt.month == 12:
                end = start.replace(year=start.year + 1, month=1)
            else:
                end = start.replace(month=start.month + 1)

            count = db.session.query(func.count(User.id)).filter(
                User.created_at >= start, User.created_at < end
            ).scalar() or 0

            user_growth_labels.append(start.strftime('%b %Y'))
            user_growth_data.append(count)

        # Global category breakdown (all time)
        category_query = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total')
        ).group_by(Expense.category).order_by(desc('total')).all()

        category_labels = [r[0] for r in category_query]
        category_data = [round(r[1], 2) for r in category_query]

        return {
            'monthly_labels': monthly_labels,
            'monthly_totals': monthly_totals,
            'monthly_counts': monthly_counts,
            'user_growth_labels': user_growth_labels,
            'user_growth_data': user_growth_data,
            'category_labels': category_labels,
            'category_data': category_data,
        }

    # ── User Management ────────────────────────────────────────────────────

    @staticmethod
    def get_all_users(search: str = '', sort: str = 'newest') -> list:
        """Return all users with their expense stats."""
        query = db.session.query(
            User,
            func.count(Expense.id).label('expense_count'),
            func.coalesce(func.sum(Expense.amount), 0).label('total_spent')
        ).outerjoin(Expense, User.id == Expense.user_id).group_by(User.id)

        if search:
            term = f'%{search.strip()}%'
            query = query.filter(
                db.or_(
                    User.username.ilike(term),
                    User.email.ilike(term),
                )
            )

        sort_map = {
            'newest': User.created_at.desc(),
            'oldest': User.created_at.asc(),
            'name': User.username.asc(),
            'most_expenses': desc('expense_count'),
            'highest_spent': desc('total_spent'),
        }
        query = query.order_by(sort_map.get(sort, User.created_at.desc()))

        results = query.all()
        users = []
        for user, exp_count, total_spent in results:
            users.append({
                'user': user,
                'expense_count': exp_count,
                'total_spent': round(total_spent, 2),
            })
        return users

    @staticmethod
    def get_user_detail(user_id: int) -> dict | None:
        """Return full user detail with expense breakdown."""
        user = db.session.get(User, user_id)
        if not user:
            return None

        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Expense stats
        total_expenses = db.session.query(func.count(Expense.id)).filter(
            Expense.user_id == user_id
        ).scalar() or 0

        total_spent = db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        ).filter(Expense.user_id == user_id).scalar()

        month_spent = db.session.query(
            func.coalesce(func.sum(Expense.amount), 0)
        ).filter(
            Expense.user_id == user_id,
            Expense.date >= month_start
        ).scalar()

        # Category breakdown
        cat_query = db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total')
        ).filter(
            Expense.user_id == user_id
        ).group_by(Expense.category).order_by(desc('total')).all()

        categories = {r[0]: round(r[1], 2) for r in cat_query}

        # Recent expenses
        recent = Expense.query.filter_by(user_id=user_id).order_by(
            Expense.date.desc()
        ).limit(20).all()

        # Savings goals
        goals = SavingsGoal.query.filter_by(user_id=user_id).all()

        # Budgets
        budgets = Budget.query.filter_by(user_id=user_id).order_by(
            Budget.year.desc(), Budget.month.desc()
        ).limit(10).all()

        return {
            'user': user,
            'total_expenses': total_expenses,
            'total_spent': round(total_spent, 2),
            'month_spent': round(month_spent, 2),
            'categories': categories,
            'recent_expenses': recent,
            'goals': goals,
            'budgets': budgets,
        }

    @staticmethod
    def delete_user(user_id: int) -> tuple[bool, str]:
        """Delete a user and all their data. Prevents deleting admin."""
        user = db.session.get(User, user_id)
        if not user:
            return False, 'User not found.'
        if user.is_admin:
            return False, 'Cannot delete the admin account.'

        try:
            # Delete in order due to FK constraints
            SavingsContribution.query.filter_by(user_id=user_id).delete()
            SavingsGoal.query.filter_by(user_id=user_id).delete()
            Budget.query.filter_by(user_id=user_id).delete()
            FamilyMember.query.filter_by(user_id=user_id).delete()
            Expense.query.filter_by(user_id=user_id).delete()
            db.session.delete(user)
            db.session.commit()
            return True, 'User deleted successfully.'
        except Exception as e:
            db.session.rollback()
            return False, f'Error: {str(e)}'

    # ── Expense Management ─────────────────────────────────────────────────

    @staticmethod
    def get_all_expenses(search: str = '', user_id: int = None,
                         category: str = '', sort: str = 'newest',
                         limit: int = 100) -> list:
        """Return expenses across all users with optional filters."""
        query = db.session.query(Expense, User.username).join(
            User, Expense.user_id == User.id
        )

        if search:
            term = f'%{search.strip()}%'
            query = query.filter(
                db.or_(
                    Expense.name.ilike(term),
                    Expense.description.ilike(term),
                    User.username.ilike(term),
                )
            )

        if user_id:
            query = query.filter(Expense.user_id == user_id)

        if category and category != 'all':
            query = query.filter(Expense.category == category)

        sort_map = {
            'newest': Expense.date.desc(),
            'oldest': Expense.date.asc(),
            'highest': Expense.amount.desc(),
            'lowest': Expense.amount.asc(),
        }
        query = query.order_by(sort_map.get(sort, Expense.date.desc()))

        results = query.limit(limit).all()
        return [{'expense': exp, 'username': uname} for exp, uname in results]

    @staticmethod
    def delete_expense(expense_id: int) -> tuple[bool, str]:
        """Admin force-delete any expense."""
        expense = db.session.get(Expense, expense_id)
        if not expense:
            return False, 'Expense not found.'
        try:
            db.session.delete(expense)
            db.session.commit()
            return True, 'Expense deleted.'
        except Exception as e:
            db.session.rollback()
            return False, f'Error: {str(e)}'

    # ── Recent Activity ────────────────────────────────────────────────────

    @staticmethod
    def get_recent_users(limit: int = 5) -> list:
        """Return recently registered users."""
        return User.query.order_by(User.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_recent_expenses(limit: int = 10) -> list:
        """Return most recent expenses across all users."""
        results = db.session.query(Expense, User.username).join(
            User, Expense.user_id == User.id
        ).order_by(Expense.date.desc()).limit(limit).all()
        return [{'expense': exp, 'username': uname} for exp, uname in results]
