from datetime import datetime, timedelta
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def login_required_custom(f):
    """Custom login required decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def format_currency(amount: float) -> str:
    """Format a number as currency string."""
    return f"₹{amount:,.2f}"


def get_month_range(year: int, month: int):
    """Get start and end datetime for a given month."""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(seconds=1)
    return start, end


def get_week_ranges(year: int, month: int) -> list:
    """Get weekly ranges within a month."""
    start, end = get_month_range(year, month)
    weeks = []
    current = start
    week_num = 1
    while current <= end:
        week_end = min(current + timedelta(days=6), end)
        weeks.append({
            'label': f'Week {week_num}',
            'start': current,
            'end': week_end
        })
        current = week_end + timedelta(days=1)
        week_num += 1
    return weeks


def months_list(num_months: int = 6) -> list:
    """Return list of (year, month) tuples for past N months."""
    now = datetime.now()
    result = []
    for i in range(num_months - 1, -1, -1):
        month = now.month - i
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        result.append((year, month))
    return result


def month_label(year: int, month: int) -> str:
    """Return readable month label like 'Jan 2024'."""
    return datetime(year, month, 1).strftime('%b %Y')


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def safe_float(value, default=0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to max_length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'
