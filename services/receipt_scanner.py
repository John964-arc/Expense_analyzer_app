"""
Receipt Scanner Service
Extracts amount and vendor from uploaded receipt images.
Uses basic image analysis via Pillow (no system-level OCR dependency).
For production, swap in pytesseract or a cloud Vision API.
"""
import re
import os
from PIL import Image


class ReceiptScanner:

    AMOUNT_PATTERNS = [
        r'(?:total|amount|due|pay|charged?|grand\s*total)\s*[:₹]?\s*(\d{1,6}(?:[.,]\d{2})?)',
        r'₹\s*(\d{1,6}(?:[.,]\d{2})?)',
        r'(\d{1,6}\.\d{2})\s*(?:INR|inr)?',
    ]

    VENDOR_PATTERNS = [
        r'^([A-Z][A-Z\s&\'\-]{2,30})$',
        r'(?:store|restaurant|cafe|shop|market|mart)[\s:]+([A-Za-z\s]+)',
    ]

    @staticmethod
    def scan(image_path: str) -> dict:
        """
        Attempt to extract expense data from a receipt image.
        Returns dict with keys: vendor, amount, raw_text, success.
        """
        result = {'vendor': None, 'amount': None, 'raw_text': '', 'success': False}

        if not os.path.exists(image_path):
            result['error'] = 'Image file not found'
            return result

        try:
            # Verify image is valid
            with Image.open(image_path) as img:
                width, height = img.size
                result['image_size'] = f"{width}x{height}"

            # Attempt OCR if pytesseract is installed
            try:
                import pytesseract
                with Image.open(image_path) as img:
                    # Preprocess: convert to grayscale
                    gray = img.convert('L')
                    raw_text = pytesseract.image_to_string(gray)
                    result['raw_text'] = raw_text
                    result['vendor'] = ReceiptScanner._extract_vendor(raw_text)
                    result['amount'] = ReceiptScanner._extract_amount(raw_text)
                    result['success'] = True
            except ImportError:
                # pytesseract not installed — return placeholder
                result['raw_text'] = '[OCR not available — install pytesseract for full scanning]'
                result['vendor'] = 'Unknown Vendor'
                result['amount'] = 0.0
                result['success'] = False
                result['note'] = 'Install pytesseract and Tesseract OCR for receipt scanning'

        except Exception as e:
            result['error'] = str(e)

        return result

    @staticmethod
    def _extract_amount(text: str) -> float:
        """Extract the most likely total amount from receipt text."""
        text_lower = text.lower()
        for pattern in ReceiptScanner.AMOUNT_PATTERNS:
            matches = re.findall(pattern, text_lower)
            if matches:
                amounts = []
                for m in matches:
                    try:
                        amounts.append(float(m.replace(',', '.')))
                    except ValueError:
                        pass
                if amounts:
                    return max(amounts)
        return 0.0

    @staticmethod
    def _extract_vendor(text: str) -> str:
        """Extract vendor/store name from receipt text."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for line in lines[:5]:
            for pattern in ReceiptScanner.VENDOR_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    return match.group(1).title().strip()
        return lines[0].title() if lines else 'Unknown Vendor'
