# import os
# from datetime import datetime
# import requests
# import base64
# from flask_restful import Resource, reqpaerse
# from flask import jsonify

# AUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
# STKPUSH_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
# SHORT_CODE = 174379


# class Mpesa(Resource):

#     parser= reqpaerse.RequstParser()
#     parser.add_argument('phone_number', required=True, help="phone_number is required")
#     parser.add_argument('amount', required=True, help="Amount is required")


#     def post(self):
#         token= Mpesa.get_access_token()
#         access_token = token['access_token']

#         data=Mpesa.parser.parse_args()
#         timestamp=datetime.now().strftime('%Y%m%d%H%M%S')
#         passkey=str(SHORT_CODE) + ":" + os.environ.get("SAF_PASS_KEY") + ":" + timestamp
#         password_bytes=passkey.encode()

#         password=base64.b64encode(bytes(password_bytes)).decode("utf-8")
#         password=password[:-1]


#         body={    
#                 "BusinessShortCode": SHORT_CODE,    
#                  "Password": password,    
#                  "Timestamp":timestamp,    
#                 "TransactionType": "CustomerPayBillOnline",    
#                 "Amount": "1",    
#                 "PartyA": data['phone_number'],    
#                  "PartyB":SHORT_CODE,    
#                 "PhoneNumber": data['phone_number'],    
#                 "CallBackURL": "https://mydomain.com/pat",    
#                 "AccountReference":"VisaPay",    
#                   "TransactionDesc":f" Pay [data['amount']]"
#             }
#         headers={"Authorization":f"Bearer %s" % access_token, "Content-Type":"application/json" }

#         try:
#             response= requests.request("POST", STKPUSH_URL, json=body, headers=headers)
#             return response.json
#         except requests.exceptions.HTTPError as error :
#             print(error)
#         except Exception as err:
#             print(f"other error occurrred: {err}")


#     def get_access_token(self);
#         secret=os.environ.get("SAF_CONSUMER_KEY ") + ":" + os.environ.get("SAF_CONSUMER_SECRET")
#         encoded = base64.b64decode(secret.encode("utf-8")).decode("utf-8")
#         headers={"Authorization":f"Basic {encoded}" }

#         try:
#             response = requests.get(AUTH_URL, headers=headers)
#             response.raise_for_status()
#             return response.json()
#         except requests.exceptions.HTTPError as error:
#             print(error)

# class MpesaCallback(Resource):

#     defpost(self):
