import re
import csv
import json
import hashlib
from datetime import datetime
from io import StringIO
from models.expense_model import Expense, db

class SMSService:
    # ─── Configuration ────────────────────────────────────────────────────────
    
    # Common keywords for Indian banking SMS
    KEYWORDS = r'(?i)debited|credited|INR|Rs|paid|UPI|spent|purchase'
    AMOUNT_PATTERN = r'(?i)(?:INR|Rs\.?|INR\.)\s*([\d,]+\.?\d*)'
    DEBIT_KEYWORDS = ['debited', 'paid', 'spent', 'purchase', 'sent']
    CREDIT_KEYWORDS = ['credited', 'received', 'added']

    @staticmethod
    def parse_file(file_content, file_extension):
        """
        Parses the uploaded file and extracts potential transactions.
        Returns a list of dictionaries with extracted data.
        """
        if file_extension == '.json':
            return SMSService._parse_json(file_content)
        elif file_extension == '.csv':
            return SMSService._parse_csv(file_content)
        else: # Default to TXT
            return SMSService._parse_txt(file_content)

    @staticmethod
    def _parse_txt(content):
        """Line-by-line regex parsing for raw text files."""
        transactions = []
        lines = content.splitlines()
        
        for line in lines:
            if not line.strip(): continue
            tx = SMSService._extract_from_text(line)
            if tx:
                transactions.append(tx)
        
        return transactions

    @staticmethod
    def _parse_csv(content):
        """Parse CSV files, looking for columns that might contain SMS body."""
        transactions = []
        f = StringIO(content)
        reader = csv.DictReader(f)
        
        for row in reader:
            # Combine all column values to search for transaction details
            combined_text = " ".join(row.values())
            tx = SMSService._extract_from_text(combined_text)
            if tx:
                # Try to get timestamp from row if possible
                for key in row:
                    if 'date' in key.lower() or 'time' in key.lower():
                        try:
                            tx['date'] = row[key]
                            break
                        except: pass
                transactions.append(tx)
        
        return transactions

    @staticmethod
    def _parse_json(content):
        """Parse JSON files (common for SMS Backup apps)."""
        transactions = []
        try:
            data = json.loads(content)
            # Support both list of objects and nested 'sms' lists
            items = data if isinstance(data, list) else data.get('sms', [])
            
            for item in items:
                body = item.get('body', "") or item.get('message', "")
                tx = SMSService._extract_from_text(body)
                if tx:
                    # Prefer date from JSON metadata if available
                    if 'date' in item:
                        try:
                            # Convert ms timestamp if needed
                            dt = datetime.fromtimestamp(int(item['date'])/1000)
                            tx['date'] = dt.strftime('%Y-%m-%d %H:%M')
                        except: pass
                    transactions.append(tx)
        except:
            pass
        return transactions

    @staticmethod
    def _extract_from_text(text):
        """Core extraction logic using regex."""
        # Check for keywords first
        if not re.search(SMSService.KEYWORDS, text):
            return None

        # 1. Extract Amount
        amount_match = re.search(SMSService.AMOUNT_PATTERN, text)
        if not amount_match:
            return None
        
        amount_str = amount_match.group(1).replace(',', '')
        try:
            amount = float(amount_str)
        except ValueError:
            return None

        # 2. Extract Transaction Type
        tx_type = 'Expense' # Default
        if any(kw in text.lower() for kw in SMSService.CREDIT_KEYWORDS):
            tx_type = 'Income'
        elif any(kw in text.lower() for kw in SMSService.DEBIT_KEYWORDS):
            tx_type = 'Expense'

        # 3. Extract Merchant (Rudimentary logic: look for "at [Merchant]" or "to [Merchant]")
        merchant = "Unknown Merchant"
        merchant_match = re.search(r'(?i)(?:at|to|from|for|info)\s+([A-Z0-9\s*]{3,20})(?:\s|on|at|ref|$)', text)
        if merchant_match:
            merchant = merchant_match.group(1).strip()
        
        # 4. Handle Date (Try to find DD-MM-YY or similar)
        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
        date_str = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')

        return {
            'amount': amount,
            'name': merchant,
            'date': date_str,
            'type': tx_type,
            'raw_text': text[:200], # Keep snippet for reference
            'import_hash': SMSService._generate_hash(date_str, amount, merchant)
        }

    @staticmethod
    def _generate_hash(date_str, amount, name):
        """Generate deduplication hash."""
        raw = f"{date_str}|{amount}|{name.lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def check_duplicate(user_id, import_hash):
        """Check if this transaction already exists for the user."""
        return Expense.query.filter_by(user_id=user_id, import_hash=import_hash).first() is not None
