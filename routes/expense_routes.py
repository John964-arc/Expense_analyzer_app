import os
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, current_app, send_file)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from services.expense_service  import ExpenseService
from services.analysis_service import AnalysisService
from services.receipt_scanner  import ReceiptScanner
from services.export_service   import ExportService
from services.currency_service import CurrencyService
from utils.category_detector   import get_all_categories
from utils.helpers              import allowed_file, months_list, month_label

expenses_bp = Blueprint('expenses', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@expenses_bp.route('/')
@expenses_bp.route('/dashboard')
@login_required
def dashboard():
    data = AnalysisService.get_dashboard_data(current_user.id)
    return render_template('dashboard.html', data=data, now=datetime.now())


# ─────────────────────────────────────────────────────────────────────────────
# ADD EXPENSE
# ─────────────────────────────────────────────────────────────────────────────

@expenses_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    categories = get_all_categories()
    currencies = current_app.config.get('SUPPORTED_CURRENCIES', ['INR'])

    context_month = request.args.get('context_month', type=int)
    context_year  = request.args.get('context_year',  type=int)

    default_date = datetime.now()
    if context_month and context_year:
        try:
            default_date = datetime(context_year, context_month, 1)
        except ValueError:
            pass

    if request.method == 'POST':
        name          = request.form.get('name', '').strip()
        amount_str    = request.form.get('amount', '0')
        date_str      = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        description   = request.form.get('description', '').strip()
        category      = request.form.get('category', 'auto')
        currency      = request.form.get('currency', 'INR').upper()
        is_recurring  = bool(request.form.get('is_recurring'))
        recurring_day = request.form.get('recurring_day', type=int)
        receipt_image = None

        # Validation
        errors = []
        if not name:
            errors.append('Expense name is required.')
        try:
            amount = float(amount_str)
            if amount <= 0:
                errors.append('Amount must be greater than zero.')
        except ValueError:
            errors.append('Invalid amount.')
            amount = 0

        # Handle receipt upload
        if 'receipt' in request.files:
            file = request.files['receipt']
            if file and file.filename:
                if allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
                    filename   = secure_filename(file.filename)
                    upload_dir = current_app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_dir, exist_ok=True)
                    filepath   = os.path.join(upload_dir, filename)
                    file.save(filepath)
                    scan = ReceiptScanner.scan(filepath)
                    receipt_image = filename
                    if scan.get('success'):
                        if not name:
                            name = scan.get('vendor', name)
                        if scan.get('amount', 0) > 0 and amount == 0:
                            amount = scan['amount']
                        flash(f'Receipt scanned: {scan.get("vendor","Unknown")} — ₹{scan.get("amount",0):.2f}', 'info')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('add_expense.html', categories=categories,
                                   currencies=currencies, today=default_date.strftime('%Y-%m-%d'))

        # Currency conversion — convert to user's base currency
        base_currency    = getattr(current_user, 'base_currency', 'INR') or 'INR'
        converted_amount = None
        if currency != base_currency:
            try:
                converted_amount = CurrencyService.convert(amount, currency, base_currency)
            except Exception:
                converted_amount = None

        expense = ExpenseService.add_expense(
            user_id          = current_user.id,
            name             = name,
            amount           = amount,
            date_str         = date_str,
            description      = description,
            category         = category if category != 'auto' else None,
            receipt_image    = receipt_image,
            currency         = currency,
            converted_amount = converted_amount,
            is_recurring     = is_recurring,
            recurring_day    = recurring_day if is_recurring else None,
        )
        flash(f'Expense "{expense.name}" added to {expense.category}!', 'success')
        return redirect(url_for('expenses.all_transactions',
                                month=expense.date.month, year=expense.date.year))

    return render_template('add_expense.html', categories=categories,
                           currencies=currencies,
                           today=default_date.strftime('%Y-%m-%d'))


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTIONS — with search & sort
# ─────────────────────────────────────────────────────────────────────────────

@expenses_bp.route('/transactions')
@login_required
def all_transactions():
    year     = request.args.get('year',     default=datetime.now().year,  type=int)
    month    = request.args.get('month',    default=datetime.now().month, type=int)
    query    = request.args.get('q',        default='',  type=str)
    category = request.args.get('category', default='all')
    sort     = request.args.get('sort',     default='newest')

    if query or category != 'all' or sort != 'newest':
        expenses = ExpenseService.search(
            user_id  = current_user.id,
            query    = query,
            category = category,
            sort     = sort,
            year     = year,
            month    = month,
        )
    else:
        expenses = ExpenseService.get_expenses_by_month(current_user.id, year, month)

    available_months = [
        {'year': y, 'month': m, 'label': month_label(y, m)}
        for y, m in months_list(12)
    ]
    total      = sum(e.amount for e in expenses)
    categories = get_all_categories()

    return render_template('all_expenses.html',
                           expenses         = expenses,
                           current_year     = year,
                           current_month    = month,
                           available_months = available_months,
                           total            = total,
                           categories       = categories,
                           current_q        = query,
                           current_cat      = category,
                           current_sort     = sort)


# ─────────────────────────────────────────────────────────────────────────────
# EXPENSE CRUD  (JSON APIs)
# ─────────────────────────────────────────────────────────────────────────────

@expenses_bp.route('/expenses')
@login_required
def list_expenses():
    expenses = ExpenseService.get_user_expenses(current_user.id)
    return jsonify([e.to_dict() for e in expenses])


@expenses_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    success = ExpenseService.delete_expense(expense_id, current_user.id)
    return jsonify({'success': success})


@expenses_bp.route('/expenses/<int:expense_id>/toggle-recurring', methods=['POST'])
@login_required
def toggle_recurring(expense_id):
    data          = request.get_json() or {}
    recurring_day = data.get('recurring_day')
    expense       = ExpenseService.toggle_recurring(expense_id, current_user.id, recurring_day)
    if not expense:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({'success': True, 'is_recurring': expense.is_recurring})


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

@expenses_bp.route('/export/csv')
@login_required
def export_csv():
    year     = request.args.get('year',  default=datetime.now().year,  type=int)
    month    = request.args.get('month', default=datetime.now().month, type=int)
    category = request.args.get('category', default='all')

    expenses = ExpenseService.get_expenses_by_month(current_user.id, year, month)
    if category != 'all':
        expenses = [e for e in expenses if e.category == category]

    label  = month_label(year, month)
    buf    = ExportService.generate_csv(expenses, label)
    fname  = f'expenses_{year}_{month:02d}.csv'
    return send_file(buf, mimetype='text/csv',
                     as_attachment=True, download_name=fname)


@expenses_bp.route('/export/pdf')
@login_required
def export_pdf():
    year     = request.args.get('year',  default=datetime.now().year,  type=int)
    month    = request.args.get('month', default=datetime.now().month, type=int)
    category = request.args.get('category', default='all')

    expenses = ExpenseService.get_expenses_by_month(current_user.id, year, month)
    if category != 'all':
        expenses = [e for e in expenses if e.category == category]

    label          = month_label(year, month)
    cat_totals     = {}
    for e in expenses:
        cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount

    buf   = ExportService.generate_pdf(expenses, current_user.username, label, cat_totals)
    fname = f'expenses_{year}_{month:02d}.pdf'
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True, download_name=fname)


# ─────────────────────────────────────────────────────────────────────────────
# CURRENCY API
# ─────────────────────────────────────────────────────────────────────────────

@expenses_bp.route('/api/currency/rates')
@login_required
def currency_rates():
    base  = request.args.get('base', 'INR').upper()
    try:
        rates = CurrencyService.get_rates(base)
        return jsonify({'base': base, 'rates': rates, 'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD DATA  (JSON)
# ─────────────────────────────────────────────────────────────────────────────

@expenses_bp.route('/api/dashboard-data')
@login_required
def dashboard_data_api():
    data = AnalysisService.get_dashboard_data(current_user.id)
    return jsonify(data)
