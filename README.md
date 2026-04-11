# AI Expense Analyzer with Chatbot

A full-stack expense tracking web app built with Flask, SQLite, Scikit-learn, and Chart.js.

---

## Features

- **User auth** — register, login, logout with Flask-Login
- **Expense tracking** — add, view, delete expenses with SQLite storage
- **AI Categorization** — keyword-based NLP auto-detects Food, Transport, Shopping, Entertainment, Bills, Health, Education
- **ML Prediction** — multi-model Linear Regression (with Ridge + Polynomial comparison via LOOCV) predicts next month's spending with a 90% confidence interval
- **Dashboard** — monthly totals, category pie chart, weekly bar chart, 6-month history, recent transactions
- **AI Chatbot** — left-sidebar assistant answers natural language questions about your spending
- **Insights** — overspending alerts, trend detection, month-over-month change
- **Receipt Scanner** — upload receipt images; extracts vendor + amount via pytesseract OCR (optional)

---

## Folder Structure

```
ai-expense-analyzer/
├── app.py                  # Flask app factory
├── config.py               # Environment configs
├── requirements.txt
├── README.md
├── database/
│   └── expenses.db         # SQLite (auto-created on first run)
├── models/
│   ├── expense_model.py    # SQLAlchemy User + Expense ORM
│   ├── prediction_model.py # Multi-model regression (Linear/Ridge/Poly2)
│   └── chatbot_model.py    # Rule-based expense chatbot
├── services/
│   ├── expense_service.py  # CRUD operations
│   ├── analysis_service.py # Dashboard aggregation + ML pipeline
│   └── receipt_scanner.py  # OCR receipt parsing
├── routes/
│   ├── auth_routes.py      # /auth/login, /auth/register, /auth/logout
│   ├── expense_routes.py   # /, /dashboard, /add, /expenses/<id>
│   └── chatbot_routes.py   # /chat, /chat/suggestions
├── utils/
│   ├── db_helper.py        # DB init + demo data seeder
│   ├── category_detector.py# Keyword-based category classifier
│   └── helpers.py          # Date, format, file utilities
├── templates/              # Jinja2 HTML templates
├── static/
│   ├── css/style.css       # Dark fintech design system
│   ├── js/dashboard.js     # Chart.js charts + delete logic
│   └── js/chatbot.js       # Chatbot UI + fetch logic
└── data/
    └── sample_expenses.csv # 36 sample records for reference
```

---

## Quick Start

```bash
# 1. Clone / unzip the project
cd ai-expense-analyzer

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Open **http://localhost:5000** in your browser.

**Demo account** (auto-created with 6 months of sample data):
- Email: `demo@example.com`
- Password: `demo123`

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/` | Redirect to dashboard |
| GET | `/dashboard` | Main analytics dashboard |
| GET | `/add` | Add expense form |
| POST | `/add` | Submit new expense |
| DELETE | `/expenses/<id>` | Delete an expense |
| GET | `/api/dashboard-data` | Dashboard JSON (AJAX) |
| POST | `/chat` | Chatbot message |
| GET | `/chat/suggestions` | Suggested chat prompts |
| GET/POST | `/auth/login` | Login |
| GET/POST | `/auth/register` | Register |
| GET | `/auth/logout` | Logout |

---

## Optional: Receipt OCR

To enable full receipt scanning:

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt install tesseract-ocr

# Then uncomment in requirements.txt:
pip install pytesseract==0.3.10
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, Flask 3.0 |
| Database | SQLite via Flask-SQLAlchemy |
| Auth | Flask-Login + Werkzeug password hashing |
| ML | Scikit-learn (LinearRegression, Ridge, PolynomialFeatures, LOOCV) |
| NLP | Keyword-based category classifier (category_detector.py) |
| Charts | Chart.js 4.4 (Bar, Doughnut) |
| Fonts | Syne (headings) + IBM Plex Sans (body) via Google Fonts |
| CSS | Custom design system with CSS variables (no framework) |
