import requests
import logging

# Airtable API details
base_key = 'appd8lN3nYsIT139L'
token = "patxr7JPJypDemRWQ.00484d9b9fc6dbb0fc4b3f8b0ab838a146a314df809048191d5cff9d6d64da1e"
AIRTABLE_API_URL = f'https://api.airtable.com/v0/{base_key}/Products'
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

def get_products_by_page(page_number):
    logging.info(f"Starting to fetch products for page number: {page_number}")
    offset = None
    current_page = 1
    page_size = 100

    while current_page < page_number:
        params = {'pageSize': page_size}
        if offset:
            params['offset'] = offset

        try:
            response = requests.get(AIRTABLE_API_URL, headers=headers, params=params)
            response.raise_for_status()
            response_data = response.json()

            offset = response_data.get('offset')
            if not offset:
                logging.warning(f"Reached end of data before page {page_number}. Returning empty list.")
                return {"HasMorePages": False, "Products": []}

            current_page += 1

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch products while skipping pages: {e}")
            return {"HasMorePages": False, "Products": []}
        except Exception as e:
            logging.error(f"An unexpected error occurred while skipping pages: {e}")
            return {"HasMorePages": False, "Products": []}

    # Fetch the requested page
    params = {'pageSize': page_size}
    if offset:
        params['offset'] = offset

    try:
        response = requests.get(AIRTABLE_API_URL, headers=headers, params=params)
        response.raise_for_status()
        response_data = response.json()

        products = response_data.get('records', [])
        logging.info(f"Fetched {len(products)} products from page {page_number}")

        has_more_pages = 'offset' in response_data
        return {"HasMorePages": has_more_pages, "Products": products}

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch products for page {page_number}: {e}")
        return {"HasMorePages": False, "Products": []}
    except Exception as e:
        logging.error(f"An unexpected error occurred while fetching page {page_number}: {e}")
        return {"HasMorePages": False, "Products": []}

# Example usage
page_number = 1  # Change this to the desired page number
result = get_products_by_page(page_number)


#print(f"Fetched {len(result['Products'])} products from page {page_number}")
#print(f"HasMorePages: {result['HasMorePages']}")
#print(result['Products'])