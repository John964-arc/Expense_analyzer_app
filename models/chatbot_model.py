import re
from datetime import datetime


class ExpenseChatbot:
    """
    Rule-based + data-driven chatbot that answers questions
    about a user's expense data.
    """

    def __init__(self, expense_data: dict):
        """
        expense_data: dict with keys:
            - monthly_total: float
            - category_totals: dict {category: amount}
            - weekly_totals: list of {label, total}
            - predicted_next: float
            - all_expenses: list of expense dicts
            - trend: str
            - mom_change: float
        """
        self.data = expense_data
        self.month_name = datetime.now().strftime('%B')

    def get_response(self, message: str) -> str:
        """Route user message to appropriate handler."""
        msg = message.lower().strip()
        msg = re.sub(r'[^\w\s]', '', msg)

        # Spending most / top category
        if any(kw in msg for kw in ['most', 'highest', 'top', 'biggest', 'largest', 'where']):
            return self._top_spending()

        # Monthly total
        if any(kw in msg for kw in ['month', 'total', 'spent', 'how much', 'this month', 'spend']):
            if 'next' in msg or 'predict' in msg or 'forecast' in msg:
                return self._predict_next()
            return self._monthly_summary()

        # Weekly breakdown
        if any(kw in msg for kw in ['week', 'weekly', 'this week']):
            return self._weekly_summary()

        # Category breakdown
        if any(kw in msg for kw in ['breakdown', 'categor', 'distribution', 'split']):
            return self._category_breakdown()

        # Savings / reduction tips
        if any(kw in msg for kw in ['save', 'saving', 'reduce', 'cut', 'tip', 'advice', 'suggest', 'how can']):
            return self._saving_tips()

        # Trend / comparison
        if any(kw in msg for kw in ['trend', 'compare', 'last month', 'previous', 'increase', 'decreas']):
            return self._trend_info()

        # Prediction
        if any(kw in msg for kw in ['next month', 'predict', 'forecast', 'future']):
            return self._predict_next()

        # Overspending
        if any(kw in msg for kw in ['overspend', 'over budget', 'too much', 'alert']):
            return self._overspending_check()

        # Greeting
        if any(kw in msg for kw in ['hi', 'hello', 'hey', 'help', 'what can you']):
            return self._greeting()

        return self._default_response()

    def _greeting(self) -> str:
        total = self.data.get('monthly_total', 0)
        return (
            f"👋 Hi! I'm your AI Expense Assistant.\n\n"
            f"You've spent **₹{total:,.2f}** so far in {self.month_name}.\n\n"
            f"You can ask me:\n"
            f"• Where do I spend the most?\n"
            f"• How much did I spend this month?\n"
            f"• What's my spending breakdown?\n"
            f"• How can I reduce expenses?\n"
            f"• What's my predicted expense next month?"
        )

    def _monthly_summary(self) -> str:
        total = self.data.get('monthly_total', 0)
        mom = self.data.get('mom_change', 0)
        trend_emoji = '📈' if mom > 0 else ('📉' if mom < 0 else '➡️')
        change_text = f"{abs(mom):.1f}% {'more' if mom > 0 else 'less'} than last month"
        return (
            f"💰 In **{self.month_name}**, you've spent **₹{total:,.2f}**.\n\n"
            f"{trend_emoji} That's {change_text}."
        )

    def _top_spending(self) -> str:
        cats = self.data.get('category_totals', {})
        if not cats:
            return "I don't have enough data to determine your top spending category yet."
        sorted_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_amt = sorted_cats[0]
        total = self.data.get('monthly_total', 1)
        pct = (top_amt / total * 100) if total > 0 else 0
        lines = [f"🏆 Your top spending category is **{top_cat}** at **₹{top_amt:,.2f}** ({pct:.1f}% of total).\n"]
        lines.append("📊 Full breakdown:")
        for cat, amt in sorted_cats[:5]:
            bar_pct = (amt / total * 100) if total > 0 else 0
            lines.append(f"  • {cat}: ₹{amt:,.2f} ({bar_pct:.1f}%)")
        return '\n'.join(lines)

    def _category_breakdown(self) -> str:
        cats = self.data.get('category_totals', {})
        total = self.data.get('monthly_total', 0)
        if not cats:
            return "No category data available yet."
        lines = [f"📊 Your spending breakdown for {self.month_name}:\n"]
        for cat, amt in sorted(cats.items(), key=lambda x: x[1], reverse=True):
            pct = (amt / total * 100) if total > 0 else 0
            lines.append(f"  • {cat}: ₹{amt:,.2f} ({pct:.1f}%)")
        return '\n'.join(lines)

    def _weekly_summary(self) -> str:
        weeks = self.data.get('weekly_totals', [])
        if not weeks:
            return "No weekly data available yet."
        lines = [f"📅 Weekly spending in {self.month_name}:\n"]
        for w in weeks:
            lines.append(f"  • {w['label']}: ₹{w['total']:,.2f}")
        if len(weeks) >= 2:
            last = weeks[-1]['total']
            prev = weeks[-2]['total']
            diff = last - prev
            emoji = '📈' if diff > 0 else '📉'
            lines.append(f"\n{emoji} Last week you spent ₹{abs(diff):,.2f} {'more' if diff > 0 else 'less'} than the week before.")
        return '\n'.join(lines)

    def _saving_tips(self) -> str:
        cats = self.data.get('category_totals', {})
        tips = []
        if cats.get('Food', 0) > 300:
            tips.append("🍽️ **Food**: Consider meal prepping at home to cut dining-out costs.")
        if cats.get('Entertainment', 0) > 100:
            tips.append("🎬 **Entertainment**: Review streaming subscriptions — cancel ones you rarely use.")
        if cats.get('Transport', 0) > 200:
            tips.append("🚗 **Transport**: Try carpooling or public transit to reduce ride costs.")
        if cats.get('Shopping', 0) > 250:
            tips.append("🛍️ **Shopping**: Use a 24-hour rule before impulse purchases.")
        tips.append("💡 **General**: Set a monthly budget for each category and track daily spending.")
        tips.append("💳 **Bills**: Bundle services or negotiate rates with providers annually.")
        return "Here are some tips to reduce your expenses:\n\n" + '\n'.join(tips)

    def _predict_next(self) -> str:
        pred = self.data.get('predicted_next', 0)
        current = self.data.get('monthly_total', 0)
        diff = pred - current
        emoji = '📈' if diff > 0 else '📉'
        direction = 'higher' if diff > 0 else 'lower'
        return (
            f"🔮 Based on your spending history, next month's predicted expense is **₹{pred:,.2f}**.\n\n"
            f"{emoji} That's ₹{abs(diff):,.2f} {direction} than your current month's spending of ₹{current:,.2f}."
        )

    def _trend_info(self) -> str:
        trend = self.data.get('trend', 'stable')
        mom = self.data.get('mom_change', 0)
        emojis = {'increasing': '📈', 'decreasing': '📉', 'stable': '➡️'}
        emoji = emojis.get(trend, '➡️')
        return (
            f"{emoji} Your spending trend is **{trend}**.\n\n"
            f"Month-over-month change: **{mom:+.1f}%**\n\n"
            f"{'⚠️ Consider reviewing your expenses to find areas to cut back.' if trend == 'increasing' else '✅ Great job keeping your spending in check!' if trend == 'decreasing' else '📊 Your spending is fairly consistent.'}"
        )

    def _overspending_check(self) -> str:
        cats = self.data.get('category_totals', {})
        alerts = []
        thresholds = {'Food': 400, 'Shopping': 300, 'Entertainment': 150, 'Transport': 250}
        for cat, threshold in thresholds.items():
            if cats.get(cat, 0) > threshold:
                alerts.append(f"⚠️ **{cat}**: ₹{cats[cat]:,.2f} (threshold: ₹{threshold})")
        if not alerts:
            return "✅ No overspending alerts! Your spending looks well-balanced this month."
        return "🚨 Overspending alerts for this month:\n\n" + '\n'.join(alerts)

    def _default_response(self) -> str:
        return (
            "🤔 I'm not sure I understood that. Here's what I can help with:\n\n"
            "• **Monthly total**: 'How much did I spend this month?'\n"
            "• **Top category**: 'Where do I spend the most?'\n"
            "• **Breakdown**: 'Show my spending breakdown'\n"
            "• **Tips**: 'How can I reduce expenses?'\n"
            "• **Prediction**: 'Predict next month's expenses'\n"
            "• **Trends**: 'What's my spending trend?'"
        )
