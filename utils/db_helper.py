from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()


def init_db(app):
    """Initialize database with the Flask app and run lightweight migrations."""
    db.init_app(app)
    with app.app_context():
        # Import ALL models so SQLAlchemy knows about every table
        import models.expense_model  # noqa: F401 (Budget, SavingsGoal, SavingsContribution included)

        db.create_all()  # Creates any new tables that don't yet exist

        # ── Column migrations for existing tables ───────────────────────────
        _run_migrations()

        # ── Seed demo data only when the DB is empty ────────────────────────
        _seed_sample_data()


def _run_migrations():
    """Safely add new columns / tables to already-existing SQLite databases."""
    migrations = [
        # Expense table — new columns
        'ALTER TABLE expenses ADD COLUMN currency VARCHAR(3) DEFAULT "INR"',
        'ALTER TABLE expenses ADD COLUMN converted_amount FLOAT',
        'ALTER TABLE expenses ADD COLUMN is_recurring BOOLEAN DEFAULT 0',
        'ALTER TABLE expenses ADD COLUMN recurring_day INTEGER',
        'ALTER TABLE expenses ADD COLUMN source VARCHAR(50) DEFAULT "manual"',
        'ALTER TABLE expenses ADD COLUMN import_hash VARCHAR(64)',
        'ALTER TABLE expenses ADD COLUMN family_id INTEGER',
        'ALTER TABLE expenses ADD COLUMN is_private BOOLEAN DEFAULT 1',
        'ALTER TABLE expenses ADD COLUMN recurring_type VARCHAR(20) DEFAULT "MONTHLY"',
        'ALTER TABLE expenses ADD COLUMN subscription_name VARCHAR(100)',
        # Users table — new columns
        'ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255)',
        'ALTER TABLE users ADD COLUMN base_currency VARCHAR(3) DEFAULT "INR"',
    ]
    for sql in migrations:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()


def _seed_sample_data():
    """Seed database with sample data if empty."""
    from models.expense_model import User, Expense
    from werkzeug.security import generate_password_hash
    from datetime import datetime, timedelta
    import random

    if db.session.execute(db.select(User).limit(1)).first():
        return  # Already seeded

    demo_user = User(
        username='demo',
        email='demo@example.com',
        password_hash=generate_password_hash('demo123')
    )
    db.session.add(demo_user)
    db.session.flush()

    categories = {
        'Food':          ['Groceries', 'Restaurant', 'Coffee', 'Pizza', 'Lunch', 'Dinner'],
        'Transport':     ['Uber', 'Gas', 'Bus ticket', 'Metro', 'Taxi', 'Parking'],
        'Shopping':      ['Amazon', 'Clothes', 'Electronics', 'Books', 'Shoes'],
        'Entertainment': ['Netflix', 'Cinema', 'Spotify', 'Games', 'Concert'],
        'Bills':         ['Electricity', 'Internet', 'Water bill', 'Rent', 'Phone bill'],
        'Health':        ['Gym', 'Medicine', 'Doctor', 'Pharmacy'],
    }

    # Some expenses are recurring for demo purposes
    recurring_names = {'Netflix', 'Spotify', 'Gym', 'Rent', 'Internet', 'Phone bill'}

    base_date = datetime.now()
    expenses  = []

    for month_offset in range(6):
        month_date = base_date - timedelta(days=30 * month_offset)
        for category, names in categories.items():
            for _ in range(random.randint(3, 7)):
                day_offset   = random.randint(0, 28)
                expense_date = month_date.replace(day=1) + timedelta(days=day_offset)
                chosen_name  = random.choice(names)
                expenses.append(Expense(
                    user_id          = demo_user.id,
                    name             = chosen_name,
                    amount           = round(random.uniform(5, 200), 2),
                    category         = category,
                    date             = expense_date,
                    description      = f'Sample {category.lower()} expense',
                    currency         = 'INR',
                    is_recurring     = chosen_name in recurring_names,
                    recurring_day    = 1 if chosen_name in recurring_names else None,
                ))

    db.session.bulk_save_objects(expenses)
    db.session.commit()
