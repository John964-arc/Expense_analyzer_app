import os

files = [
    'utils/helpers.py',
    'templates/dashboard.html',
    'templates/add_expense.html',
    'static/js/dashboard.js',
    'services/analysis_service.py',
    'routes/expense_routes.py',
    'models/expense_model.py',
    'models/chatbot_model.py'
]

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('$', '₹')
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
