from flask import Flask, jsonify, request, Response, send_file, current_app
from flask_httpauth import HTTPTokenAuth
import traceback
import logging
import uuid
import json
from functools import wraps
from datetime import datetime, timedelta

from redis import Redis
import asyncio
import os
import threading
from flask import send_from_directory

import sync_orders
import sync_price
from sync_inventory import sync_inventory
import sync_update_listing
from sync_down_catalogue import get_products_by_page

app = Flask(__name__)
auth = HTTPTokenAuth(scheme='Bearer')
redis_client = Redis(host='localhost', port=6379, db=0)

logging.basicConfig(filename="logs.log", level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


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
            # logging.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            print(f"Error in {f.__name__}: {str(e)}")
            return jsonify({"Error": str(e), "Stack Trace": traceback.format_exc(), "AuthorizationToken": None}), 500

    return decorated


@app.teardown_request
def log_teardown(exception=None):
    if exception:
        logging.error(f"Teardown exception: {str(exception)}", exc_info=True)



def generate_token():
    return str(uuid.uuid4())


def add_token(token, client_id, scope, expires_in=18600):
    expiration_time = datetime.utcnow() + timedelta(seconds=expires_in)
    token_data = {'client_id': client_id, 'scope': scope, 'expires_at': expiration_time.isoformat()}
    redis_client.set(token, json.dumps(token_data), ex=expires_in)
    #logging.info(f"Token added: {token} for client {client_id} with scope {scope}, expires at {expiration_time}")


@auth.verify_token
def verify_token(token):
    token_data_json = redis_client.get(token)
    if token_data_json:
        token_data = json.loads(token_data_json)
        if datetime.fromisoformat(token_data['expires_at']) > datetime.utcnow():
            #logging.info(f"Token found: {token}, expires at {token_data['expires_at']}")
            return token_data['client_id']
    #logging.info(f"Token invalid or expired: {token}")
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
@handle_exception
def authorize():
    grant_type = request.form.get('grant_type')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    scope = request.form.get('scope')
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


@app.route('/api/alive', methods=['GET'])
def alive():
    return {"ALIVE": "t"}


@app.route('/api/Config/AddNewUser', methods=['GET', 'POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def add_new_user():
    return {"Error": None}, 200


@app.route('/api/Config/UserConfig', methods=['POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def user_config():
    data = request.get_json()
    if not data:
        logging.error("Invalid request payload: Empty or malformed JSON")
        return jsonify({"Error": "Invalid request payload"}), 400

    authorization_token = data.get("AuthorizationToken")
    if not authorization_token:
        logging.error("AuthorizationToken is missing in the request")
        return jsonify({"Error": "AuthorizationToken is required"}), 400

    # If no additional configuration is needed, we can return a basic response
    response = {
        "Error": None,
        "StepName": "UserConfig",
        "WizardStepDescription": "This is where you add your website credentials",
        "WizardStepTitle": "Add Credentials",
        "ConfigItems": [

        ]
    }
    print(f"Response {response}", response)
    logging.info(f"UserConfig response: {response}")
    return response, 200


@app.route('/api/Config/SaveUserConfig', methods=['POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def save_user_config():
    data = request.get_json()

    if not data:
        logging.error("Invalid request payload: Empty or malformed JSON")
        # return jsonify({"Error": "Invalid request payload"}), 400

    authorization_token = data.get("AuthorizationToken")
    if not authorization_token:
        logging.error("AuthorizationToken is missing in the request")
        # return jsonify({"Error": "AuthorizationToken is required"}), 400

    # If no additional configuration saving is needed, we simply return the next step
    response = {
        "Error": None,
        "StepName": "UserConfig",  # Indicate the wizard is complete or the next step
        "WizardStepDescription": "Configuration saved successfully.",
        "WizardStepTitle": "UserConfig",
        "ConfigItems": config_items
    }

    print(f"SaveUserConfig response: {response}")
    return response, 200


# Sample configuration items
config_items = [
]


@app.route('/api/Order/Orders', methods=['GET', 'POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def orders():
    data = request.get_json()
    date_str = data.get('UTCTimeFrom')
    linnworks_data = sync_orders.get_orders(True)
    return linnworks_data, 200


@app.route('/api/Order/Despatch', methods=['POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def despatch():
    data = request.get_json()
    orders = data.get('Orders', [])
    logging.info("despatch request started")
    logging.info(f" data: {orders}")

    despatch_data = {
        "Orders": orders,
    }

    response = sync_orders.send_despatch_request(despatch_data)
    print (f' output {response}')
    if response is None:
        return jsonify({"Error": "Failed to send despatch request", "Orders": []}), 500

    return response, 200


@app.route('/api/Config/ConfigDeleted', methods=['GET', 'POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def config_deleted():
    return {}, 200


@app.route('/api/Config/ConfigTest', methods=['GET', 'POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def config_test():
    # This endpoint is used by Linnworks to test the connection
    return jsonify({"Status": "Success", "Message": "Configuration is valid"}), 200


# API Endpoint to get products
@app.route('/api/Product/Products', methods=['POST'])
@auth.login_required
@handle_exception
def get_products():
    data = request.get_json()
    page_number = data.get('PageNumber', 1)

    # Fetch products for the requested page
    result = get_products_by_page(page_number)
    products = result['Products']
    has_more_pages = result['HasMorePages']

    logging.info(f"get product request {page_number}")

    # Format the products
    formatted_products = [{
        "SKU": product['fields'].get('Mazuma Variant SKU'),
        "Title": product['fields'].get('Title'),
        "Quantity": product['fields'].get('Mazuma Variant Inventory Qty', 0),
        "Price": product['fields'].get('Mazuma Buy Price', 0.0),
        "Reference": product['id']
    } for product in products]

    print(f"Get Product Request response: Page {page_number}")
    return jsonify({
        "Error": None,
        "HasMorePages": has_more_pages,
        "Products": formatted_products
    }), 200


@app.route('/api/Config/ShippingTags', methods=['POST', 'GET'])
@auth.login_required
@add_token_to_response
@handle_exception
def payment_shipment_tags():
    return {"Error": None}, 200


@app.route('/api/Config/PaymentTags', methods=['POST', 'GET'])
@auth.login_required
@add_token_to_response
@handle_exception
def payment_payment_tags():
    return {"Error": None}, 200


def run_sync_inventory(data):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("run_sync_inventory")
    loop.run_until_complete(sync_inventory(data))


@app.route('/api/Product/InventoryUpdate', methods=['POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def inventory_update():
    data = request.get_json()
    threading.Thread(target=run_sync_inventory, args=(data,)).start()

    return {"Error": None}, 200


def run_sync_price(data):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sync_price.sync_price(data))


@app.route('/api/Product/PriceUpdate', methods=['POST', 'GET'])
@auth.login_required
@add_token_to_response
@handle_exception
def price_update():
    data = request.get_json()
    threading.Thread(target=run_sync_price, args=(data,)).start()
    #logging.info("Update Price")
    return {"Error": None}, 200


@app.route('/api/Listing/ListingUpdate', methods=['POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def listing_update():
    data = request.get_json()
    sync_update_listing.sync_catalogue.sync_catalogue(data)
    #logging.info("sync_catalogue")
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
        print("GetConfiguratorSettings requested")
        return jsonify(response), 200
    except Exception as e:
        logging.error(f"Error in get_configurator_settings: {str(e)}", exc_info=True)
        return jsonify({"Error": str(e), "Stack Trace": traceback.format_exc(), "AuthorizationToken": None}), 500


@app.route('/api/image/<path:filename>')
def serve_image(filename):
    try:
        # Adjust the directory path according to where your static folder is located
        directory = os.path.join(current_app.root_path, 'static', 'image')
        file_path = os.path.join(directory, filename)
        logging.info("Image requested")
        logging.info(f"Directory: {directory}")
        logging.info(f"File path: {file_path}")

        # Check if the file exists
        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            return jsonify({"error": "File not found"}), 404

        # Check if the file has read permissions
        if not os.access(file_path, os.R_OK):
            logging.error(f"File not accessible: {file_path}")
            return jsonify({"error": "File not accessible"}), 403

        # Serve the file
        return send_file(file_path, mimetype='image/png')

    except Exception as e:
        logging.error(f"Error serving image {filename}: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
