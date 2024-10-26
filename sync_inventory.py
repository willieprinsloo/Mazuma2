import aiohttp
import asyncio
from datetime import datetime
import logging

json_string = {
    "Products": [
        {"SKU": "1", "Reference": "recM3yHPDPkc5lbX3", "Quantity": 20},
        {"SKU": "2", "Reference": "rec4u2gCGHkV7RrA0", "Quantity": 30},
        {"SKU": "3", "Reference": "recM3yHPDPkc5lbX3", "Quantity": 20},
        {"SKU": "4", "Reference": "rec4u2gCGHkV7RrA0", "Quantity": 30},
        {"SKU": "5", "Reference": "recM3yHPDPkc5lbX3", "Quantity": 20},
        {"SKU": "6", "Reference": "rec4u2gCGHkV7RrA0", "Quantity": 30},
        {"SKU": "7", "Reference": "recM3yHPDPkc5lbX3", "Quantity": 20},
        {"SKU": "8", "Reference": "rec4u2gCGHkV7RrA0", "Quantity": 30},
    ]
}

# Airtable API details
base_key = 'appd8lN3nYsIT139L'
token = "patxr7JPJypDemRWQ.00484d9b9fc6dbb0fc4b3f8b0ab838a146a314df809048191d5cff9d6d64da1e"

#Production
#AIRTABLE_API_URL = f'https://api.airtable.com/v0/{base_key}/Products'
AIRTABLE_API_URL = f'https://api.airtable.com/v0/{base_key}/Productsv2'



headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Function to find records by SKU in batches
async def find_records_by_skus(session, skus, supplier_name, batch_size=50):
    record_ids = {}
    for i in range(0, len(skus), batch_size):
        batch = skus[i:i + batch_size]

        formula = 'OR(' + ','.join(
            [f"AND({{Supplier Variant SKU}}='{sku}', {{Supplier Name}}='{supplier_name}')" for sku in batch]) + ')'

        print (formula)
        params = {'filterByFormula': formula}
        try:
            async with session.get(AIRTABLE_API_URL, headers=headers, params=params) as response:
                if response.status == 200:
                    batch_records = {record['fields']['Supplier Variant SKU']: record['id'] for record in
                                     (await response.json()).get('records', [])}
                    record_ids.update(batch_records)
                    logging.info(f"Fetched records for batch {i // batch_size + 1}: {batch_records}")
                else:
                    logging.error(f"Failed to fetch records: {response.status}, {await response.text()}")
        except asyncio.TimeoutError:
            logging.error(f"Update timed out for batch {i // batch_size + 1}")
    return record_ids

# Function to sync data with Airtable in bulk
async def sync_inventory(data, supplier_name):
    logging.info("Inventory sync started")
    current_date = datetime.now().strftime('%Y-%m-%d')

    skus = [product['SKU'] for product in data['Products']]

    async with aiohttp.ClientSession() as session:
        record_ids = await find_records_by_skus(session,supplier_name=supplier_name , skus=skus)
        records_to_update = []
        records_to_create = []

        for product in data['Products']:
            record_id = record_ids.get(product['SKU'])
            if record_id:
                record = {
                    'id': record_id,
                    'fields': {
                        'Supplier Variant SKU': product['SKU'],
                        'Supplier LW Reference': product['Reference'],
                        'Supplier Variant Inventory Qty': product['Quantity'],
                        'Supplier LastQtyUpdated': current_date
                    }
                }
                records_to_update.append(record)
            else:
                logging.info(f"Record with SKU {product['SKU']} not found. Adding new record.")
                print(f"Record with SKU {product['SKU']} not found. Adding new record.")
                record = {
                    'fields': {
                        'Supplier Variant SKU': product['SKU'],
                        'Supplier LW Reference': product['Reference'],
                        'Supplier Variant Inventory Qty': product['Quantity'],
                        'Supplier LastQtyUpdated': current_date
                    }
                }
                records_to_create.append(record)

        # Update existing records
        if records_to_update:
            await batch_update(session, records_to_update)
        # Create new records
        if records_to_create:
            await batch_create(session, records_to_create)

# Function to perform batch updates
async def batch_update(session, records):
    logging.info("Starting Batch Update...")
    for i in range(0, len(records), 10):
        batch = records[i:i + 10]
        data = {'records': batch}
        await asyncio.sleep(1)  # To respect Airtable rate limits
        logging.info(f'Updating batch {i // 10 + 1}: {batch}')  # Debugging log
        try:
            print (data)
            async with session.patch(AIRTABLE_API_URL, headers=headers, json=data) as response:
                if response.status in [200, 201]:
                    logging.info(f'Successfully updated records for batch (Inventory) {i // 10 + 1}')

                else:
                    logging.error(f'Failed to update records for batch {i // 10 + 1}, Error: {await response.text()}')
        except asyncio.TimeoutError:
            logging.error(f"Request timed out for batch {i // 10 + 1}")

# Function to perform batch creates
async def batch_create(session, records):
    logging.info("Starting Batch Create...")
    for i in range(0, len(records), 10):
        batch = records[i:i + 10]
        data = {'records': batch}
        await asyncio.sleep(1)  # To respect Airtable rate limits
        logging.info(f'Creating batch {i // 10 + 1}: {batch}')  # Debugging log
        try:
            async with session.post(AIRTABLE_API_URL, headers=headers, json=data) as response:
                if response.status in [200, 201]:
                    logging.info(f'Successfully created records for batch {i // 10 + 1}')
                else:
                    logging.error(f'Failed to create records for batch {i // 10 + 1}, Error: {await response.text()}')
        except asyncio.TimeoutError:
            logging.error(f"Request timed out for batch {i // 10 + 1}")

# Example of how to run the sync_inventory function
if __name__ == "__main__":
    asyncio.run(sync_inventory(json_string,supplier_name='MAZUMA'))

# Function to run sync periodically
async def run_periodically(data, interval, supplier_name):
    while True:
        logging.info("Periodic sync started")
        await sync_inventory(data, supplier_name)
        await asyncio.sleep(interval)

def start_periodic_sync():
    logging.info("Starting periodic sync")
    asyncio.run(run_periodically(json_string, 3600))