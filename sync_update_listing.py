import requests
import json
from datetime import datetime

# JSON data
data = {
    "AuthorizationToken": "0dfdbaf3e4d5434f825e774e31bcc148",
    "Listings": [
        {
            "Attributes": [
                {
                    "AttributeID": "Brand Name",
                    "AttributeValue": "CoolProducts",
                    "IsCustomAttribute": False
                },
                {
                    "AttributeID": "Condition",
                    "AttributeValue": "new",
                    "IsCustomAttribute": False
                }
            ],
            "Categories": [
                "test"
            ],
            "ConfiguratorId": 13,
            "Description": "This is a high quality item",
            "ExternalListingId": "",
            "Images": [
                {
                    "Tags": [
                        "Main_image"
                    ],
                    "Url": "https://server.com/images.linnlive.com/f9a059eb1008300ab7eea8d586dd5000/bf24d3f3-1830-4ad4-ad8e-f01b9bbb00f1.jpg"
                },
                {
                    "Tags": [
                        "Main_image"
                    ],
                    "Url": "https://server.com/images.linnlive.com/f9a059eb1008300ab7eea8d586dd5000/bf24d3f3-1830-4ad4-ad8e-f01b9bbb00f1.jpg"
                }
            ],
            "Price": 10,
            "Quantity": 1,
            "SKU": "TEST#",
            "ShippingMethods": [
                {}
            ],
            "TemplateId": 2,
            "Title": "T-shirt",
            "VariationOptions": [
                {
                    "Name": "Gender",
                    "Position": 1,
                    "Values": [
                        {
                            "Position": 1,
                            "value": "Women"
                        },
                        {
                            "Position": 2,
                            "value": "Men"
                        }
                    ]
                }
            ],
            "Variations": [
                {
                    "AttributeSettings": [
                        {}
                    ],
                    "Images": [
                        {}
                    ],
                    "OptionValues": [
                        {
                            "Name": "Gender",
                            "Position": 1,
                            "Value": "Women"
                        }
                    ],
                    "Price": 10,
                    "Quantity": 5,
                    "SKU": "XYZ-1",
                    "Title": "Nice Women’s T-shirt. One size."
                },
                {
                    "AttributeSettings": [
                        {}
                    ],
                    "Images": [
                        {}
                    ],
                    "OptionValues": [
                        {
                            "Name": "Gender",
                            "Position": 2,
                            "Value": "Men"
                        }
                    ],
                    "Price": 10,
                    "Quantity": 3,
                    "SKU": "TEST4",
                    "Title": "Nice Men’s T-shirt. One size."
                }
            ],
            "Settings": [
                {
                    "ConfiguratorId": 13,
                    "Settings": {
                        "GeneralSettings": [
                            {}
                        ],
                        "PaymentMethods": [],
                        "PaymentSettings": [
                            {}
                        ],
                        "ReturnsSettings": [
                            {
                                "ID": "ReturnCost",
                                "Values": [
                                    "Buyer"
                                ]
                            },
                            {
                                "ID": "ReturnDays",
                                "Values": [
                                    "14"
                                ]
                            }
                        ],
                        "ShippingSettings": [
                            {
                                "ID": "ShippedFromCountry",
                                "Values": [
                                    "United Kingdom"
                                ]
                            },
                            {
                                "ID": "ShippedFromTown",
                                "Values": [
                                    "Chichester"
                                ]
                            },
                            {
                                "ID": "ShippedFromPostCode",
                                "Values": [
                                    "PO19 8DJ"
                                ]
                            }
                        ],
                        "VariationSettings": [
                            {
                                "ID": "VariationTheme",
                                "Values": [
                                    "Color-Size"
                                ]
                            }
                        ]
                    }
                }
            ],
            "Type": "CREATE"
        }
        # Add more listings here as needed
    ]
}

# Airtable API details
base_key = 'appd8lN3nYsIT139L'
token = "patxr7JPJypDemRWQ.00484d9b9fc6dbb0fc4b3f8b0ab838a146a314df809048191d5cff9d6d64da1e"
AIRTABLE_API_URL = f'https://api.airtable.com/v0/{base_key}/Products'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# Function to find record by SKU
def find_record_by_sku(sku):
    params = {
        'filterByFormula': f'{{SKU}}="{sku}"'
    }
    response = requests.get(AIRTABLE_API_URL, headers=headers, params=params)
    if response.status_code == 200:
        records = response.json().get('records')
        if records:
            return records[0]['id']
    return None

# Function to sync data with Airtable
def sync_catalogue(data):
    current_date = datetime.now().strftime('%Y-%m-%d')
    records_to_update = []
    records_to_create = []

    for listing in data['Listings']:
        record_id = find_record_by_sku(listing['SKU'])
        im = listing['Images'][0]

        record = {
            'fields': {
                'Body (HTML)': listing['Description'],
                'Mazuma Buy Price': listing['Price'],
                'Mazuma Variant Inventory Qty': listing['Quantity'],
                'Mazuma Variant SKU': listing['SKU'],
                'Title': listing['Title'],
            }
        }

        if record_id:
            record['id'] = record_id
            records_to_update.append(record)
        else:
            records_to_create.append(record)

    # Update existing records in batches of 10
    if records_to_update:
        batch_update(records_to_update)

    # Create new records in batches of 10
    if records_to_create:
        batch_create(records_to_create)

def batch_update(records):
    for i in range(0, len(records), 10):
        batch = records[i:i + 10]
        data = {'records': batch}
        print(f'Updating batch: {batch}')  # Debugging print
        response = requests.patch(AIRTABLE_API_URL, headers=headers, json=data)
        if response.status_code in [200, 201]:
            print(f'Successfully updated records: {batch}')
        else:
            print(f'Failed to update records, Error: {response.text}')

def batch_create(records):
    for i in range(0, len(records), 10):
        batch = records[i:i + 10]
        data = {'records': batch}
        print(f'Creating batch: {batch}')  # Debugging print
        response = requests.post(AIRTABLE_API_URL, headers=headers, json=data)
        if response.status_code in [200, 201]:
            print(f'Successfully created records: {batch}')
        else:
            print(f'Failed to create records, Error: {response.text}')

# Run the sync
#sync_catalogue(data)