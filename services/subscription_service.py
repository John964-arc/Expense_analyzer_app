"""
subscription_service.py
──────────────────────────────────────────────
Detects and manages recurring/subscription expenses.
Uses keyword matching for auto-detection; users can also flag manually.
"""
from datetime import datetime, date
from models.expense_model import Expense
from services.expense_service import ExpenseService


# Keywords that strongly suggest a recurring subscription
SUBSCRIPTION_KEYWORDS = [
    'netflix', 'spotify', 'amazon prime', 'prime', 'disney', 'hulu', 'youtube premium',
    'apple tv', 'hotstar', 'zee5', 'sonyliv', 'jiocinema',
    'gym', 'fitness', 'yoga studio',
    'rent', 'mortgage', 'emi', 'loan',
    'electricity', 'water bill', 'gas bill', 'internet', 'wifi', 'broadband',
    'phone bill', 'mobile bill', 'postpaid', 'prepaid recharge',
    'insurance', 'premium', 'membership', 'subscription',
    'adobe', 'microsoft', 'google one', 'dropbox', 'github',
    'coursera', 'udemy', 'linkedin', 'medium',
]


class SubscriptionService:

    @staticmethod
    def get_recurring_expenses(user_id: int) -> list:
        """Return all expenses marked as recurring for a user."""
        return (
            Expense.query
            .filter_by(user_id=user_id, is_recurring=True)
            .order_by(Expense.date.desc())
            .all()
        )

    @staticmethod
    def get_monthly_recurring_cost(user_id: int) -> float:
        """Approximate monthly cost of all recurring expenses.
        Uses the most recent occurrence amount for each unique name."""
        recurring = SubscriptionService.get_recurring_expenses(user_id)
        seen: dict = {}
        for e in recurring:
            key = e.name.strip().lower()
            if key not in seen:
                seen[key] = e.amount   # first occurrence = most recent (DESC order)
        return round(sum(seen.values()), 2)

    @staticmethod
    def get_detected_candidates(user_id: int) -> list:
        """
        Scan all expenses and flag ones that look like subscriptions
        but aren't yet marked as recurring.
        Returns up to 20 candidates with detection reason.
        """
        all_expenses = ExpenseService.get_user_expenses(user_id)
        candidates   = []
        seen_names   = set()

        for e in all_expenses:
            if e.is_recurring:
                continue
            name_lower = e.name.strip().lower()
            if name_lower in seen_names:
                continue
            matched = next(
                (kw for kw in SUBSCRIPTION_KEYWORDS if kw in name_lower),
                None
            )
            if matched:
                seen_names.add(name_lower)
                candidates.append({
                    **e.to_dict(),
                    'reason': f'Matches keyword "{matched}"',
                })
            if len(candidates) >= 20:
                break

        return candidates

    @staticmethod
    def get_upcoming_reminders(user_id: int, days_ahead: int = 7) -> list:
        """
        Return recurring expenses whose recurring_day falls within
        the next `days_ahead` days from today.
        """
        today      = date.today()
        month      = today.month
        year       = today.year
        reminders  = []

        recurring = SubscriptionService.get_recurring_expenses(user_id)
        for e in recurring:
            if not e.recurring_day:
                continue
            try:
                due = date(year, month, int(e.recurring_day))
            except ValueError:
                continue
            delta = (due - today).days
            if 0 <= delta <= days_ahead:
                reminders.append({
                    **e.to_dict(),
                    'due_date':   due.isoformat(),
                    'days_until': delta,
                })

        return sorted(reminders, key=lambda x: x['days_until'])

    @staticmethod
    def get_summary(user_id: int) -> dict:
        recurring  = SubscriptionService.get_recurring_expenses(user_id)
        monthly    = SubscriptionService.get_monthly_recurring_cost(user_id)
        candidates = SubscriptionService.get_detected_candidates(user_id)
        reminders  = SubscriptionService.get_upcoming_reminders(user_id)

        return {
            'recurring':         [e.to_dict() for e in recurring],
            'monthly_total':     monthly,
            'annual_total':      round(monthly * 12, 2),
            'count':             len(recurring),
            'candidates':        candidates,
            'reminders':         reminders,
        }
