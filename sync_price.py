import aiohttp
import asyncio
from datetime import datetime
import logging

# JSON data
data = {
    "Products": [
        {"SKU": "TEST1", "Reference": "122440", "Price": 102.99, "Tag": ""},
        {"SKU": "TEST2", "Reference": "122440", "Price": 202.99, "Tag": ""},
        # Add more products as needed
    ],
    "AuthorizationToken": "4d1aa44d211641a48da9ae269ff68975"
}

# Airtable API details
base_key = 'appd8lN3nYsIT139L'
token = "patxr7JPJypDemRWQ.00484d9b9fc6dbb0fc4b3f8b0ab838a146a314df809048191d5cff9d6d64da1e"
AIRTABLE_API_URL = f'https://api.airtable.com/v0/{base_key}/Products'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}


# Function to find records by SKU in batches
async def find_records_by_skus(session, skus, batch_size=50):
    record_ids = {}
    for i in range(0, len(skus), batch_size):
        batch = skus[i:i + batch_size]
        formula = 'OR(' + ','.join([f"{{Mazuma Variant SKU}}='{sku}'" for sku in batch]) + ')'
        params = {'filterByFormula': formula}
        try:
            async with session.get(AIRTABLE_API_URL, headers=headers, params=params) as response:
                if response.status == 200:
                    batch_records = {record['fields']['Mazuma Variant SKU']: record['id'] for record in
                                     (await response.json()).get('records', [])}
                    record_ids.update(batch_records)
                    logging.info(f"Fetched records for batch {i // batch_size + 1}: {batch_records}")
                else:
                    logging.error(f"Failed to fetch records: {response.status}, {await response.text()}")
        except asyncio.TimeoutError:
            logging.error(f"Update timed out for batch {i // batch_size + 1}")
    return record_ids


# Function to sync prices with Airtable in bulk
async def sync_price(data):
    logging.info("Price sync started")
    print("Price sync started")
    current_date = datetime.now().strftime('%Y-%m-%d')
    skus = [product['SKU'] for product in data['Products']]

    async with aiohttp.ClientSession() as session:
        record_ids = await find_records_by_skus(session, skus)
        records_to_update = []

        for product in data['Products']:
            record_id = record_ids.get(product['SKU'])
            record = {
                'fields': {
                    'Mazuma Variant SKU': product['SKU'],
                    'Mazuma Buy Price': product['Price'],
                    'Mazuma LastPriceUpdated': current_date
                }
            }
            if record_id:
                record['id'] = record_id
            records_to_update.append(record)

        # Update existing records
        if records_to_update:
            await batch_update(session, records_to_update)


# Function to perform batch updates
async def batch_update(session, records):
    logging.info("Price batch update")
    logging.info("Starting Batch Update...")
    for i in range(0, len(records), 10):
        batch = records[i:i + 10]
        data = {'records': batch}
        await asyncio.sleep(1)  # To respect Airtable rate limits
        logging.info(f'Updating batch {i // 10 + 1}: {batch}')  # Debugging log
        try:
            async with session.patch(AIRTABLE_API_URL, headers=headers, json=data) as response:
                if response.status in [200, 201]:
                    logging.info(f'Successfully updated records for batch {i // 10 + 1}')
                    print (f'Successfully updated records for batch {i // 10 + 1}')
                else:
                    logging.error(f'Failed to update records for batch {i // 10 + 1}, Error: {await response.text()}')
        except asyncio.TimeoutError:
            logging.error(f"Request timed out for batch {i // 10 + 1}")

# Example of how to run the sync_price function
#if __name__ == "__main__":
#   asyncio.run(sync_price(data))
