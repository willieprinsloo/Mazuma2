from flask import Flask, jsonify, request, Response, current_app, send_file
from flask_httpauth import HTTPTokenAuth
import traceback
import logging
import uuid
import json
import requests
from functools import wraps
from datetime import datetime, timedelta
from redis import Redis
import asyncio
import os
import threading
import time

import sync_inventory
import sync_orders
import sync_price
import sync_update_listing
from sync_down_catalogue import get_products_by_page

app = Flask(__name__)
auth = HTTPTokenAuth(scheme='Bearer')
redis_client = Redis(host='localhost', port=6379, db=0)

logging.basicConfig(filename="logs.log", level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Airtable API details
base_key = 'appd8lN3nYsIT139L'
token = "patxr7JPJypDemRWQ.00484d9b9fc6dbb0fc4b3f8b0ab838a146a314df809048191d5cff9d6d64da1e"
AIRTABLE_API_URL = f'https://api.airtable.com/v0/{base_key}/linnworks_suppliers'

# In-memory cache for Airtable data
supplier_cache = {}
cache_lock = threading.Lock()

# Set the interval for cache updates (30 minutes)
CACHE_UPDATE_INTERVAL = 1800  # 30 minutes


def fetch_suppliers():
    global supplier_cache
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(AIRTABLE_API_URL, headers=headers)

    if response.status_code != 200:
        logging.error("Failed to fetch suppliers from Airtable")
        return

    suppliers = response.json().get('records', [])
    with cache_lock:
        supplier_cache = {}
        total_records = len(suppliers)
        valid_records = 0

        for supplier in suppliers:
            fields = supplier.get('fields', {})
            client_id = fields.get('Client ID')
            client_secret = fields.get('Client Secret')
            live_status = fields.get('Live')


            if client_id and client_secret and live_status:
                supplier_cache[client_id] = {
                    'Client Secret': client_secret,
                    'Live': live_status
                }
                valid_records += 1
            else:
                logging.warning(f"Skipping supplier record due to missing fields: {supplier}")

        logging.info(
            f"Processed {total_records} records. Valid records: {valid_records}. Skipped records: {total_records - valid_records}.")


def update_cache():
    while True:
        fetch_suppliers()
        time.sleep(CACHE_UPDATE_INTERVAL)


# Start the background thread to update the cache
threading.Thread(target=update_cache, daemon=True).start()


def handle_exception(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Error in {f.__name__}: {str(e)}")
            return jsonify({"Error": str(e), "Stack Trace": traceback.format_exc(), "AuthorizationToken": None}), 500

    return decorated


def generate_token():
    return str(uuid.uuid4())


def add_token(token, client_id, scope, expires_in=18600):
    expiration_time = datetime.utcnow() + timedelta(seconds=expires_in)
    token_data = {'client_id': client_id, 'scope': scope, 'expires_at': expiration_time.isoformat()}
    redis_client.set(token, json.dumps(token_data), ex=expires_in)


@auth.verify_token
def verify_token(token):
    token_data_json = redis_client.get(token)
    if token_data_json:
        token_data = json.loads(token_data_json)
        if datetime.fromisoformat(token_data['expires_at']) > datetime.utcnow():
            return token_data['client_id']
    return None


def validate_client(client_id, client_secret):
    print(client_id, client_secret)
    with cache_lock:
        supplier_info = supplier_cache.get(client_id)

    if not supplier_info:
        return False

    return (supplier_info['Client Secret'] == client_secret and supplier_info['Live'] in ['Yes', 'No'])


@app.route('/api/oauth/authorize', methods=['POST'])
@handle_exception
def authorize():
    grant_type = request.form.get('grant_type')
    client_id = request.form.get('client_id')
    client_secret = request.form.get('client_secret')
    scope = request.form.get('scope')

    if grant_type != 'client_credentials':
        logging.info("unsupported_grant_type")
        return jsonify({"error": "unsupported_grant_type"}), 400

    if not validate_client(client_id, client_secret):
        logging.info("invalid_client")
        return jsonify({"error": "invalid_client"}), 401

    requested_scopes = scope.split()
    if not all(s in ["read", "write"] for s in requested_scopes):
        logging.info("invalid_scope")
        return jsonify({"error": "invalid_scope"}), 400

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
    client_id = auth.current_user()
    linnworks_data = sync_orders.get_orders(client_id, True)
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
    print(f' output {response}')
    if response is None:
        return jsonify({"Error": "Failed to send dispatch request", "Orders": []}), 500

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
    result = get_products_by_page(page_number, client_id)
    products = result['Products']
    has_more_pages = result['HasMorePages']

    logging.info(f"get product request {page_number}")

    # Format the products
    formatted_products = [{
        "SKU": product['fields'].get('Supplier Variant SKU'),
        "Title": product['fields'].get('Title'),
        "Quantity": product['fields'].get('Supplier Variant Inventory Qty', 0),
        "Price": product['fields'].get('Supplier Buy Price', 0.0),
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
    client_id = auth.current_user()

    loop.run_until_complete(sync_inventory.sync_inventory(data, supplier_name=client_id))


@app.route('/api/Product/InventoryUpdate', methods=['POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def inventory_update():
    data = request.get_json()
    threading.Thread(target=run_sync_inventory, args=(data,)).start()

    return {"Error": None}, 200


def run_sync_price(data, supplier_name):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sync_price.sync_price(data, supplier_name=supplier_name))


@app.route('/api/Product/PriceUpdate', methods=['POST', 'GET'])
@auth.login_required
@add_token_to_response
@handle_exception
def price_update():
    data = request.get_json()
    client_id = auth.current_user()
    threading.Thread(target=run_sync_price, args=(data, client_id)).start()
    # logging.info("Update Price")
    return {"Error": None}, 200


@app.route('/api/Listing/ListingUpdate', methods=['POST'])
@auth.login_required
@add_token_to_response
@handle_exception
def listing_update():
    data = request.get_json()
    sync_update_listing.sync_catalogue.sync_catalogue(data)
    # logging.info("sync_catalogue")
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
