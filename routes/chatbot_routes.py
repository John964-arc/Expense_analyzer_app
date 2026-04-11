from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.analysis_service import AnalysisService
from models.chatbot_model import ExpenseChatbot

chatbot_bp = Blueprint('chatbot', __name__)


@chatbot_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    message = data['message'].strip()
    if not message:
        return jsonify({'error': 'Empty message'}), 400

    if len(message) > 500:
        return jsonify({'error': 'Message too long'}), 400

    try:
        context = AnalysisService.get_chatbot_context(current_user.id)
        bot = ExpenseChatbot(context)
        response = bot.get_response(message)
        return jsonify({'response': response, 'status': 'ok'})
    except Exception as e:
        return jsonify({'response': 'Sorry, I encountered an error. Please try again.', 'status': 'error'}), 500


@chatbot_bp.route('/chat/suggestions', methods=['GET'])
@login_required
def suggestions():
    """Return suggested chat prompts."""
    prompts = [
        "Where do I spend the most?",
        "How much did I spend this month?",
        "Show my spending breakdown",
        "How can I reduce expenses?",
        "What's my predicted expense next month?",
        "What's my spending trend?",
        "Any overspending alerts?",
        "Show weekly spending",
    ]
    return jsonify({'suggestions': prompts})
