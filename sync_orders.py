import requests
from datetime import datetime, timedelta, time
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
from sendMail import sendMail  # Import the sendMail function
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Airtable API details
base_key = 'appd8lN3nYsIT139L'
order_table_name = 'tblGj6D9MkzvcqIWY'
order_view_name = 'viwk8IXeFWVSsqhzk'
line_items_table_name = 'tbl7Bvy9ZLLMh3Xyj'

# Production
#order_table_name = 'tbleRUUaL4t4TfPEf'
#order_view_name = 'viwSGwefEGPr9fohB'
#line_items_table_name = 'tblQJYV5oc6EvSVuu'

token = "patxr7JPJypDemRWQ.00484d9b9fc6dbb0fc4b3f8b0ab838a146a314df809048191d5cff9d6d64da1e"

order_api_url = f'https://api.airtable.com/v0/{base_key}/{order_table_name}'
line_items_api_url = f'https://api.airtable.com/v0/{base_key}/{line_items_table_name}'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}


def update_order_status(order_id, status):
    update_data = {
        "fields": {
            "Supplier Fulfilment Status": status
        }
    }
    try:
        response = requests.patch(f'{order_api_url}/{order_id}', headers=headers, json=update_data)
        if response.status_code != 200:
            logging.error(f'Failed to update order status for order {order_id}, Error: {response.text}')
    except requests.exceptions.RequestException as e:
        logging.error(f'Requests exception when updating order status: {e}')


def print_order_summary(orders_data):
    if orders_data.get("Orders"):
        print("\nSummary of Retrieved Orders:\n")
        for order in orders_data["Orders"]:
            order_number = order.get("ReferenceNumber", "N/A")
            shopify_date = order.get("ReceivedDate", "N/A")
            customer_name = order.get("ChannelBuyerName", "N/A")
            fulfillment_status = order.get("PaymentStatus", "N/A")
            override_recommendation = order.get("Override Recommendation", "N/A")
            fraud_risk_recommendation = order.get("Fraud Risk Recommendation", "N/A")

            print(f"Order Number: {order_number} Order Date {shopify_date}")
            print(f"Customer: {customer_name}  Payment Status {fulfillment_status} ")
            print(f"Override Recommendation: {override_recommendation}")
            print(f"Fraud Risk Recommendation: {fraud_risk_recommendation}")
            print("-" * 40)  # Separator for clarity
    else:
        print("No orders retrieved or an error occurred.")

def print_raw_summary(orders, update_status):
    if orders:
        print("\n\033[1mOrder Sync to Lynnworks:\033[0m\n")
        email_content = "<h2 style='color: black;'>Summary of Retrieved Orders:</h2><ul style='list-style-type: none;'>"

        for order in orders:
            fields = order.get('fields', {})
            order_number = fields.get("Order Number", "N/A")
            shopify_date = fields.get("Shopify Order Date", "N/A")
            customer_name = f"{fields.get('Customer First Name', 'N/A')} {fields.get('Customer Last Name', 'N/A')}"
            fulfillment_status = fields.get("Financial Status Latest", "N/A")
            override_recommendation = fields.get("Override Recommendation", "N/A")
            fraud_risk_recommendation = fields.get("Fraud Risk Recommendation", "N/A")

            # Console output with colors
            print(f"\033[94mOrder Number:\033[0m {order_number} \033[94mOrder Date:\033[0m {shopify_date}")
            print(f"\033[94mCustomer:\033[0m {customer_name} \033[94mPayment Status:\033[0m {fulfillment_status}")
            print(f"\033[94mOverride Recommendation:\033[0m {override_recommendation}")
            print(f"\033[94mFraud Risk Recommendation:\033[0m {fraud_risk_recommendation}")
            print("-" * 40)  # Separator for clarity

            # Email content with HTML and inline CSS for colors
            email_content += f"<li><strong style='color: grey;'>Order Number:</strong> {order_number}<br>"
            email_content += f"<strong style='color: grey;'>Order Date:</strong> {shopify_date}<br>"
            email_content += f"<strong style='color: grey;'>Customer:</strong> {customer_name}<br>"
            email_content += f"<strong style='color: grey;'>Payment Status:</strong> {fulfillment_status}<br>"
            email_content += f"<strong style='color: grey;'>Override Recommendation:</strong> {override_recommendation}<br>"
            email_content += f"<strong style='color: grey;'>Fraud Risk Recommendation:</strong> {fraud_risk_recommendation}</li><hr>"

        email_content += "</ul>"
        update_status = True
        # Send the email only if there are orders
        if update_status:
            sendMail('ivan@reboxed.co', 'prinsloo.willie@gmail.com', 'Order Sync', email_content)
            sendMail('ivan@reboxed.co', 'ivan@reboxed.co', 'Order Sync', email_content)
            print("Summary email sent successfully.")

    else:
        print("No orders retrieved or an error occurred.")


def print_and_email_dispatched_orders(despatch_response):
    dispatched_orders = despatch_response.get("Orders", [])

    if dispatched_orders:
        print("\n\033[1mDispatched Orders Summary:\033[0m\n")
        email_content = "<h2 style='color: black;'>Dispatched Orders Summary:</h2><ul style='list-style-type: none;'>"

        for order in dispatched_orders:
            # Debugging print to check the structure of 'order'
            print(f"Order Data: {order}")

            # Check if the order is actually a dictionary
            if not isinstance(order, dict):
                print("Error: Order is not a dictionary. Skipping this order.")
                continue

            reference_number = order.get("ReferenceNumber", "N/A")

            # Console output with colors
            print(f"\033[94mOrder Number:\033[0m {reference_number}")

            # Email content with HTML and inline CSS for colors
            email_content += f"<li><strong style='color: grey;'>Order Number:</strong> {reference_number}<br>"

        email_content += "</ul>"

        # Send email with dispatched orders summary
        sendMail('ivan@reboxed.co', 'prinsloo.willie@gmail.com', 'Dispatched Orders Summary', email_content)
        sendMail('ivan@reboxed.co', 'ivan@reboxed.co', 'Dispatched Orders Summary', email_content)
        print("Dispatched orders summary email sent successfully.")
    else:
        print("No dispatched orders to print or email.")


def get_orders(client_id, update_status = False):
    def fetch_orders():
        five_days_ago = datetime.now() - timedelta(days=4)
        filter_formula = f'''
        AND(
            FIND("{client_id}", {{Fulfillment Location (from Order Line Items)}}) > 0,
            {{Supplier Fulfilment Status}}=BLANK(),     
            {{Fulfillment Status Latest}} != "Cancelled",
            IS_AFTER({{Shopify Order Date}}, "{five_days_ago.isoformat()}"),
            OR(
                {{Override Recommendation}}=TRUE(),
                {{Fraud Risk Recommendation}}="accept"
            )
            
        )
        '''
        print (filter_formula)
        # filter_formula = f'AND(IS_AFTER({{Shopify Order Date}}, "{date_str}"), {{Fulfillment Location (from Order Line Items)}}="MAZUMA", OR({{Override Recommendation}}=TRUE(), {{Fraud Risk Recommendation}}="accept"))'
        params = {
            'filterByFormula': filter_formula,
            'view': order_view_name,
            'maxRecords': 50,
            'sort[0][field]': 'Shopify Order Date',
            'sort[0][direction]': 'desc'
        }
        try:
            response = requests.get(order_api_url, headers=headers, params=params, verify=False)
            logging.info(f' Order request results: {response}')
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f'Failed to fetch orders, Error: {response.text}')
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f'Requests exception: {e}')
            return None

    def fetch_order_line_items_concurrently(line_item_ids):
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_item = {executor.submit(fetch_single_line_item, line_item_id): line_item_id for line_item_id in
                              line_item_ids}
            line_items = []
            for future in as_completed(future_to_item):
                line_item = future.result()
                if line_item:
                    line_items.append(line_item)
            return line_items

    def fetch_single_line_item(line_item_id):
        try:
            response = requests.get(f'{line_items_api_url}/{line_item_id}', headers=headers, verify=False)
            if response.status_code == 200:
                return response.json().get('fields')
            else:
                logging.error(f'Failed to fetch line item {line_item_id}, Error: {response.text}')
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f'Requests exception: {e}')
            return None

    def map_payment_status(status):
        status_mapping = {
            'paid': 'PAID',
            'unpaid': 'UNPAID',
            'voided': 'CANCELLED'
        }
        return status_mapping.get(status.lower(), 'PAID')

    def transform_to_linnworks_format(orders, update_status):
        linnworks_orders = []

        if len(orders["records"]) > 0:
            logging.info(f'Number of orders fetched: {len(orders["records"])}')
            logging.info(f'Order fetch: {orders["records"]}')
            print_raw_summary(orders["records"],update_status)

        for order in orders['records']:
            line_item_ids = order['fields'].get('Order Line Items', [])
            order_line_items = fetch_order_line_items_concurrently(line_item_ids) if line_item_ids else []
            # Prepare order items
            order_items = []
            for item in order_line_items:
                mazuma_sku = item.get("Mazuma Variant SKU", "")
                location = item.get("Fulfillment Location", "")
                if location == 'MAZUMA':
                    order_items.append({
                        "TaxCostInclusive": True,
                        "UseChannelTax": False,
                        "IsService": False,
                        "OrderLineNumber": str(item.get("Line Item ID", "")),
                        "SKU": mazuma_sku,
                        "PricePerUnit": item.get("Order Value", 0),
                        "Qty": item.get("Quantity", 0),
                        "TaxRate": item.get("VAT", 0),
                        "LinePercentDiscount": 0.0,
                        "ItemTitle": item.get("Variant Full Description", ""),
                        "Options": []
                    })

            # Prepare the order in Linnworks format
            linnworks_order = {
                "BillingAddress": {
                    "FullName": f"Mr {order['fields'].get('Customer First Name', '')} {order['fields'].get('Customer Last Name', '')}",
                    "Company": "",
                    "Address1": order['fields'].get('Shipping Address Line 1', ''),
                    "Address2": "",
                    "Address3": "",
                    "Town": order['fields'].get('Shipping Town or City', ''),
                    "Region": order['fields'].get('Shipping County or Province', ''),
                    "PostCode": order['fields'].get('Postcode or Zip', ''),
                    "Country": order['fields'].get('Shipping Country', ''),
                    "CountryCode": "GB",
                    "PhoneNumber": order['fields'].get('Recipient Phone Number', ''),
                    "EmailAddress": order['fields'].get('Customer Email Address', '')
                },
                "DeliveryAddress": {
                    "FullName": f"Mr {order['fields'].get('Recipient First Name', '')} {order['fields'].get('Recipient Last Name', '')}",
                    "Company": "",
                    "Address1": order['fields'].get('Shipping Address Line 1', ''),
                    "Address2": "",
                    "Address3": "",
                    "Town": order['fields'].get('Shipping Town or City', ''),
                    "Region": order['fields'].get('Shipping County or Province', ''),
                    "PostCode": order['fields'].get('Postcode or Zip', ''),
                    "Country": order['fields'].get('Shipping Country', ''),
                    "CountryCode": "GB",
                    "PhoneNumber": order['fields'].get('Recipient Phone Number', ''),
                    "EmailAddress": order['fields'].get('Customer Email Address', '')
                },
                "OrderItems": order_items,
                "ExtendedProperties": [],
                "Notes": [],
                "Site": "",
                "MatchPostalServiceTag": order['fields'].get('Selected Shipping Option', ''),
                "MatchPaymentMethodTag": order['fields'].get('Payment Gateway', ''),
                "PaymentStatus": map_payment_status(order['fields'].get('Financial Status Latest', 'Paid')),
                "ChannelBuyerName": f"{order['fields'].get('Customer First Name', '')} {order['fields'].get('Customer Last Name', '')}",
                "ReferenceNumber": order['fields'].get('Order Number', ''),
                "ExternalReference": str(order['fields'].get('Order ID', '')),
                "SecondaryReferenceNumber": None,
                "Currency": "GBP",
                "ReceivedDate": order['fields'].get('Shopify Order Date', ''),
                "DispatchBy": (datetime.now() + timedelta(days=10)).isoformat(),  # Just an example dispatch by date
                "PaidOn": order['fields'].get('Shopify Order Date', ''),
                "PostalServiceCost": order['fields'].get('Total Shipping Price', 0),
                "PostalServiceTaxRate": 20.0,
                "UseChannelTax": False
            }

            linnworks_orders.append(linnworks_order)
            if update_status:
                update_order_status(order['id'], "Linnworks")
        return {
            "Error": None,
            "HasMorePages": False,
            "Orders": linnworks_orders
        }

    orders = fetch_orders()
    if orders:
        linnworks_data = transform_to_linnworks_format(orders, update_status)
        return linnworks_data
    else:
        return {"Error": "No orders fetched or an error occurred."}


def send_despatch_request(despatch_data):
    logging.info("Despatch request started for {despatch_data}")
    print("Despatch request started")

    despatch_response = {
        "Error": None,
        "Orders": []
    }

    for order in despatch_data.get("Orders", []):
        reference_number = order.get("ReferenceNumber", "")
        tracking_number = order.get("TrackingNumber", "")
        order_id = None

        # Fetch order from Airtable
        try:
            response = requests.get(f'{order_api_url}?filterByFormula={{Order Number}}="{reference_number}"',
                                    headers=headers)
            if response.status_code == 200:
                records = response.json().get('records', [])
                if records:
                    order_id = records[0]['id']
                    order_fields = records[0]['fields']
                else:
                    despatch_response["Orders"].append({
                        "Error": f"Order {reference_number} not found",
                        "ReferenceNumber": reference_number,
                        "Retry": False
                    })
                    continue
            else:
                logging.error(f'Failed to fetch order {reference_number}, Error: {response.text}')
                despatch_response["Orders"].append({
                    "Error": f"Failed to fetch order {reference_number}",
                    "ReferenceNumber": reference_number,
                    "Retry": False
                })
                continue
        except requests.exceptions.RequestException as e:
            logging.error(f'Requests exception: {e}')
            despatch_response["Orders"].append({
                "Error": f"Requests exception: {e}",
                "ReferenceNumber": reference_number,
                "Retry": True  # Retry if there's a request exception
            })
            continue

        # Update order in Airtable
        order_update_data = {
            "fields": {
                "Linnworks Fulfilment Status": "fulfilled",
            }
        }
        try:
            response = requests.patch(f'{order_api_url}/{order_id}', headers=headers, json=order_update_data)
            if response.status_code != 200:
                logging.error(f'Failed to update order {reference_number}, Error: {response.text}')
                despatch_response["Orders"].append({
                    "Error": f"Failed to update order {reference_number}",
                    "ReferenceNumber": reference_number,
                    "Retry": False
                })
                continue
        except requests.exceptions.RequestException as e:
            logging.error(f'Requests exception: {e}')
            despatch_response["Orders"].append({
                "Error": f"Requests exception: {e}",
                "ReferenceNumber": reference_number,
                "Retry": True  # Retry if there's a request exception
            })
            continue

        # Prepare batch update for tracking numbers in order line items
        line_item_ids = [item.get("OrderLineNumber", "") for item in order.get("Items", [])]
        line_item_records_to_update = []

        try:
            response = requests.get(f'{line_items_api_url}?filterByFormula=OR(' + ','.join(
                [f'{{Line Item ID}}="{line_item_id}"' for line_item_id in line_item_ids]) + ')', headers=headers)
            if response.status_code == 200:
                line_item_records = response.json().get('records', [])
                for record in line_item_records:
                    line_item_update_data = {
                        "id": record['id'],
                        "fields": {
                            "Linnworks Tracking Number": tracking_number,
                            "Fulfilment Status": "fulfilled"
                        }
                    }

                    line_item_records_to_update.append(line_item_update_data)
            else:
                logging.error(f'Failed to fetch line items for order {reference_number}, Error: {response.text}')
                despatch_response["Orders"].append({
                    "Error": f"Failed to fetch line items for order {reference_number}",
                    "ReferenceNumber": reference_number,
                    "Retry": False
                })
                continue
        except requests.exceptions.RequestException as e:
            logging.error(f'Requests exception: {e}')
            despatch_response["Orders"].append({
                "Error": f"Requests exception: {e}",
                "ReferenceNumber": reference_number,
                "Retry": True  # Retry if there's a request exception
            })
            continue

        # Batch update the tracking numbers
        if line_item_records_to_update:
            print(f"Calling batch update....{line_item_records_to_update}")
            batch_update(line_item_records_to_update)

        despatch_response["Orders"].append({
            "Error": None,
            "ReferenceNumber": reference_number,
            "Retry": False
        })

    # Use the new function to print and email dispatched orders
    print_and_email_dispatched_orders(despatch_response)

    return despatch_response


def batch_update(records):
    print(records)
    logging.info("Starting Batch Update...")
    for i in range(0, len(records), 10):
        batch = records[i:i + 10]
        data = {'records': batch}
        time.sleep(1)  # To respect Airtable rate limits
        logging.info(f'Updating batch {i // 10 + 1}: {batch}')  # Debugging log
        try:
            response = requests.patch(line_items_api_url, headers=headers, json=data)
            if response.status_code in [200, 201]:
                logging.info(f'Successfully updated records for batch {i // 10 + 1}')
                print(f'Successfully updated records for batch {i // 10 + 1}')
            else:
                logging.error(f'Failed to update records for batch {i // 10 + 1}, Error: {response.text}')
        except requests.exceptions.RequestException as e:
            logging.error(f'Requests exception for batch {i // 10 + 1}: {e}')

print(get_orders(False))
