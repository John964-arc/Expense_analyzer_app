"""
savings_service.py
──────────────────────────────────────────────
CRUD for savings goals and contributions.
Computes progress, ETA, and goal recommendations.
"""
from datetime import datetime, date, timedelta
from utils.db_helper import db
from models.expense_model import SavingsGoal, SavingsContribution


class SavingsService:

    # ── Goals ────────────────────────────────────────────────────────────────

    @staticmethod
    def create_goal(user_id: int, name: str, target_amount: float,
                    target_date: str = None, icon: str = '🎯',
                    color: str = '#6C63FF') -> SavingsGoal:
        parsed_date = None
        if target_date:
            try:
                parsed_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                pass

        goal = SavingsGoal(
            user_id       = user_id,
            name          = name.strip(),
            target_amount = round(float(target_amount), 2),
            target_date   = parsed_date,
            icon          = icon or '🎯',
            color         = color or '#6C63FF',
        )
        db.session.add(goal)
        db.session.commit()
        return goal

    @staticmethod
    def get_goals(user_id: int) -> list:
        return SavingsGoal.query.filter_by(
            user_id=user_id
        ).order_by(SavingsGoal.is_completed.asc(),
                   SavingsGoal.created_at.desc()).all()

    @staticmethod
    def delete_goal(goal_id: int, user_id: int) -> bool:
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()
        if goal:
            db.session.delete(goal)
            db.session.commit()
            return True
        return False

    # ── Contributions ─────────────────────────────────────────────────────────

    @staticmethod
    def add_contribution(goal_id: int, user_id: int,
                         amount: float, note: str = '') -> SavingsContribution:
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()
        if not goal:
            raise ValueError('Goal not found')

        contribution = SavingsContribution(
            goal_id = goal_id,
            user_id = user_id,
            amount  = round(float(amount), 2),
            note    = note.strip() if note else None,
        )
        db.session.add(contribution)

        goal.saved_amount = round(goal.saved_amount + contribution.amount, 2)
        if goal.saved_amount >= goal.target_amount:
            goal.is_completed = True

        db.session.commit()
        return contribution

    @staticmethod
    def get_contributions(goal_id: int, user_id: int) -> list:
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=user_id).first()
        if not goal:
            return []
        return SavingsContribution.query.filter_by(
            goal_id=goal_id
        ).order_by(SavingsContribution.date.desc()).all()

    # ── Analytics ─────────────────────────────────────────────────────────────

    @staticmethod
    def get_goals_summary(user_id: int) -> dict:
        """Aggregate savings summary for the dashboard widget."""
        goals = SavingsService.get_goals(user_id)
        active  = [g for g in goals if not g.is_completed]
        done    = [g for g in goals if g.is_completed]
        total_target = sum(g.target_amount for g in active)
        total_saved  = sum(g.saved_amount  for g in active)

        return {
            'total_goals':     len(goals),
            'active_goals':    len(active),
            'completed_goals': len(done),
            'total_target':    round(total_target, 2),
            'total_saved':     round(total_saved, 2),
            'overall_pct':     round((total_saved / total_target * 100) if total_target else 0, 1),
            'goals':           [SavingsService._enrich(g) for g in goals],
        }

    @staticmethod
    def _enrich(goal: SavingsGoal) -> dict:
        """Add ETA and monthly saving needed to a goal dict."""
        d = goal.to_dict()

        # ETA from contributions average
        monthly_rate = SavingsService._avg_monthly_rate(goal)
        if monthly_rate and monthly_rate > 0 and goal.remaining > 0:
            months_left = goal.remaining / monthly_rate
            eta_date    = date.today() + timedelta(days=int(months_left * 30.44))
            d['eta']    = eta_date.strftime('%b %Y')
            d['monthly_rate'] = round(monthly_rate, 2)
        elif goal.target_date and goal.remaining > 0:
            months_left = max(
                (goal.target_date - date.today()).days / 30.44, 1
            )
            d['monthly_rate'] = round(goal.remaining / months_left, 2)
            d['eta'] = goal.target_date.strftime('%b %Y')
        else:
            d['eta']          = None
            d['monthly_rate'] = 0

        return d

    @staticmethod
    def _avg_monthly_rate(goal: SavingsGoal) -> float:
        """Compute average monthly contribution for a goal."""
        contribs = goal.contributions
        if len(contribs) < 2:
            return 0.0
        dates  = sorted(c.date for c in contribs)
        span   = (dates[-1] - dates[0]).days
        months = max(span / 30.44, 1)
        total  = sum(c.amount for c in contribs)
        return total / months
