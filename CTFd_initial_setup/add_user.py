import sys
import requests
from csv import DictReader
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    url = "https://127.0.0.1"  # Your CTFd URL
    token = sys.argv[1]
    
    # Create API Session
    url = url.rstrip("/")  # Remove trailing slash if present
    s = requests.Session()
    s.headers.update({"Authorization": f"Token {token}"})

    # Read users.csv with username, email, and password
    users = DictReader(open("/home/ubuntu/ctfd_automation/csv_files/users.csv"))

    for user in users:
        # Post the user data to create the account
        r = s.post(
            f"{url}/api/v1/users?notify=true",  # Notify sends email with credentials
            json={
                "name": user["username"],  # Use username for the "name" field
                "email": user["email"],
                "password": user["password"],
                "type": "user",  # Set account type to "user"
                "verified": True,  # Mark the user as verified
                "hidden": False,  # User visibility
                "banned": False,  # User ban status
                "fields": [],  # No additional fields
            },
            headers={"Content-Type": "application/json"},
            verify=False
        )
        # Output response
        if r.status_code == 200:
            print(f"User created successfully: Username: {user['username']}, Password: {user['password']}, Email: {user['email']}")
        else:
            print(f"Failed to create user {user['username']}. Status: {r.status_code}. Response: {r.text}")

if __name__ == "__main__":
    main()
