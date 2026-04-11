from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

def init_db(app):
    """Initialize database with the Flask app."""
    db.init_app(app)
    with app.app_context():
        import models.expense_model
        db.create_all()
        
        # Simple schema migration
        try:
            db.session.execute(text('ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255)'))
            db.session.commit()
        except Exception:
            db.session.rollback()
            
        _seed_sample_data()

def _seed_sample_data():
    """Seed database with sample data if empty."""
    from models.expense_model import User, Expense
    from werkzeug.security import generate_password_hash
    from datetime import datetime, timedelta
    import random

    # FIX: use db.session.execute instead of deprecated User.query.first()
    if db.session.execute(db.select(User).limit(1)).first():
        return  # Already seeded

    # Create demo user
    demo_user = User(
        username='demo',
        email='demo@example.com',
        password_hash=generate_password_hash('demo123')
    )
    db.session.add(demo_user)
    db.session.flush()

    # Sample expense data for 6 months
    categories = {
        'Food':          ['Groceries', 'Restaurant', 'Coffee', 'Pizza', 'Lunch', 'Dinner'],
        'Transport':     ['Uber', 'Gas', 'Bus ticket', 'Metro', 'Taxi', 'Parking'],
        'Shopping':      ['Amazon', 'Clothes', 'Electronics', 'Books', 'Shoes'],
        'Entertainment': ['Netflix', 'Cinema', 'Spotify', 'Games', 'Concert'],
        'Bills':         ['Electricity', 'Internet', 'Water bill', 'Rent', 'Phone bill'],
        'Health':        ['Gym', 'Medicine', 'Doctor', 'Pharmacy'],
    }

    base_date = datetime.now()
    expenses  = []

    for month_offset in range(6):
        month_date = base_date - timedelta(days=30 * month_offset)
        for category, names in categories.items():
            for _ in range(random.randint(3, 7)):
                day_offset   = random.randint(0, 28)
                expense_date = month_date.replace(day=1) + timedelta(days=day_offset)
                expenses.append(Expense(
                    user_id     = demo_user.id,
                    name        = random.choice(names),
                    amount      = round(random.uniform(5, 200), 2),
                    category    = category,
                    date        = expense_date,
                    description = f'Sample {category.lower()} expense'
                ))

    db.session.bulk_save_objects(expenses)
    db.session.commit()
