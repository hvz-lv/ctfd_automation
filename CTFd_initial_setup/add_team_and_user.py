import requests
from csv import DictReader
import urllib3
import sys
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_team(session, base_url, team_name, team_password):
    """Create a team with a specific password"""
    team_data = {
        "name": team_name,
        "password": team_password  
    }
    
    r = session.post(f"{base_url}/api/v1/teams", json=team_data, headers={"Content-Type": "application/json"}, verify=False)
    
    if r.status_code == 200:
        team_id = r.json()["data"]["id"]
        print(f"Team '{team_name}' created with ID {team_id}")
        return team_id
    else:
        print(f"Failed to create team '{team_name}': {r.status_code} - {r.text}")
        return None

def create_user(session, base_url, email, password):
    """Create a user with username derived from the email"""
    username = email.split('@')[0]  # Derive username from email
    
    r = session.post(
        f"{base_url}/api/v1/users?notify=true",  # Notify sends email with credentials
        json={
            "name": username,
            "email": email,
            "password": password,
            "type": "user",
            "verified": True,
            "hidden": False,
            "banned": False,
            "fields": [],
        },
        headers={"Content-Type": "application/json"},
        verify=False
    )

    if r.status_code == 200:
        user_id = r.json()["data"]["id"]
        print(f"User created successfully: Username: {username}, Password: {password}, Email: {email}")
        return user_id
    else:
        print(f"Failed to create user {username}. Status: {r.status_code}. Response: {r.text}")
        return None

def add_user_to_team(session, base_url, team_id, user_id):
    """Add a user to an existing team by team ID"""
    r = session.post(f"{base_url}/api/v1/teams/{team_id}/members", 
                     json={"user_id": user_id},
                     headers={"Content-Type": "application/json"},
                     verify=False)
    
    if r.status_code == 200:
        print(f"User with ID {user_id} added to team ID {team_id}")
    else:
        print(f"Failed to add user {user_id} to team {team_id}: {r.status_code} - {r.text}")

def main():
    url = "https://127.0.0.1"  # Your CTFd URL
    token = sys.argv[1]  

    # Create API session
    url = url.strip("/")
    s = requests.Session()
    s.headers.update({"Authorization": f"Token {token}"})

    # Read teams_and_members.csv
    teams = DictReader(open("team_and_users.csv"))

    for team in teams:
        team_name = team["team"]
        team_password = team["team_password"]
        members = team["members"].split("|")  # Split members by pipe character

        # Create the team and get the team ID
        team_id = create_team(s, url, team_name, team_password)
        if not team_id:
            continue  # If team creation failed, skip to the next team

        # Add each member to the team
        for i in range(0, len(members), 3):
            email = members[i + 2]
            password = members[i + 1]
            
            # Create user
            user_id = create_user(s, url, email, password)
            if user_id:
                # Add the user to the team
                add_user_to_team(s, url, team_id, user_id)

if __name__ == "__main__":
    main()
