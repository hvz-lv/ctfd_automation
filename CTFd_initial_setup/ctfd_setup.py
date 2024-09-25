import requests
from bs4 import BeautifulSoup
import sys
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get the user mode and admin credentials from the command line arguments
if len(sys.argv) != 5:
    print("Usage: python3 ctfd_setup.py <user_mode> <admin_username> <admin_email> <admin_password>")
    sys.exit(1)

user_mode = sys.argv[1]
admin_username = sys.argv[2]
admin_email = sys.argv[3]
admin_password = sys.argv[4]

setup_page_url = f'https://127.0.0.1/setup'

# Create a session to persist cookies
session = requests.Session()

# Step 1: Access the setup page to get the CSRF token
setup_page_response = session.get(setup_page_url, verify=False)

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
setup_url = f'https://127.0.0.1/setup'
setup_data = {
    'ctf_name': 'CTFd',
    'ctf_description': 'CTFd description',
    'user_mode': user_mode,  # Use the mode passed from the bash script
    'challenge_visibility': 'private',
    'account_visibility': 'public',
    'score_visibility': 'public',
    'registration_visibility': 'public',
    'verify_emails': 'false',
    'team_size': '5',
    'name': admin_username,  # Use the admin username from the bash script
    'email': admin_email,  # Use the admin email from the bash script
    'password': admin_password,  # Use the admin password from the bash script
    'ctf_logo': '',
    'ctf_banner': '',
    'ctf_small_icon': '',
    'ctf_theme': 'core',
    'nonce': csrf_token,  # Add CSRF token here
    '_submit': 'Submit'
}

# Send setup request
setup_response = session.post(setup_url, data=setup_data, verify=False)

# Check if setup was successful
if setup_response.status_code == 200 or setup_response.status_code == 302:
    print("Setup successful!")
else:
    print(f"Setup failed. Status code: {setup_response.status_code}")
