from models import User, Beneficiary
from flask import request, jsonify,make_response

from app import app
from db import db


## BENEFICIARY ROUTES ###
# Route to add a beneficiary
@app.route('/beneficiary', methods=['POST'])
def add_beneficiary():
    data = request.get_json()
    beneficiary_email = data.get('beneficiary_email')
    user_id=data.get('user_id')

    # Check if beneficiary email exists in the system
    beneficiary = User.query.filter_by(email=beneficiary_email).first()
    if not beneficiary:
        return jsonify({'message': 'Beneficiary email not found'}), 404
    
     # Create a new beneficiary record
    new_beneficiary = Beneficiary(
        user_id=user_id,
        beneficiary_email=beneficiary_email
    )
   
    db.session.add(new_beneficiary)
    db.session.commit()

    return jsonify({'message': 'Beneficiary added', 'beneficiary': new_beneficiary.to_dict()}), 201


# Route to get all beneficiaries of a user
@app.route('/beneficiaries/<int:id>', methods=['GET'])
def get_beneficiaries(id):
    user = User.query.get(id)
    if user:
        beneficiaries = Beneficiary.query.filter_by(user_id=id).all()
        return jsonify([beneficiary.to_dict() for beneficiary in beneficiaries]), 200
    return jsonify({"error": "User not found!"}), 404

# Route to delete a beneficiary
@app.route('/beneficiary/<int:id>', methods=['DELETE'])
def delete_beneficiary(id):
    
    beneficiary = Beneficiary.query.filter(Beneficiary.beneficiary_id == id).first()
    db.session.delete(beneficiary)
    db.session.commit()
    return make_response({'message': 'beneficiary successfully deleted'}, 200)
