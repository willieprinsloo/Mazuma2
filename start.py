from flask import Flask, jsonify, request, Response
from flask_httpauth import HTTPTokenAuth
import traceback
import logging
import uuid
import json
from functools import wraps
from datetime import datetime, timedelta
from redis import Redis


import sync_orders
import sync_price, sync_inventory, sync_update_listing

app = Flask(__name__)
auth = HTTPTokenAuth(scheme='Bearer')
redis_client = Redis(host='localhost', port=6379, db=0)

# Secure token and client storage (using a dictionary for example purposes, replace with a database in production)
TOKENS = {}
CLIENTS = {
    "META100": "META472732"  # Example client_id and client_secret, replace with secure storage
}
SCOPES = ["read", "write"]  # Example scopes, replace with actual scopes required

def handle_exception(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({"Error": str(e), "Stack Trace": traceback.format_exc(), "AuthorizationToken": None}), 500

    return decorated

@app.before_request
def log_request_info():
    logging.info(f"Request: {request.method} {request.url}")
    logging.info(f"Headers: {dict(request.headers)}")
    if request.method in ['POST', 'PUT', 'PATCH']:
        logging.info(f"Body: {request.get_data()}")

@app.after_request
def log_response_info(response):
    logging.info(f"Response status: {response.status}")
    logging.info(f"Response headers: {dict(response.headers)}")
    if response.is_json:
        logging.info(f"Response body: {response.get_json()}")
    else:
        logging.info(f"Response body: {response.data}")
    return response

@app.teardown_request
def log_teardown(exception=None):
    if exception:
        logging.error(f"Teardown exception: {str(exception)}", exc_info=True)
    else:
        logging.info("Request handled successfully without exceptions.")

def generate_token():
    return str(uuid.uuid4())

def add_token(token, client_id, scope, expires_in=18600):
    expiration_time = datetime.utcnow() + timedelta(seconds=expires_in)
    token_data = {'client_id': client_id, 'scope': scope, 'expires_at': expiration_time.isoformat()}
    redis_client.set(token, json.dumps(token_data), ex=expires_in)
    logging.info(f"Token added: {token} for client {client_id} with scope {scope}, expires at {expiration_time}")

@auth.verify_token
def verify_token(token):

    token_data_json = redis_client.get(token)
    if token_data_json:
        token_data = json.loads(token_data_json)
        if datetime.fromisoformat(token_data['expires_at']) > datetime.utcnow():
            logging.info(f"Token found: {token}, expires at {token_data['expires_at']}")
            return token_data['client_id']
    logging.info(f"Token invalid or expired: {token}")
    return None

@app.before_request
def check_token():
    if request.method != 'OPTIONS':  # Skip for CORS preflight requests
        auth_header = request.headers.get('Authorization')
        if auth_header:
            token = auth_header.split()[-1]
            if not verify_token(token):
                return jsonify({"Error": "Invalid or expired token"}), 401
@app.route('/api/oauth/authorize', methods=['POST'])
def authorize():
    grant_type = request.form.get('grant_type')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    scope = request.form.get('scope')
    logging.info("oauth called")
    # Validate grant_type
    if grant_type != 'client_credentials':
        logging.info("unsupported_grant_type")
        return jsonify({"error": "unsupported_grant_type"}), 400

    # Validate client_id and client_secret
    if CLIENTS.get(client_id) != client_secret:
        logging.info("invalid_client")
        return jsonify({"error": "invalid_client"}), 401

    # Validate scope
    requested_scopes = scope.split()
    if not all(s in SCOPES for s in requested_scopes):
        logging.info("invalid_scope")
        return jsonify({"error": "invalid_scope"}), 400

    # Generate and store token
    access_token = generate_token()
    add_token(access_token, client_id, scope)

    return jsonify({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 18600,
        "scope": scope
    }), 200


def add_token_to_response(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        response = f(*args, **kwargs)
        if isinstance(response, Response):
            data = response.get_json()
            status_code = response.status_code
        elif isinstance(response, tuple):
            data, status_code = response
        else:
            data, status_code = response, 200

        auth_header = request.headers.get('Authorization')
        if auth_header:
            token = auth_header.split()[-1]
            if isinstance(data, dict):
                data['AuthorizationToken'] = token
                data['Error'] = None
            else:
                data = {"Error": None, "AuthorizationToken": token}

        return jsonify(data), status_code

    return decorated



@app.route('/api/Config/AddNewUser', methods=['GET', 'POST'])
@auth.login_required
@add_token_to_response
def add_new_user():
    return {"Error": None}, 200


@app.route('/api/Config/UserConfig', methods=['GET', 'POST'])
@auth.login_required
@add_token_to_response
def user_config():
    return {
        "IsConfigActive": False,
        "ConfigStatus": "UserConfig",
        "ConfigStage": {
            "WizardStepDescription": "Description of the stage.",
            "WizardStepTitle": "Title of the wizard Stage",
            "ConfigItems": [
                {
                    "ConfigItemId": "ITEM1",
                    "Name": "Config Item 1",
                    "Description": "Description Item 1",
                    "GroupName": "Group item",
                    "SortOrder": 1,
                    "SelectedValue": "",
                    "RegExValidation": None,
                    "RegExError": None,
                    "MustBeSpecified": True,
                    "ReadOnly": False,
                    "ListValues": [
                        {
                            "Display": "List Value 1",
                            "Value": "1"
                        }
                    ],
                    "ValueType": 5
                }
            ]
        },
        "IsError": False,
        "ErrorMessage": None
    }, 200


@app.route('/api/Order/Orders', methods=['GET', 'POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def orders():
    data = request.get_json()
    date_str = data.get('UTCTimeFrom')
    linnworks_data = sync_orders.get_orders_after_date(date_str)
    return {"Error": None, "OrdersData": linnworks_data}, 200


@app.route('/api/Config/SaveUserConfig', methods=['POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def save_user_config():
    data = request.get_json()
    return {
        "Error": None,
        "StepName": "UserConfig",
        "WizardStepDescription": "Definition of tax settings and items to return",
        "WizardStepTitle": "UserConfig",
        "ConfigItems": data.get('ConfigItems')
    }, 200


@app.route('/api/Config/ConfigDeleted', methods=['GET', 'POST'])
@auth.login_required
@add_token_to_response
def config_deleted():
    return {}, 200


@app.route('/api/Config/ConfigTest', methods=['GET', 'POST'])
@auth.login_required
@add_token_to_response
def config_test():
    # This endpoint is used by Linnworks to test the connection
    return jsonify({"Status": "Success", "Message": "Configuration is valid"}), 200


@app.route('/api/Product/Products', methods=['POST', 'GET'])
@auth.login_required
@add_token_to_response
def products():
    return {"Error": None}, 200


@app.route('/api/Config/ShippingTags', methods=['POST', 'GET'])
@auth.login_required
@add_token_to_response
def payment_shipment_tags():
    return {"Error": None}, 200


@app.route('/api/Config/PaymentTags', methods=['POST', 'GET'])
@auth.login_required
@add_token_to_response
def payment_payment_tags():
    return {"Error": None}, 200


@app.route('/api/Product/InventoryUpdate', methods=['POST', 'GET'])
@auth.login_required
@add_token_to_response
@handle_exception
def inventory_update():
    data = request.get_json()
    sync_inventory.sync_inventory(data)
    return {"Error": None}, 200


@app.route('/api/Product/PriceUpdate', methods=['POST', 'GET'])
@auth.login_required
@add_token_to_response
@handle_exception
def price_update():
    data = request.get_json()
    sync_price.sync_price(data)
    return {
        "Error": None,
        "Products": [
            {"SKU": product.get('SKU'), "Error": None}
            for product in data.get('Products', [])
        ]
    }, 200


@app.route('/api/Listing/ListingUpdate', methods=['POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def listing_update():
    data = request.get_json()
    sync_catalogue.sync_catalogue(data)
    return {
        "Error": None,
        "Products": [
            {"SKU": product.get('SKU'), "Error": None}
            for product in data.get('Products', [])
        ]
    }, 200


@app.route('/api/Listing/GetConfiguratorSettings', methods=['POST'])
@auth.login_required
@add_token_to_response
def get_configurator_settings():
    try:
        response = {
            "Settings": [
                {
                    "GroupName": "VARIATION",
                    "ConfigItemId": "VariationTheme",
                    "Subtitle": "General",
                    "SubTitleSortOrder": 1,
                    "ItemSortOrder": 1,
                    "Description": "Theme used for variation. Cannot be changed once config created",
                    "FriendlyName": "Variation Theme",
                    "MustBeSpecified": False,
                    "ExpectedType": "STRING",
                    "ValueOptions": ["Color", "Size", "Color-Size"],
                    "InitialValues": [],
                    "IsMultiOption": False,
                    "ValueFromOptionsList": True,
                    "RegExValidation": "",
                    "RegExError": "",
                    "IsWizardOnly": True
                }
            ],
            "MaxDescriptionLength": 10000,
            "ImageSettings": {
                "Type": 2,
                "MaxImages": 100,
                "MaxVariantImages": 4,
                "ImageTags": [
                    {"Name": "Main_image", "ImageTagType": 2},
                    {"Name": "Large_image", "ImageTagType": 2},
                    {"Name": "Thumbnail_image", "ImageTagType": 1},
                    {"Name": "Basket_image", "ImageTagType": 1}
                ]
            },
            "MaxCategoryCount": 1000,
            "MaxCustomAttributeLength": 1000,
            "IsCustomHtmlSupported": True,
            "IsCustomAttributesAllowed": True,
            "HasMainVariationPrice": True,
            "IsTitleInVariation": False,
            "HasVariationAttributeDisplayName": True,
            "IsPriceInVariation": True,
            "IsShippingListingSpecific": False,
            "IsPaymentListingSpecific": False,
            "Error": None
        }
        return jsonify(response), 200
    except Exception as e:
        logging.error(f"Error in get_configurator_settings: {str(e)}", exc_info=True)
        return jsonify({"Error": str(e), "Stack Trace": traceback.format_exc(), "AuthorizationToken": None}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
