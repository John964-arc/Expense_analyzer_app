from datetime import datetime
from services.expense_service import ExpenseService
from services.budget_service import BudgetService
from services.savings_service import SavingsService
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

        # ── ML Prediction ──────────────────────────────────────────────────
        predictor = ExpensePredictionModel()
        predictor.train(monthly_totals_list)
        predicted_next  = predictor.predict_next_month()
        trend           = predictor.get_trend()
        mom_change      = predictor.get_month_over_month_change()
        ci_low, ci_high = predictor.predict_confidence_interval(0.90)
        model_report    = predictor.get_model_report()

        # ── Budget warnings ───────────────────────────────────────────────
        budget_warnings = BudgetService.get_dashboard_warnings(user_id)

        # ── Savings summary ───────────────────────────────────────────────
        savings_summary = SavingsService.get_goals_summary(user_id)

        # ── Health Score ──────────────────────────────────────────────────
        health = AnalysisService.get_health_score(
            user_id        = user_id,
            monthly_total  = monthly_total,
            budget_warnings= budget_warnings,
            savings_summary= savings_summary,
            trend          = trend,
            mom_change     = mom_change,
        )

        # ── Insights ──────────────────────────────────────────────────────
        insights = AnalysisService._generate_insights(
            monthly_total, category_totals,
            trend, mom_change, monthly_totals_list, budget_warnings
        )

        # ── Chart data ────────────────────────────────────────────────────
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
            'confidence_low':  ci_low,
            'confidence_high': ci_high,
            'model_report':    model_report,
            'trend':           trend,
            'mom_change':      mom_change,
            'insights':        insights,
            'chart_data':      chart_data,
            'recent_expenses': [e.to_dict() for e in recent],
            'budget_warnings': budget_warnings,
            'savings_summary': savings_summary,
            'health_score':    health,
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
            'health_score':    dashboard['health_score'],
        }

    @staticmethod
    def get_health_score(user_id: int, monthly_total: float = None,
                         budget_warnings: list = None,
                         savings_summary: dict = None,
                         trend: str = 'stable',
                         mom_change: float = 0.0) -> dict:
        """
        Compute a 0-100 financial health score.
        Factors (each up to 25 pts):
          1. Budget adherence  — have budgets set + not overspending
          2. Savings progress  — have active goals with progress
          3. Spending trend    — decreasing is good, increasing is bad
          4. Category balance  — no single category > 50 % of total
        """
        score    = 0
        factors  = []

        # ── 1. Budget adherence (25 pts) ──────────────────────────────────
        if budget_warnings is None:
            budget_warnings = BudgetService.get_dashboard_warnings(user_id)

        danger_count = sum(1 for w in budget_warnings if w['alert'] in ('danger', 'critical'))
        warn_count   = sum(1 for w in budget_warnings if w['alert'] == 'warning')

        if not budget_warnings:      # no budgets — partial credit for not overspending
            b_score = 15
            b_msg   = 'Set budgets to improve your score'
        else:
            b_score = max(0, 25 - (danger_count * 10) - (warn_count * 4))
            b_msg   = 'Budget adherence'
        score += b_score
        factors.append({'label': 'Budget Adherence', 'score': b_score, 'max': 25, 'msg': b_msg})

        # ── 2. Savings progress (25 pts) ─────────────────────────────────
        if savings_summary is None:
            savings_summary = SavingsService.get_goals_summary(user_id)

        overall_pct = savings_summary.get('overall_pct', 0)
        if savings_summary.get('active_goals', 0) == 0:
            s_score = 10
            s_msg   = 'Create savings goals to boost your score'
        else:
            s_score = int(min(overall_pct / 100 * 25, 25))
            s_msg   = f'{overall_pct:.0f}% of savings goals reached'
        score += s_score
        factors.append({'label': 'Savings Progress', 'score': s_score, 'max': 25, 'msg': s_msg})

        # ── 3. Spending trend (25 pts) ────────────────────────────────────
        if trend == 'decreasing':
            t_score = 25
            t_msg   = 'Spending is trending down 📉'
        elif trend == 'stable':
            t_score = 18
            t_msg   = 'Spending is stable ➡️'
        else:
            # Increasing — deduct based on magnitude
            t_score = max(0, 25 - int(abs(mom_change) / 5))
            t_msg   = f'Spending up {mom_change:+.1f}% MoM 📈'
        score += t_score
        factors.append({'label': 'Spending Trend', 'score': t_score, 'max': 25, 'msg': t_msg})

        # ── 4. Category balance (25 pts) ─────────────────────────────────
        now = datetime.now()
        cat = ExpenseService.get_category_totals(user_id, now.year, now.month)
        total = monthly_total or sum(cat.values()) or 1
        top_pct = (max(cat.values()) / total * 100) if cat else 0

        if top_pct > 70:
            c_score, c_msg = 5,  'Spending heavily concentrated in one category'
        elif top_pct > 50:
            c_score, c_msg = 15, 'Spending somewhat concentrated'
        else:
            c_score, c_msg = 25, 'Spending well distributed across categories'
        score += c_score
        factors.append({'label': 'Category Balance', 'score': c_score, 'max': 25, 'msg': c_msg})

        # ── Grade ─────────────────────────────────────────────────────────
        if score >= 85:
            grade, grade_color = 'A', '#22C55E'
        elif score >= 70:
            grade, grade_color = 'B', '#84CC16'
        elif score >= 55:
            grade, grade_color = 'C', '#EAB308'
        elif score >= 40:
            grade, grade_color = 'D', '#F97316'
        else:
            grade, grade_color = 'F', '#EF4444'

        return {
            'score':       score,
            'grade':       grade,
            'grade_color': grade_color,
            'factors':     factors,
        }

    @staticmethod
    def _generate_insights(monthly_total: float, category_totals: dict,
                           trend: str, mom_change: float,
                           monthly_totals_list: list,
                           budget_warnings: list = None) -> list:
        """Generate human-readable insight messages."""
        insights = []
        budget_warnings = budget_warnings or []

        # Trend insights
        if trend == 'increasing':
            insights.append({'type': 'warning', 'icon': '📈',
                'message': f'Spending is up {mom_change:+.1f}% vs last month. Review your expenses.'})
        elif trend == 'decreasing':
            insights.append({'type': 'success', 'icon': '📉',
                'message': f'Great! Spending dropped {abs(mom_change):.1f}% vs last month.'})

        # Top category insight
        if category_totals:
            top_cat = max(category_totals, key=category_totals.get)
            top_pct = (category_totals[top_cat] / monthly_total * 100) if monthly_total > 0 else 0
            if top_pct > 40:
                insights.append({'type': 'info', 'icon': '💡',
                    'message': f'{top_cat} is {top_pct:.0f}% of your spending this month.'})

        # Smart alert: unusual month vs 3-month average
        if len(monthly_totals_list) >= 3:
            avg_3 = sum(monthly_totals_list[-4:-1]) / 3 if len(monthly_totals_list) > 3 else sum(monthly_totals_list[:-1]) / max(1, len(monthly_totals_list) - 1)
            if avg_3 > 0 and monthly_total > avg_3 * 1.25:
                excess_pct = (monthly_total / avg_3 - 1) * 100
                insights.append({'type': 'danger', 'icon': '🔔',
                    'message': f'This month\'s spending is {excess_pct:.0f}% above your 3-month average!'})

        # Budget overspend warnings
        for w in budget_warnings:
            if w['alert'] in ('danger', 'critical'):
                if w['category']:
                    insights.append({'type': 'danger', 'icon': '🚨',
                        'message': f'{w["label"]} budget exceeded! Spent ₹{w["spent"]:,.0f} of ₹{w["budget"]:,.0f}.'})
                else:
                    insights.append({'type': 'danger', 'icon': '🚨',
                        'message': f'Monthly budget exceeded! Spent ₹{w["spent"]:,.0f} of ₹{w["budget"]:,.0f}.'})

        # Hardcoded category thresholds (fallback)
        thresholds = {'Food': 400, 'Shopping': 300, 'Entertainment': 150, 'Transport': 250}
        for cat, threshold in thresholds.items():
            if category_totals.get(cat, 0) > threshold:
                already_warned = any(
                    cat.lower() in i['message'].lower() for i in insights
                )
                if not already_warned:
                    insights.append({'type': 'warning', 'icon': '⚠️',
                        'message': f'{cat} spending (₹{category_totals[cat]:,.0f}) is high this month.'})

        if not insights:
            insights.append({'type': 'success', 'icon': '✅',
                'message': 'Your spending looks well-balanced this month. Keep it up!'})

        return insights
