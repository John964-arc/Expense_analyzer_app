import random
import string
from datetime import datetime
from sqlalchemy import func
from models.expense_model import db, FamilyGroup, FamilyMember, Expense, User
from utils.category_detector import get_category_color

class FamilyService:
    @staticmethod
    def create_group(user_id, name):
        """Create a new family group and assign the user as ADMIN."""
        invite_code = FamilyService._generate_invite_code()
        
        group = FamilyGroup(
            name=name,
            invite_code=invite_code,
            created_by=user_id
        )
        db.session.add(group)
        db.session.flush() # Get group.id

        member = FamilyMember(
            user_id=user_id,
            group_id=group.id,
            role='ADMIN'
        )
        db.session.add(member)
        db.session.commit()
        return group

    @staticmethod
    def join_group(user_id, invite_code):
        """Join an existing family group using an invite code."""
        group = FamilyGroup.query.filter_by(invite_code=invite_code.upper()).first()
        if not group:
            return None, "Invalid invite code."
        
        # Check if already a member
        existing = FamilyMember.query.filter_by(user_id=user_id, group_id=group.id).first()
        if existing:
            return group, "You are already a member of this group."

        member = FamilyMember(
            user_id=user_id,
            group_id=group.id,
            role='MEMBER'
        )
        db.session.add(member)
        db.session.commit()
        return group, None

    @staticmethod
    def get_user_group(user_id):
        """Get the group the user belongs to (if any)."""
        member = FamilyMember.query.filter_by(user_id=user_id).first()
        return member.group if member else None

    @staticmethod
    def get_family_dashboard_data(group_id):
        """Aggregate shared expenses for the whole family."""
        # Only shared expenses (is_private=False)
        shared_expenses = Expense.query.filter_by(family_id=group_id, is_private=False).all()
        
        total_spent = sum(e.amount for e in shared_expenses)
        
        # Category breakdown
        cat_totals = {}
        for e in shared_expenses:
            cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount
        
        # Sort categories
        sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
        
        # Member-wise spending
        member_totals = {}
        for e in shared_expenses:
            member_totals[e.user_id] = member_totals.get(e.user_id, 0) + e.amount
        
        # Resolve usernames and find Top Spender
        members_data = []
        top_spender = None
        max_spend = -1
        
        group_members = FamilyMember.query.filter_by(group_id=group_id).all()
        for m in group_members:
            user = User.query.get(m.user_id)
            spend = round(member_totals.get(m.user_id, 0), 2)
            members_data.append({
                'username': user.username,
                'total_spend': spend,
                'role': m.role
            })
            if spend > max_spend:
                max_spend = spend
                top_spender = user.username

        # Chart data
        chart_data = {
            'pie': {
                'labels': [c[0] for c in sorted_cats],
                'values': [round(c[1], 2) for c in sorted_cats],
                'colors': [get_category_color(c[0]) for c in sorted_cats]
            },
            'members': {
                'labels': [m['username'] for m in members_data],
                'values': [m['total_spend'] for m in members_data]
            }
        }

        return {
            'total_spent': round(total_spent, 2),
            'top_spender': top_spender if total_spent > 0 else "None yet",
            'members': members_data,
            'chart_data': chart_data,
            'recent_shared': [e.to_dict() for e in shared_expenses[-10:]][::-1]
        }

    @staticmethod
    def _generate_invite_code():
        """Generate a random 6-char alphanumeric code."""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not FamilyGroup.query.filter_by(invite_code=code).first():
                return code
