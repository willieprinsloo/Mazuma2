import requests
import json
import random

# Set the URLs for the endpoints
AUTH_URL = "http://localhost:8000/api/oauth/authorize"
PRICE_UPDATE_URL = "http://localhost:8000/api/Product/PriceUpdate"

#AUTH_URL = "http://works.reboxed.co/api/oauth/authorize"
#PRICE_UPDATE_URL = "http://works.reboxed.co/api/Product/PriceUpdate"


# Data for obtaining the access token
AUTH_DATA = {
    'grant_type': 'client_credentials',
    'client_id': 'MAZUMA',
    'client_secret': 'META472732',
    'scope': 'read write'
}

# Function to generate JSON data with random prices
def generate_price_data():
    products = [
        {"SKU": "1", "Reference": "recM3yHPDPkc5lbX3"},
        {"SKU": "2", "Reference": "rec4u2gCGHkV7RrA0"},
        {"SKU": "3", "Reference": "rec2cdCKK3eq6S7lw"},
        {"SKU": "4", "Reference": "recMQ7GbSyW5cRXie"},
        {"SKU": "5", "Reference": "recW3GSvbM06Vo6Cv"}
    ]
    for product in products:
        product["Price"] = round(random.uniform(10.0, 200.0), 2)
    return {"Products": products}

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

# Function to send a POST request to PriceUpdate
def test_post_request(access_token, json_data):
    print("Testing POST request...")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.post(PRICE_UPDATE_URL, headers=headers, json=json_data)
    print(f"Response Body: {response.json()}")
    print(f"HTTP Code: {response.status_code}")

    if response.status_code == 200:
        print("POST request test passed!")
    else:
        print("POST request test failed!")

# Main function to run the tests
def main():
    access_token = get_access_token()
    json_data = generate_price_data()
    test_post_request(access_token, json_data)

if __name__ == "__main__":
    main()