import requests
import json

# Set the URLs for the endpoints
AUTH_URL = "http://localhost:8000/api/oauth/authorize"
INVENTORY_UPDATE_URL = "http://localhost:8000/api/Product/InventoryUpdate"

# Data for obtaining the access token
AUTH_DATA = {
    'grant_type': 'client_credentials',
    'client_id': 'META100',
    'client_secret': 'META472732',
    'scope': 'read write'
}

# JSON data to be sent in the POST request to InventoryUpdate
JSON_DATA = {
    "Products": [
        {"SKU": "MAZP15425G2T1", "Reference": "recM3yHPDPkc5lbX3", "Quantity": 300},
        {"SKU": "MAZP17115G2T1", "Reference": "rec4u2gCGHkV7RrA0", "Quantity": 300},
        {"SKU": "MAZP17074G2T1", "Reference": "rec2cdCKK3eq6S7lw", "Quantity": 300},
        {"SKU": "MAZP12946G2T1", "Reference": "recMQ7GbSyW5cRXie", "Quantity": 300},
        {"SKU": "MAZP23033G2T1", "Reference": "recW3GSvbM06Vo6Cv", "Quantity": 300}
    ]
}

# Function to obtain an access token
def get_access_token():
    print("Obtaining access token...")
    response = requests.post(AUTH_URL, data=AUTH_DATA)
    response_data = response.json()
    print(f"Authorization Response: {response_data}")  # Debugging print

    access_token = response_data.get('access_token')
    if access_token:
        print(f"Access token obtained: {access_token}")
        return access_token
    else:
        print("Failed to obtain access token.")
        exit(1)

# Function to send a POST request to InventoryUpdate
def test_post_request(access_token):
    print("Testing POST request...")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.post(INVENTORY_UPDATE_URL, headers=headers, json=JSON_DATA)
    print(f"Response Body: {response.json()}")
    print(f"HTTP Code: {response.status_code}")

    if response.status_code == 200:
        print("POST request test passed!")
    else:
        print("POST request test failed!")

# Main function to run the tests
def main():
    access_token = get_access_token()
    test_post_request(access_token)

if __name__ == "__main__":
    main()