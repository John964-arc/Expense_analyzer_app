"""
routes/admin_routes.py
======================
Admin-only routes for system management.
Completely hidden from regular users — non-admins are silently
redirected to their dashboard with no indication the panel exists.
"""

from functools import wraps
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify)
from flask_login import login_required, current_user

from services.admin_service import AdminService
from utils.category_detector import get_all_categories

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ─────────────────────────────────────────────────────────────────────────────
# Admin Guard Decorator
# ─────────────────────────────────────────────────────────────────────────────

def admin_required(f):
    """Decorator: requires login + admin status. Non-admins get silently redirected."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not getattr(current_user, 'is_admin', False):
            return redirect(url_for('expenses.dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/')
@admin_required
def dashboard():
    stats = AdminService.get_dashboard_stats()
    analytics = AdminService.get_system_analytics()
    recent_users = AdminService.get_recent_users(5)
    recent_expenses = AdminService.get_recent_expenses(8)
    return render_template('admin/dashboard.html',
                           stats=stats,
                           analytics=analytics,
                           recent_users=recent_users,
                           recent_expenses=recent_expenses)


# ─────────────────────────────────────────────────────────────────────────────
# USER MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/users')
@admin_required
def users():
    search = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'newest')
    users_data = AdminService.get_all_users(search=search, sort=sort)
    return render_template('admin/users.html',
                           users=users_data,
                           current_q=search,
                           current_sort=sort)


@admin_bp.route('/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    data = AdminService.get_user_detail(user_id)
    if not data:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_detail.html', data=data)


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    success, message = AdminService.delete_user(user_id)
    status = 200 if success else 400
    return jsonify({'success': success, 'message': message}), status


# ─────────────────────────────────────────────────────────────────────────────
# EXPENSE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/expenses')
@admin_required
def expenses():
    search = request.args.get('q', '').strip()
    user_id = request.args.get('user_id', type=int)
    category = request.args.get('category', 'all')
    sort = request.args.get('sort', 'newest')

    expenses_data = AdminService.get_all_expenses(
        search=search, user_id=user_id,
        category=category, sort=sort
    )
    categories = get_all_categories()

    # Get user list for filter dropdown
    all_users = AdminService.get_all_users()

    return render_template('admin/expenses.html',
                           expenses=expenses_data,
                           categories=categories,
                           all_users=all_users,
                           current_q=search,
                           current_user_id=user_id,
                           current_cat=category,
                           current_sort=sort)


@admin_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@admin_required
def delete_expense(expense_id):
    success, message = AdminService.delete_expense(expense_id)
    status = 200 if success else 400
    return jsonify({'success': success, 'message': message}), status


# ─────────────────────────────────────────────────────────────────────────────
# API — Dashboard Stats JSON
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    stats = AdminService.get_dashboard_stats()
    return jsonify(stats)
