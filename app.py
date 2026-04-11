import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from config import config
from utils.db_helper import db, init_db


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure directories exist
    os.makedirs(os.path.join(app.root_path, 'database'), exist_ok=True)
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)

    # Init DB
    init_db(app)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from models.expense_model import User
        return db.session.get(User, int(user_id))

    # ── Register blueprints ───────────────────────────────────────────────
    from routes.auth_routes         import auth_bp
    from routes.expense_routes      import expenses_bp
    from routes.chatbot_routes      import chatbot_bp
    from routes.budget_routes       import budgets_bp
    from routes.savings_routes      import savings_bp
    from routes.subscription_routes import subscriptions_bp

    app.register_blueprint(auth_bp,          url_prefix='/auth')
    app.register_blueprint(expenses_bp,      url_prefix='')
    app.register_blueprint(chatbot_bp,       url_prefix='')
    app.register_blueprint(budgets_bp)       # prefix='/budgets' set in blueprint
    app.register_blueprint(savings_bp)       # prefix='/savings'
    app.register_blueprint(subscriptions_bp) # prefix='/subscriptions'

    @app.route('/')
    def index():
        return redirect(url_for('expenses.dashboard'))

    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True, host='0.0.0.0', port=5000)
