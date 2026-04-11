from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from services.budget_service import BudgetService
from utils.category_detector import get_all_categories

budgets_bp = Blueprint('budgets', __name__, url_prefix='/budgets')


@budgets_bp.route('/')
@login_required
def index():
    now    = datetime.now()
    year   = request.args.get('year',  default=now.year,  type=int)
    month  = request.args.get('month', default=now.month, type=int)

    status     = BudgetService.get_budget_status(current_user.id, year, month)
    categories = get_all_categories()

    months = [
        {'year': now.year, 'month': m,
         'label': datetime(now.year, m, 1).strftime('%B %Y')}
        for m in range(1, 13)
    ]

    return render_template('budgets.html',
                           status       = status,
                           categories   = categories,
                           months       = months,
                           current_year = year,
                           current_month= month,
                           now          = now)


@budgets_bp.route('/set', methods=['POST'])
@login_required
def set_budget():
    amount   = request.form.get('amount',   type=float)
    month    = request.form.get('month',    default=datetime.now().month, type=int)
    year     = request.form.get('year',     default=datetime.now().year,  type=int)
    category = request.form.get('category', '').strip() or None

    if not amount or amount <= 0:
        flash('Please enter a valid budget amount.', 'danger')
        return redirect(url_for('budgets.index', year=year, month=month))

    BudgetService.set_budget(current_user.id, amount, month, year, category)
    label = category or 'Overall'
    flash(f'{label} budget set to ₹{amount:,.0f} for {datetime(year, month, 1).strftime("%B %Y")}.', 'success')
    return redirect(url_for('budgets.index', year=year, month=month))


@budgets_bp.route('/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_budget(budget_id):
    success = BudgetService.delete_budget(budget_id, current_user.id)
    if success:
        flash('Budget removed.', 'info')
    return redirect(url_for('budgets.index'))


@budgets_bp.route('/api/status')
@login_required
def budget_status_api():
    now   = datetime.now()
    year  = request.args.get('year',  default=now.year,  type=int)
    month = request.args.get('month', default=now.month, type=int)
    status = BudgetService.get_budget_status(current_user.id, year, month)
    return jsonify(status)
