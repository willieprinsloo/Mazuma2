import requests
import json

# Set the URLs for the endpoints

AUTH_URL = "http://works.reboxed.co/api/oauth/authorize"
DESPATCH_URL = "http://works.reboxed.co/api/Order/Despatch"  # Change this to your actual endpoint

#AUTH_URL = "http://localhost:8000/api/oauth/authorize"
#DESPATCH_URL = "http://localhost:8000/api/Order/Despatch"  # Change this to your actual endpoint


# Data for obtaining the access token
AUTH_DATA = {
    'grant_type': 'client_credentials',
    'client_id': 'META100',
    'client_secret': 'META472732',
    'scope': 'read write'
}

# Function to generate JSON data with despatch orders
def generate_despatch_data():
    orders = [
        {
            "ReferenceNumber": "18725",
            "ShippingVendor": "NONE",
            "ShippingMethod": "Default",
            "TrackingNumber": "JT202044101GB",
            "ProcessedOn": "2024-07-25 10:01:37Z",
            "Items": [
                {
                    "SKU": "JT202044101GB",
                    "OrderLineNumber": "14632808874215",
                    "DespatchedQuantity": 1
                }
            ]
        }
    ]
    return {"Orders": orders}


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

# Function to send a POST request to the Despatch endpoint
def test_post_request(access_token, json_data):
    print("Testing POST request...")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.post(DESPATCH_URL, headers=headers, json=json_data)
    print(f"Response Body: {response.json()}")
    print(f"HTTP Code: {response.status_code}")

    if response.status_code == 200:
        print("POST request test passed!")
    else:
        print("POST request test failed!")

# Main function to run the tests
def main():
    access_token = get_access_token()
    json_data = generate_despatch_data()
    test_post_request(access_token, json_data)

if __name__ == "__main__":
    main()