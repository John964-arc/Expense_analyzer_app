from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from services.savings_service import SavingsService

savings_bp = Blueprint('savings', __name__, url_prefix='/savings')

GOAL_ICONS = ['🎯', '✈️', '💻', '🏖️', '🚗', '🏠', '📱', '🎓', '💍', '🎮', '🏋️', '💰']
GOAL_COLORS = ['#6C63FF', '#22C55E', '#F59E0B', '#EF4444', '#06B6D4', '#EC4899',
               '#8B5CF6', '#14B8A6', '#F97316', '#3B82F6', '#84CC16', '#A855F7']


@savings_bp.route('/')
@login_required
def index():
    summary = SavingsService.get_goals_summary(current_user.id)
    return render_template('savings.html',
                           summary    = summary,
                           goal_icons = GOAL_ICONS,
                           goal_colors= GOAL_COLORS)


@savings_bp.route('/create', methods=['POST'])
@login_required
def create_goal():
    name          = request.form.get('name', '').strip()
    target_amount = request.form.get('target_amount', type=float)
    target_date   = request.form.get('target_date', '')
    icon          = request.form.get('icon', '🎯')
    color         = request.form.get('color', '#6C63FF')

    if not name or not target_amount or target_amount <= 0:
        flash('Please provide a valid goal name and target amount.', 'danger')
        return redirect(url_for('savings.index'))

    SavingsService.create_goal(current_user.id, name, target_amount, target_date, icon, color)
    flash(f'Savings goal "{name}" created! Keep saving!', 'success')
    return redirect(url_for('savings.index'))


@savings_bp.route('/<int:goal_id>/contribute', methods=['POST'])
@login_required
def add_contribution(goal_id):
    amount = request.form.get('amount', type=float)
    note   = request.form.get('note', '').strip()

    if not amount or amount <= 0:
        flash('Please enter a valid contribution amount.', 'danger')
        return redirect(url_for('savings.index'))

    try:
        contrib = SavingsService.add_contribution(goal_id, current_user.id, amount, note)
        flash(f'₹{amount:,.0f} added to your savings goal!', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('savings.index'))


@savings_bp.route('/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete_goal(goal_id):
    success = SavingsService.delete_goal(goal_id, current_user.id)
    if success:
        flash('Savings goal deleted.', 'info')
    return redirect(url_for('savings.index'))


@savings_bp.route('/api/summary')
@login_required
def summary_api():
    return jsonify(SavingsService.get_goals_summary(current_user.id))
