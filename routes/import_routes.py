import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from services.sms_service import SMSService
from models.expense_model import Expense, db
from utils.category_detector import detect_category
from datetime import datetime

import_bp = Blueprint('imports', __name__, url_prefix='/import')

@import_bp.route('/', methods=['GET'])
@login_required
def index():
    return render_template('imports/import_transactions.html')

@import_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in ['.txt', '.csv', '.json']:
        flash('Unsupported file type. Please upload .txt, .csv, or .json', 'error')
        return redirect(request.url)

    try:
        content = file.read().decode('utf-8')
        raw_transactions = SMSService.parse_file(content, ext)
        
        # Enrich and check for duplicates
        processed = []
        for tx in raw_transactions:
            tx['is_duplicate'] = SMSService.check_duplicate(current_user.id, tx['import_hash'])
            # Auto-detect category
            tx['category'] = detect_category(tx['name'])
            processed.append(tx)

        return render_template('imports/import_transactions.html', 
                               transactions=processed, 
                               filename=filename)
    except Exception as e:
        flash(f'Error parsing file: {str(e)}', 'error')
        return redirect(request.url)

@import_bp.route('/save', methods=['POST'])
@login_required
def save():
    try:
        selected_txs = request.json.get('transactions', [])
        saved_count = 0
        duplicate_count = 0

        for tx_data in selected_txs:
            # Final deduplication check
            if SMSService.check_duplicate(current_user.id, tx_data['import_hash']):
                duplicate_count += 1
                continue

            # Parse date safely
            try:
                date_obj = datetime.strptime(tx_data['date'], '%Y-%m-%d')
            except:
                date_obj = datetime.utcnow()

            expense = Expense(
                user_id=current_user.id,
                name=tx_data['name'],
                amount=float(tx_data['amount']),
                category=tx_data['category'],
                date=date_obj,
                source='SMS Import',
                import_hash=tx_data['import_hash'],
                currency='INR'
            )
            # Add conversion if needed (assuming INR to base_currency)
            # For now keeping it simple as per requirements
            db.session.add(expense)
            saved_count += 1

        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully imported {saved_count} transactions. {duplicate_count} duplicates skipped.',
            'redirect': url_for('expenses.all_transactions')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
