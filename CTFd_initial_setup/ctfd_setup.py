import requests
from bs4 import BeautifulSoup
import sys
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


setup_page_url = f'https://localhost/setup'

# Create a session to persist cookies
session = requests.Session()

# Step 1: Access the setup page to get the CSRF token
setup_page_response = session.get(setup_page_url,verify=False)

# Parse the HTML to find the CSRF token
soup = BeautifulSoup(setup_page_response.text, 'html.parser')
csrf_token_element = soup.find('input', {'name': 'nonce'})

if csrf_token_element:
    csrf_token = csrf_token_element.get('value')
    print(f"CSRF Token: {csrf_token}")
else:
    print("CSRF token not found on the setup page.")
    sys.exit(1)

# Step 2: Perform the setup using the CSRF token
setup_url = f'https://localhost/setup'
setup_data = {
    'ctf_name': 'CTFd',
    'ctf_description': 'CTFd description',
    'user_mode': 'teams',
    'challenge_visibility': 'private',
    'account_visibility': 'public',
    'score_visibility': 'public',
    'registration_visibility': 'public',
    'verify_emails': 'false',
    'team_size': '5',
    'name': 'admin',
    'email': 'admin@admin.com',
    'password': 'admin',
    'ctf_logo': '',
    'ctf_banner': '',
    'ctf_small_icon': '',
    'ctf_theme': 'core',
    'nonce': csrf_token,  # Add CSRF token here
    '_submit': 'Submit'
}

# Send setup request
setup_response = session.post(setup_url, data=setup_data,verify=False)

# Check if setup was successful
if setup_response.status_code == 200 or setup_response.status_code == 302:
    print("Setup successful!")
else:
    print(f"Setup failed. Status code: {setup_response.status_code}")

