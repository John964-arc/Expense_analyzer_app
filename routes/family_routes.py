from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from services.family_service import FamilyService
from models.expense_model import db

family_bp = Blueprint('family', __name__, url_prefix='/family')

@family_bp.route('/')
@login_required
def index():
    """Landing page: Redirect to dashboard if in group, else show setup."""
    group = FamilyService.get_user_group(current_user.id)
    if group:
        return redirect(url_for('family.dashboard'))
    return render_template('family/setup.html')

@family_bp.route('/dashboard')
@login_required
def dashboard():
    """Family spending overview."""
    group = FamilyService.get_user_group(current_user.id)
    if not group:
        return redirect(url_for('family.index'))
    
    data = FamilyService.get_family_dashboard_data(group.id)
    return render_template('family/dashboard.html', group=group, data=data)

@family_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Handle family group creation."""
    name = request.form.get('name')
    if not name:
        flash('Group name is required.', 'danger')
        return redirect(url_for('family.index'))
    
    group = FamilyService.create_group(current_user.id, name)
    flash(f'Family group "{group.name}" created! Invite code: {group.invite_code}', 'success')
    return redirect(url_for('family.dashboard'))

@family_bp.route('/join', methods=['POST'])
@login_required
def join():
    """Handle joining an existing group."""
    code = request.form.get('invite_code')
    if not code:
        flash('Invite code is required.', 'danger')
        return redirect(url_for('family.index'))
    
    group, error = FamilyService.join_group(current_user.id, code)
    if error:
        flash(error, 'danger')
        return redirect(url_for('family.index'))
    
    flash(f'Joined "{group.name}" family group!', 'success')
    return redirect(url_for('family.dashboard'))

@family_bp.route('/members')
@login_required
def members():
    """List members of the family group."""
    group = FamilyService.get_user_group(current_user.id)
    if not group:
        return redirect(url_for('family.index'))
    
    return render_template('family/members.html', group=group)
