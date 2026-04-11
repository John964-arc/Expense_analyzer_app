import re

CATEGORY_KEYWORDS = {
    'Food': [
        'grocery', 'groceries', 'restaurant', 'food', 'lunch', 'dinner', 'breakfast',
        'coffee', 'pizza', 'burger', 'sushi', 'cafe', 'bakery', 'snack', 'meal',
        'takeout', 'delivery', 'mcdonald', 'starbucks', 'subway', 'kfc', 'domino',
        'zomato', 'swiggy', 'doordash', 'ubereats', 'eat', 'drink', 'juice', 'tea'
    ],
    'Transport': [
        'uber', 'lyft', 'taxi', 'cab', 'bus', 'metro', 'subway', 'train', 'flight',
        'airline', 'airport', 'gas', 'petrol', 'fuel', 'parking', 'toll', 'transport',
        'travel', 'commute', 'ola', 'rapido', 'bike', 'ride', 'car', 'vehicle'
    ],
    'Shopping': [
        'amazon', 'flipkart', 'ebay', 'walmart', 'target', 'shopping', 'clothes',
        'clothing', 'shoes', 'fashion', 'electronics', 'gadget', 'phone', 'laptop',
        'book', 'online', 'purchase', 'order', 'store', 'market', 'mall', 'shop'
    ],
    'Entertainment': [
        'netflix', 'spotify', 'youtube', 'cinema', 'movie', 'theatre', 'concert',
        'game', 'gaming', 'steam', 'playstation', 'xbox', 'disney', 'hulu', 'prime',
        'entertainment', 'fun', 'leisure', 'hobby', 'music', 'subscription', 'streaming'
    ],
    'Bills': [
        'electricity', 'electric', 'water', 'gas bill', 'internet', 'wifi', 'broadband',
        'phone bill', 'mobile', 'rent', 'mortgage', 'insurance', 'tax', 'utility',
        'utilities', 'bill', 'payment', 'emi', 'loan', 'credit card'
    ],
    'Health': [
        'gym', 'fitness', 'doctor', 'hospital', 'medicine', 'pharmacy', 'drug',
        'health', 'medical', 'dental', 'eye', 'clinic', 'therapy', 'vitamin',
        'supplement', 'yoga', 'workout', 'wellness'
    ],
    'Education': [
        'school', 'college', 'university', 'course', 'class', 'tuition', 'education',
        'learning', 'udemy', 'coursera', 'book', 'textbook', 'training', 'workshop'
    ],
}

def detect_category(name: str, description: str = '') -> str:
    """
    Detect expense category from name and description using keyword matching.
    Returns category string or 'Other' if no match found.
    """
    text = f"{name} {description}".lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    words = text.split()

    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            keyword_words = keyword.lower().split()
            if len(keyword_words) == 1:
                if keyword in words:
                    scores[category] += 2
                elif any(keyword in word for word in words):
                    scores[category] += 1
            else:
                if keyword in text:
                    scores[category] += 3

    best_category = max(scores, key=scores.get)
    return best_category if scores[best_category] > 0 else 'Other'


def get_all_categories() -> list:
    """Return list of all available categories."""
    return list(CATEGORY_KEYWORDS.keys()) + ['Other']


def get_category_color(category: str) -> str:
    """Return a consistent color hex for each category."""
    colors = {
        'Food': '#FF6384',
        'Transport': '#36A2EB',
        'Shopping': '#FFCE56',
        'Entertainment': '#4BC0C0',
        'Bills': '#9966FF',
        'Health': '#FF9F40',
        'Education': '#C9CBCF',
        'Other': '#7EC8A4',
    }
    return colors.get(category, '#AAAAAA')
