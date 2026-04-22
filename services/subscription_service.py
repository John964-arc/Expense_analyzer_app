import re
from datetime import datetime, date, timedelta
from collections import defaultdict
from models.expense_model import Expense
from services.expense_service import ExpenseService


# Keywords that strongly suggest a recurring subscription
SUBSCRIPTION_KEYWORDS = [
    'netflix', 'spotify', 'amazon prime', 'prime', 'disney', 'hulu', 'youtube premium',
    'apple tv', 'hotstar', 'zee5', 'sonyliv', 'jiocinema',
    'gym', 'fitness', 'yoga studio', 'cult',
    'rent', 'mortgage', 'emi', 'loan',
    'electricity', 'water bill', 'gas bill', 'internet', 'wifi', 'broadband',
    'phone bill', 'mobile bill', 'postpaid', 'prepaid recharge',
    'insurance', 'premium', 'membership', 'subscription',
    'adobe', 'microsoft', 'google one', 'dropbox', 'github',
    'coursera', 'udemy', 'linkedin', 'medium', 'notion', 'canva'
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
        """
        Calculate total monthly fixed cost.
        Prorates WEEKLY (x4.33) and YEARLY (/12) to get a monthly average.
        """
        recurring = SubscriptionService.get_recurring_expenses(user_id)
        seen: dict = {}
        
        # Use only the latest item for each unique subscription_name or normalized name
        for e in recurring:
            key = (e.subscription_name or e.name).strip().lower()
            if key not in seen:
                # Prorate
                amount = e.amount
                if e.recurring_type == 'WEEKLY':
                    amount *= 4.33
                elif e.recurring_type == 'YEARLY':
                    amount /= 12
                seen[key] = amount
        
        return round(sum(seen.values()), 2)

    @staticmethod
    def get_detected_candidates(user_id: int) -> list:
        """
        AI Detector: Finds patterns (same amount + similar merchant) + keywords.
        """
        all_expenses = ExpenseService.get_user_expenses(user_id)
        candidates = []
        
        # 1. Group by (Rounded Amount, Normalized Name)
        patterns = defaultdict(list)
        for e in all_expenses:
            if e.is_recurring: continue
            norm_name = SubscriptionService._normalize_name(e.name)
            key = (round(e.amount, 0), norm_name)
            patterns[key].append(e)
            
        # 2. Analyze groups for frequency
        processed_keys = set()
        for key, logs in patterns.items():
            amount, norm_name = key
            if len(logs) < 2: continue # Need at least 2 occurrences
            
            # Check month-spread
            months = {l.date.strftime('%Y-%m') for l in logs}
            if len(months) < 2: continue
            
            # Detect Interval
            interval, reason = SubscriptionService._detect_interval(logs)
            if interval:
                latest = logs[0] # Newest first because get_user_expenses is DESC
                candidates.append({
                    **latest.to_dict(),
                    'reason': reason,
                    'detected_interval': interval,
                    'subscription_name_suggestion': norm_name.title()
                })
                processed_keys.add(key)

        # 3. Add Keyword-only candidates (if not already found by pattern)
        for e in all_expenses:
            if e.is_recurring: continue
            name_lower = e.name.strip().lower()
            norm_name = SubscriptionService._normalize_name(e.name)
            key = (round(e.amount, 0), norm_name)
            if key in processed_keys: continue
            
            matched = next((kw for kw in SUBSCRIPTION_KEYWORDS if kw in name_lower), None)
            if matched:
                candidates.append({
                    **e.to_dict(),
                    'reason': f'Matches keyword "{matched}"',
                    'detected_interval': 'MONTHLY',
                    'subscription_name_suggestion': matched.title()
                })
                processed_keys.add(key)
            
            if len(candidates) >= 15: break

        return candidates

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Strips dates, months, and numbers to find canonical merchant name."""
        name = name.lower()
        # Remove month names
        months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 
                  'august', 'september', 'october', 'november', 'december',
                  'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        for m in months:
            name = name.replace(m, "")
        
        # Remove years (2020-2029) and short numbers
        name = re.sub(r'20\d{2}', '', name)
        name = re.sub(r'\d+', '', name)
        
        # Clean special chars and extra spaces
        name = re.sub(r'[^a-z\s]', '', name)
        return name.strip()

    @staticmethod
    def _detect_interval(logs: list) -> (str, str):
        """Analyze gaps between dates to guess interval."""
        if len(logs) < 2: return None, None
        
        # Logs are sorted newest first
        dates = sorted([l.date for l in logs])
        gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        avg_gap = sum(gaps) / len(gaps)
        
        if 25 <= avg_gap <= 35:
            return 'MONTHLY', f'Consistent monthly pattern ({len(logs)} months)'
        elif 6 <= avg_gap <= 8:
            return 'WEEKLY', f'Seen {len(logs)} times, approx weekly'
        elif 350 <= avg_gap <= 380:
            return 'YEARLY', f'Annual pattern detected'
        
        return 'MONTHLY', f'Repeated transaction ({len(logs)} times)'

    @staticmethod
    def get_upcoming_reminders(user_id: int, days_ahead: int = 7) -> list:
        """
        Return recurring expenses whose recurring_day falls within
        the next `days_ahead` days from today.
        Only applies to MONTHLY subscriptions for now.
        """
        today      = date.today()
        month      = today.month
        year       = today.year
        reminders  = []

        recurring = SubscriptionService.get_recurring_expenses(user_id)
        for e in recurring:
            if not e.recurring_day or e.recurring_type != 'MONTHLY':
                continue
            try:
                # Handle end of month issues
                day = min(int(e.recurring_day), 28) # simpler safety
                due = date(year, month, day)
                if due < today:
                    # Look at next month
                    if month == 12: due = date(year+1, 1, day)
                    else: due = date(year, month+1, day)
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
            'monthly_total':     round(monthly, 2),
            'annual_total':      round(monthly * 12, 2),
            'count':             len(recurring),
            'candidates':        candidates,
            'reminders':         reminders,
        }
