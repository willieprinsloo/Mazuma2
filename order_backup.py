import requests
from datetime import datetime, timedelta
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Airtable API details
base_key = 'appd8lN3nYsIT139L'
order_table_name = 'tbleRUUaL4t4TfPEf'
order_view_name = 'viwSGwefEGPr9fohB'
line_items_table_name = 'tbleRUUaL4t4TfPEf'
token = "patxr7JPJypDemRWQ.00484d9b9fc6dbb0fc4b3f8b0ab838a146a314df809048191d5cff9d6d64da1e"

order_api_url = f'https://api.airtable.com/v0/{base_key}/{order_table_name}'
line_items_api_url = f'https://api.airtable.com/v0/{base_key}/{line_items_table_name}'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

def get_orders_after_date(date_str):
    def fetch_orders_after_date(date_str):
        #date_str = "2024-07-01 13:50"
        filter_formula = f'AND(IS_AFTER({{Created Time}}, "{date_str}"), {{Fulfillment Location (from Order Line Items)}}="MAZUMA")'

        params = {
            'filterByFormula': filter_formula,
            'view': order_view_name,
            'maxRecords': 500,
            'sort[0][field]': 'Shopify Order Date',
            'sort[0][direction]': 'desc'
        }
        try:
            response = requests.get(order_api_url, headers=headers, params=params, verify=False)

            if response.status_code == 200:
                print(response.json)
                return response.json()
            else:
                logging.error(f'Failed to fetch orders, Error: {response.text}')
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f'Requests exception: {e}')
            return None

    def fetch_order_line_items_concurrently(line_item_ids):
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_item = {executor.submit(fetch_single_line_item, line_item_id): line_item_id for line_item_id in line_item_ids}
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

    def transform_to_linnworks_format(orders):
        linnworks_orders = []
        print("transform_to_linnworks_format")
        print(orders)
        for order in orders['records']:
            line_item_ids = order['fields'].get('Order Line Items', [])
            order_line_items = fetch_order_line_items_concurrently(line_item_ids) if line_item_ids else []
            print("orders")
            # Prepare order items
            order_items = []
            for item in order_line_items:
                mazuma_sku = item.get("Mazuma Variant SKU", "")

                print(mazuma_sku)

                if not mazuma_sku:
                    continue  # Ignore items without Mazuma Variant SKU

                order_items.append({
                    "TaxCostInclusive": True,
                    "UseChannelTax": False,
                    "IsService": False,
                    "OrderLineNumber": str(item.get("Line Item ID", "")),
                    "SKU": mazuma_sku,
                    "PricePerUnit": item.get("Variant Price", 0),
                    "Qty": item.get("Quantity", 0),
                    "TaxRate": item.get("VAT", 0),
                    "LinePercentDiscount": 0.0,
                    "ItemTitle": item.get("Variant Full Description", ""),
                    "Options": []
                })

            if not order_items:
                continue  # Ignore orders without valid line items

            # Convert date to desired format
            received_date = order['fields'].get('Shopify Order Date', '')
            paid_on = order['fields'].get('Shopify Order Date', '')

            if received_date:
                received_date = datetime.strptime(received_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%SZ")

            if paid_on:
                paid_on = datetime.strptime(paid_on, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%d %H:%M:%SZ")

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
                "ExtendedProperties": [
                    {
                        "Name": "Fulfillment Location",
                        "Value": "Mazuma"
                    }
                ],
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
                "ReceivedDate": received_date,
                "DispatchBy": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%SZ"),  # Example dispatch by date
                "PaidOn": paid_on,
                "PostalServiceCost": order['fields'].get('Total Shipping Price', 0),
                "PostalServiceTaxRate": 20.0,
                "UseChannelTax": False
            }

            linnworks_orders.append(linnworks_order)

        return {
            "Error": None,
            "HasMorePages": False,
            "Orders": linnworks_orders
        }

    orders = fetch_orders_after_date(date_str)
    if orders:
        linnworks_data = transform_to_linnworks_format(orders)
        return linnworks_data
    else:
        return {"Error": "No orders fetched or an error occurred."}
#print(get_orders_after_date("2024-07-07 13:50"))