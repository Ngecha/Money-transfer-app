from flask import Flask, request, jsonify
import requests
import base64
import datetime
import time
import os

app = Flask(__name__)

# Mpesa credentials
CONSUMER_KEY = os.environ.get("SAF_CONSUMER_KEY")
CONSUMER_SECRET =os.environ.get("SAF_CONSUMER_SECRET")
PASS_KEY = os.environ.get("SAF_PASS_KEY")
PAYBILL = os.environ.get("SHORTCODE")
CALLBACK_URL = "https://yourdomain.com/callback"  # Replace with your callback URL
BASE_URL = "https://sandbox.safaricom.co.ke"  # Change to production URL when live


# Helper function to get access token
def get_access_token():
    try:
        # Generate Base64 encoded credentials
        credentials = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        # Request access token
        url = f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        headers = {"Authorization": f"Basic {encoded_credentials}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return data["access_token"]
        else:
            return None
    except Exception as e:
        print(f"Error generating access token: {e}")
        return None


# Helper function to get timestamp
def mpesa_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d%H%M%S")


# Route for STK Push
@app.route("/payments/stk_push", methods=["POST"])
def stk_push():
    phone = request.json.get("phone")  # Phone number
    amount = request.json.get("amount", 1)  # Default amount is 1

    timestamp = mpesa_timestamp()
    password = base64.b64encode(f"{PAYBILL}{PASS_KEY}{timestamp}".encode()).decode()

    # Prepare the STK Push payload
    payload = {
        "BusinessShortCode": PAYBILL,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": PAYBILL,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "VisaPay",
        "TransactionDesc": "Payment of X",
    }

    # Get access token
    token = get_access_token()
    if not token:
        return jsonify({"error": "Failed to get access token"}), 500

    # Send STK Push request
    url = f"{BASE_URL}/mpesa/stkpush/v1/processrequest"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return jsonify(response.json()), 200
    else:
        return jsonify({"error": "Failed to initiate STK Push", "details": response.text}), response.status_code


# Route to query payment status
@app.route("/transactions/query", methods=["POST"])
def query_transaction():
    transaction_id = request.json.get("transaction_id")  # CheckoutRequestID from STK push response

    if not transaction_id:
        return jsonify({"error": "Transaction ID is required"}), 400

    timestamp = mpesa_timestamp()
    password = base64.b64encode(f"{PAYBILL}{PASS_KEY}{timestamp}".encode()).decode()

    # Prepare the query payload
    payload = {
        "BusinessShortCode": PAYBILL,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": transaction_id,
    }

    # Get access token
    token = get_access_token()
    if not token:
        return jsonify({"error": "Failed to get access token"}), 500

    # Send query request
    url = f"{BASE_URL}/mpesa/stkpushquery/v1/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()

        # Check transaction status
        result_desc = data.get("ResultDesc", "")
        if result_desc == "The service request is processed successfully.":
            status = "SUCCESS"
        elif result_desc == "Request cancelled by user":
            status = "CANCELLED"
        else:
            status = "PENDING"

        return jsonify({"status": status, "details": data}), 200
    else:
        return jsonify({"error": "Failed to query transaction", "details": response.text}), response.status_code


if __name__ == "__main__":
    app.run(debug=True)
