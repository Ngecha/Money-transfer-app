from flask import request, jsonify, session
from functools import wraps
from app import app
from flask_cors import CORS

from models import User, TransactionSummary, Analytics

CORS(app)

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin:
            return jsonify({'message': 'Admin access only'}), 403
        return f(*args, **kwargs)
    return decorated_function


## ANALYTICS ROUTES ###

# Admin Route: Transaction Summary
@app.route('/admin/transaction-summary', methods=['GET'])
@admin_required
def get_transaction_summary():
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        return jsonify({'message': 'Unauthorized access'}), 403

    summary = TransactionSummary.query.all() 
    return jsonify([summary_item.to_dict() for summary_item in summary]), 200

# Admin Route: User Analytics 
@app.route('/admin/user-analytics', methods=['GET'])
@admin_required
def get_user_analytics():
    user_id = request.args.get('user_id')
    analytics = Analytics.query.filter_by(user_id=user_id).all()
    return jsonify([analytic.to_dict() for analytic in analytics]), 200