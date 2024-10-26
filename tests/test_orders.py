import requests
import json

# Set the URLs for the endpoints
AUTH_URL = "http://localhost:8000/api/oauth/authorize"
ORDERS_URL = "http://localhost:8000/api/Order/Orders"  # Change this to your actual endpoint

# Data for obtaining the access token
AUTH_DATA = {
    'grant_type': 'client_credentials',
    'client_id': 'REBOXED',
    'client_secret': 'META472732',
    'scope': 'read write'
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

# Function to send a POST request to the Orders endpoint
def test_get_orders_request(access_token):
    print("Testing GET Orders request...")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    # Example JSON data to send with the request (if any)
    json_data = {
        'UTCTimeFrom': '2024-09-01'
    }
    response = requests.post(ORDERS_URL, headers=headers, json=json_data)
    print(f"HTTP Code: {response.status_code}")
    print(f"Response Body: {response.json()}")  # Print response body for debugging

    if response.status_code == 200:
        print("GET Orders request test passed!")
    else:
        print("GET Orders request test failed!")

# Main function to run the tests
def main():
    access_token = get_access_token()
    test_get_orders_request(access_token)

if __name__ == "__main__":
    main()