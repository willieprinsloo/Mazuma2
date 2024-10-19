import requests
import json
from datetime import datetime
import pandas as pd

# Airtable API details
base_key = 'appd8lN3nYsIT139L'
token = "patxr7JPJypDemRWQ.00484d9b9fc6dbb0fc4b3f8b0ab838a146a314df809048191d5cff9d6d64da1e"
AIRTABLE_API_URL = f'https://api.airtable.com/v0/{base_key}/Products'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}


# Function to update data in Airtable from CSV using batch requests
def update_data_from_csv(file_path):
    df = pd.read_csv(file_path)
    current_date = datetime.now().strftime('%Y-%m-%d')
    batch_size = 10
    records_to_update = []

    for index, row in df.iterrows():
        sku = row['SKU']
        price = row['Reboxed Price']

        # Find the Airtable record ID for the given SKU
        record_id = find_record_id_by_sku(sku)
        if record_id:
            record = {
                'id': record_id,
                'fields': {
                    'Mazuma Variant SKU': sku,
                    'Mazuma Buy Price': price,
                    'Mazuma LastPriceUpdated': current_date
                }
            }
            records_to_update.append(record)

        # When batch size is reached, send the request
        if len(records_to_update) == batch_size:
            send_batch(records_to_update)
            records_to_update = []

    # Send remaining records if any
    if records_to_update:
        send_batch(records_to_update)


# Function to find the record ID by SKU
def find_record_id_by_sku(sku):
    params = {
        'filterByFormula': f"{{Mazuma Variant SKU}}='{sku}'"
    }
    response = requests.get(AIRTABLE_API_URL, headers=headers, params=params)
    if response.status_code == 200:
        records = response.json().get('records')
        if records:
            return records[0]['id']
    return None


# Function to send a batch of records to Airtable
def send_batch(records):
    data = {'records': records}
    print (f"Updating {records}")
    response = requests.patch(AIRTABLE_API_URL, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print(f'Successfully updated batch of {len(records)} products.')
    else:
        print(f'Failed to update batch, Error: {response.text}')


# Run the update function
update_data_from_csv('import.csv')