from datetime import datetime
from services.expense_service import ExpenseService
from models.prediction_model  import ExpensePredictionModel
from utils.category_detector  import get_category_color
from utils.helpers             import months_list, month_label


class AnalysisService:

    @staticmethod
    def get_dashboard_data(user_id: int) -> dict:
        """Aggregate all data needed for the dashboard."""
        now   = datetime.now()
        year, month = now.year, now.month

        monthly_total   = round(
            sum(e.amount for e in ExpenseService.get_expenses_by_month(user_id, year, month)), 2
        )
        category_totals = ExpenseService.get_category_totals(user_id, year, month)
        weekly_data     = ExpenseService.get_weekly_totals(user_id, year, month)

        # 6-month history for charts + ML training
        history_months      = months_list(6)
        monthly_history     = []
        monthly_totals_list = []
        for y, m in history_months:
            exps  = ExpenseService.get_expenses_by_month(user_id, y, m)
            total = round(sum(e.amount for e in exps), 2)
            monthly_history.append({'label': month_label(y, m), 'total': total})
            monthly_totals_list.append(total)

        # ── ML Prediction (multi-model with LOOCV selection) ─────────────
        predictor = ExpensePredictionModel()
        predictor.train(monthly_totals_list)
        predicted_next  = predictor.predict_next_month()
        trend           = predictor.get_trend()
        mom_change      = predictor.get_month_over_month_change()
        ci_low, ci_high = predictor.predict_confidence_interval(0.90)
        model_report    = predictor.get_model_report()

        # ── Insights ─────────────────────────────────────────────────────
        insights = AnalysisService._generate_insights(
            monthly_total, category_totals, trend, mom_change
        )

        # ── Chart data ───────────────────────────────────────────────────
        chart_data = {
            'pie': {
                'labels': list(category_totals.keys()),
                'values': list(category_totals.values()),
                'colors': [get_category_color(c) for c in category_totals.keys()],
            },
            'weekly': {
                'labels': [w['label'] for w in weekly_data],
                'values': [w['total'] for w in weekly_data],
            },
            'monthly': {
                'labels': [mh['label'] for mh in monthly_history],
                'values': [mh['total'] for mh in monthly_history],
            },
        }

        recent = ExpenseService.get_user_expenses(user_id, limit=10)

        return {
            'monthly_total':   monthly_total,
            'category_totals': category_totals,
            'weekly_totals':   weekly_data,
            'monthly_history': monthly_history,
            'predicted_next':  predicted_next,
            'confidence_low':  ci_low,           # NEW: 90% CI lower bound
            'confidence_high': ci_high,          # NEW: 90% CI upper bound
            'model_report':    model_report,     # NEW: which model won
            'trend':           trend,
            'mom_change':      mom_change,
            'insights':        insights,
            'chart_data':      chart_data,
            'recent_expenses': [e.to_dict() for e in recent],
        }

    @staticmethod
    def get_chatbot_context(user_id: int) -> dict:
        """Prepare lightweight context dict for the chatbot."""
        dashboard     = AnalysisService.get_dashboard_data(user_id)
        weekly_totals = [
            {'label': w['label'], 'total': w['total']}
            for w in dashboard['weekly_totals']
        ]
        return {
            'monthly_total':   dashboard['monthly_total'],
            'category_totals': dashboard['category_totals'],
            'weekly_totals':   weekly_totals,
            'predicted_next':  dashboard['predicted_next'],
            'trend':           dashboard['trend'],
            'mom_change':      dashboard['mom_change'],
            'all_expenses':    dashboard['recent_expenses'],
        }

    @staticmethod
    def _generate_insights(monthly_total: float, category_totals: dict,
                            trend: str, mom_change: float) -> list:
        """Generate human-readable insight messages."""
        insights = []

        if trend == 'increasing':
            insights.append({'type': 'warning', 'icon': '📈',
                'message': f'Spending is up {mom_change:+.1f}% vs last month. Review your expenses.'})
        elif trend == 'decreasing':
            insights.append({'type': 'success', 'icon': '📉',
                'message': f'Great! Spending dropped {abs(mom_change):.1f}% vs last month.'})

        if category_totals:
            top_cat = max(category_totals, key=category_totals.get)
            top_pct = (category_totals[top_cat] / monthly_total * 100) if monthly_total > 0 else 0
            if top_pct > 40:
                insights.append({'type': 'info', 'icon': '💡',
                    'message': f'{top_cat} is {top_pct:.0f}% of your budget this month.'})

        thresholds = {'Food': 400, 'Shopping': 300, 'Entertainment': 150, 'Transport': 250}
        for cat, threshold in thresholds.items():
            if category_totals.get(cat, 0) > threshold:
                insights.append({'type': 'danger', 'icon': '⚠️',
                    'message': f'Overspend alert: {cat} (₹{category_totals[cat]:,.2f}) > ₹{threshold} limit.'})

        if not insights:
            insights.append({'type': 'success', 'icon': '✅',
                'message': 'Your spending looks well-balanced this month. Keep it up!'})

        return insights
