from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from services.subscription_service import SubscriptionService

subscriptions_bp = Blueprint('subscriptions', __name__, url_prefix='/subscriptions')


@subscriptions_bp.route('/')
@login_required
def index():
    summary = SubscriptionService.get_summary(current_user.id)
    return render_template('subscriptions.html', summary=summary)


@subscriptions_bp.route('/api/summary')
@login_required
def summary_api():
    return jsonify(SubscriptionService.get_summary(current_user.id))


@subscriptions_bp.route('/api/reminders')
@login_required
def reminders_api():
    days = request.args.get('days', default=7, type=int)
    reminders = SubscriptionService.get_upcoming_reminders(current_user.id, days)
    return jsonify(reminders)
