## Automation through API key of CTFd platform

+ Clone CTFd automation repository 

```bash
git clone https://github.com/hvz-lv/ctfd_automation.git
```

**Challenges creation**

The ``challenges.py`` script automates the creation and updating of challenges in the CTFd platform. It reads challenge details from a CSV file ```challenges.csv``` and handles:

1. Creating or updating challenges.
2. Setting flags, hints, hints costs, and challenge prerequisites.
3. Managing challenge types (standard, dynamic, or first blood).
4. Handling file uploads for challenges.
5. Sequencing challenge unlocking and managing challenge-specific configurations, such as dynamic decay rates for dynamic challenges.

The script interacts with the CTFd API to streamline challenge management in bulk.

+ Edit ```challenges.py``` to put your CTFd URL and API token.

```bash
cd ctfd_automation
nano challenges.py
```

``` python
# API configuration
api_url = "add_your_ctfd_url_here"
api_token = "add_your_ctfd_api_token_here"
```

```python
import requests
import csv
import os
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# API configuration
api_url = "add_your_ctfd_url_here"
api_token = "add_your_ctfd_api_token_here"
headers = {
    "Authorization": f"Bearer {api_token}"
}
csv_file_path = "challenges.csv"  # Update this with your CSV file path
# Define API endpoints
file_upload_url = f"{api_url}/files"
hint_url = f"{api_url}/hints"
flag_url = f"{api_url}/flags"
challenges_url = f"{api_url}/challenges"
def create_challenge(challenge_data):
    response = requests.post(challenges_url, headers=headers, json=challenge_data, verify=False)
    if response.status_code == 200:
        challenge_id = response.json()["data"]["id"]
        print(f"Challenge '{challenge_data['name']}' created successfully with ID {challenge_id}.")
        return challenge_id
    else:
        print(f"Unexpected response status: {response.status_code}")
        print("Response text:", response.text)
        return None
def update_challenge(challenge_id, update_data):
    update_url = f"{challenges_url}/{challenge_id}"
    response = requests.patch(update_url, headers=headers, json=update_data, verify=False)
    if response.status_code == 200:
        print(f"Challenge '{challenge_id}' updated successfully.")
    else:
        print(f"Failed to update challenge '{challenge_id}': {response.status_code}")
        print("Response text:", response.text)
def upload_file(file_path, challenge_id):
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return None
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'challenge_id': challenge_id,
            'type': 'challenge'
        }
        response = requests.post(file_upload_url, headers=headers, files=files, data=data, verify=False)        
        if response.status_code == 200:
            file_data = response.json()["data"][0]
            print(f"File '{file_path}' uploaded and associated with challenge ID {challenge_id}.")
            return file_data
        else:
            print(f"Failed to upload file '{file_path}': {response.status_code} - {response.text}")
            return None
def add_flag(challenge_id, content, flag_type):
    flag_data = {
        "challenge_id": challenge_id,
        "content": content,
        "type": flag_type
    }
    response = requests.post(flag_url, headers=headers, json=flag_data, verify=False)    
    if response.status_code == 200:
        print(f"Successfully added flag to challenge ID {challenge_id}")
    else:
        print(f"Failed to add flag: {response.status_code} - {response.text}")

def add_hint(challenge_id, content, cost=0, prerequisites=None):
    # Set an empty array for prerequisites if none are provided
    hint_data = {
        "challenge_id": challenge_id,
        "content": content,
        "cost": cost,
        "requirements": {"prerequisites": prerequisites if prerequisites else []}
    }
    response = requests.post(hint_url, headers=headers, json=hint_data, verify=False)    
    if response.status_code == 200:
        hint_id = response.json()["data"]["id"]
        print(f"Successfully added hint with ID {hint_id} to challenge ID {challenge_id}")
        return hint_id
    else:
        print(f"Failed to add hint: {response.status_code} - {response.text}")
        return None

def update_hint(hint_id, prerequisites):
    hint_update_url = f"{hint_url}/{hint_id}"
    # Set an empty array for prerequisites if none are provided
    hint_data = {
        "requirements": {"prerequisites": prerequisites if prerequisites else []}
    }
    response = requests.patch(hint_update_url, headers=headers, json=hint_data, verify=False)    
    if response.status_code == 200:
        print(f"Successfully updated hint ID {hint_id} with prerequisites")
    else:
        print(f"Failed to update hint ID {hint_id}: {response.status_code} - {response.text}")


def main():
    hint_ids, ch_dict = [dict() for _ in range(2)]
    with open(csv_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            challenge_type = row.get("Type", "standard")  # Default to 'standard' if not provided
            # Basic challenge data
            challenge_data = {
                "name": row["Name"],
                "category": row["Category"],
                "description": row["Description"],
                "max_attempts": int(row["Max Attempts"]),
                "state": row["State"],  # Should be 'visible' or 'hidden'
                "type": challenge_type,
                "connection_info": row.get("Connection_Info", ""),  # Handle connection info
                "value": int(row["Value"])
            }
            # Handle first blood bonus for firstblood challenges
            if challenge_type == "firstblood":
                first_blood_bonus = list(map(int, row["First_Blood_Bonus"].split("|")))
                challenge_data.update({
                    "first_blood_bonus[0]": first_blood_bonus[0],
                    "first_blood_bonus[1]": first_blood_bonus[1],
                    "first_blood_bonus[2]": first_blood_bonus[2]
                })
            # Additional fields for dynamic challenges
            if challenge_type == "dynamic":
                challenge_data["initial"] = int(row["Initial"])
                challenge_data["decay"] = int(row["Decay"])
                challenge_data["minimum"] = int(row["Minimum"])
            hints = row["Hints"].split("|")
            hints_cost = list(map(int, row["Hints_Cost"].split("|")))
            challenge_prerequisites = list(row.get("Challenge_Prerequisites", "").split("|"))
            # Create or update the challenge
            challenge_id = create_challenge(challenge_data)            
            if challenge_id:
                # Upload file if path is provided
                file_path = row.get("File_Path")
                if file_path:
                    upload_file(file_path, challenge_id)
                # Add flag if provided
                flag_content = row.get("Flag")
                flag_type = row.get("Flag_Type", "static")
                if flag_content:
                    add_flag(challenge_id, flag_content, flag_type)
                hint_ids[challenge_id] = []
                for hint_content, hint_cost in zip(hints, hints_cost):
                    hint_id = add_hint(challenge_id, hint_content, hint_cost)
                    if hint_id:
                        hint_ids[challenge_id].append(hint_id)                
                # Update hints with sequential prerequisites
                for index, hint_id in enumerate(hint_ids[challenge_id]):
                    prerequisites = [hid for hid in hint_ids[challenge_id][:index]]
                    update_hint(hint_id, prerequisites)
                
                ch_dict[challenge_id] = [challenge_data["name"], challenge_prerequisites]
                time.sleep(0.5)
    for key in ch_dict.keys():
        if ch_dict[key][1][0] != "":
            for x in range(0, len(ch_dict[key][1])):
                for k, value in ch_dict.items():
                    if value[0] == ch_dict[key][1][x]:
                        ch_dict[key][1][x] = k
    for key in ch_dict.keys():
        if ch_dict[key][1][0] != "":
            update_challenge(key, {"requirements": {"prerequisites": ch_dict[key][1]}})

if __name__ == "__main__":
    main()
```



+ Edit ```challenges.csv``` for challenges creation

```bash
nano challenges.csv
```

```csv
Name,Category,Description,Max Attempts,State,Type,Connection_Info,Value,Initial,Decay,Minimum,First_Blood_Bonus,Flag_Type,Flag,Hints,Hints_Cost,Challenge_Prerequisites,File_Path
Standard Challenge 1,Linux,This is the description for Standard Challenge 1.,5,visible,standard,ssh 10.10.10.10,150,,,,,static,standard_flag_1|test_flag,Hint 1|Hint 2,10|20,,/home/ubuntu/ctfd_automatization/files/file3.zip|/home/ubuntu/ctfd_automatization/files/file1.zip
Standard Challenge 2,Web,This is the description for Standard Challenge 2.,3,visible,standard,,150,,,,,static,standard_flag_2,Hint 3|Hint 4,15|25,Standard Challenge 1,,
Standard Challenge 3,Forensics,This is the description for Standard Challenge 3.,4,hidden,standard,,200,,,,,static,standard_flag_3,Hint 5|Hint 6,20|30,Standard Challenge 1|Standard Challenge 2,,
Dynamic Challenge 1,Linux,This is the description for Dynamic Challenge 1.,5,visible,dynamic,,100,100,5,10,,static,dynamic_flag_1|test_flags,Hint 7|Hint 8,10|20,Standard Challenge 1,/home/ubuntu/ctfd_automatization/files/file3.zip|/home/ubuntu/ctfd_automatization/files/file1.zip
Dynamic Challenge 2,Web,This is the description for Dynamic Challenge 2.,3,visible,dynamic,,150,150,10,50,,static,dynamic_flag_2,Hint 9|Hint 10,15|25,Standard Challenge 2,,
Dynamic Challenge 3,Forensics,This is the description for Dynamic Challenge 3.,2,hidden,dynamic,,200,200,15,100,,static,dynamic_flag_3,Hint 11|Hint 12,20|30,Dynamic Challenge 1|Dynamic Challenge 2,,
First Blood Challenge 1,Linux,This is the description for First Blood Challenge 1.,5,visible,firstblood,,100,,,,"50|30|20",static,firstblood_flag_1|test_flags,Hint 13|Hint 14,10|20,Dynamic Challenge 1,/home/ubuntu/ctfd_automatization/files/file3.zip|/home/ubuntu/ctfd_automatization/files/file1.zip
First Blood Challenge 2,Web,This is the description for First Blood Challenge 2.,3,visible,firstblood,,150,,,,"40|25|15",static,firstblood_flag_2,Hint 15|Hint 16,15|25,First Blood Challenge 1,,
First Blood Challenge 3,Forensics,This is the description for First Blood Challenge 3.,4,hidden,firstblood,,200,,,,"60|40|30",static,firstblood_flag_3,Hint 17|Hint 18,20|30,First Blood Challenge 2,,
```
**This table shows information which you need to use in CSV** 
| Header                  | Description                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Name                    | The name of the challenge.                                                                                          |
| Category                | The category of the challenge (e.g., Linux, Web, Forensics).                                                        |
| Description             | A detailed description of the challenge.                                                                            |
| Max Attempts            | The maximum number of attempts a user can make on the challenge. Left 0 if attempts unlimited.                      |
| State                   | The visibility state of the challenge (e.g., visible, hidden).                                                      |
| Type                    | The type of challenge (e.g., standard, dynamic, firstblood).                                                        |
| Connection_Info         | Connection information for accessing the challenge (e.g., ssh 172.0.0.1).                 |
| Value                   | The base point value of the challenge.                                                                              |
| Initial                 | (Dynamic only) The initial value of the challenge. (Put the same value like "Value")                                                           |
| Decay                   | (Dynamic only) The decay rate of the challenge value over time.                                                     |
| Minimum                 | (Dynamic only) The minimum value the challenge can reach.                                                           |
| First_Blood_Bonus       | (Firstblood only) A pipe separated list of bonus points awarded for solving the challenge first (descending order) only for 1st,2nd,3rd place. |
| Flag_Type               | The type of flag used in the challenge (e.g., static, dynamic).                                                     |
| Flag                    | The challenge flag. If you have more flags use pipe between flags                                                   |
| Hints                   | (Optional) A list of hints for the challenge, separated by a pipe                                                   |
| Hints_Cost              | (Optional) The cost (in points) associated with purchasing each hint,separated by a pipe                            |
| Challenge_Prerequisites | (Optional) Pipe separated list of prerequisite challenges that must be solved before attempting this one.           |
| File_Path               | (Optional) Pipe separated list of file paths associated with the challenge.                                         |

+ After csv and py file editing, execute a script ```challenges.py```

``` bash
python3 challenges.py
```

+ Output should look like that

```bash
Challenge 'Standard Challenge 1' created successfully with ID 1342.
File '/home/ubuntu/ctfd_automatization/files/file3.zip' uploaded and associated with challenge ID 1342.
File '/home/ubuntu/ctfd_automatization/files/file1.zip' uploaded and associated with challenge ID 1342.
Successfully added flag 'standard_flag_1' to challenge ID 1342
Successfully added flag 'test_flag' to challenge ID 1342
Successfully added hint with ID 2599 to challenge ID 1342
Successfully added hint with ID 2600 to challenge ID 1342
Successfully updated hint ID 2599 with prerequisites
Successfully updated hint ID 2600 with prerequisites
```

+ Check if challenges created on CTFd platform.

### **User creation**

+ You have two ways how to make automation for users creation for 2 game modes:
1. User mode
2. Team mode. 

#### **User mode**

The ``` users.py ``` script automates the creation of users on the CTFd platform using the CTFd API. It typically reads user information (such as usernames, emails, and passwords) from a CSV file (users.csv) and registers these users in bulk. The script can assign roles (e.g., admin, player) and ensure that users are created with the correct credentials. This simplifies the process of managing user accounts by automating the creation of multiple users at once through the 

+ For user creation only use ```add_user.py``` python script and put your API token and URL of CTFd platform

```bash
nano add_user.py
```

```python
    url = "YOUR_CTFd_URL"  # Your CTFd URL
    token = "YOUR_API_TOKEN"  # Your API token
```
```python
import requests
from csv import DictReader
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    url = "https://10.1.69.102"  # Your CTFd URL
    token = "ctfd_548fa19baa2b585dd413cfedaf1e26b2df2cd87297cbf203e8f7abfcc4556c0a"  # Your API token

    # Create API Session
    url = url.strip("/")
    s = requests.Session()
    s.headers.update({"Authorization": f"Token {token}"})

    # Read users.csv with username, email, and password
    users = DictReader(open("users.csv"))

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

```



| Headers  | Discription                |
| -------- | -------------------------- |
| username | Username for CTFd platform |
| email    | Email for CTFd platform    |
| password | Password for CTFd platform |


+ Edit ```users.csv``` 

```csv
username,email,password
john_doe,john@example.com,supersecretpassword
jane_smith,jane@example.com,anotherpassword
```

+ Execute script ```add_user.py```

```bash
python3 add_user.py
```

+ Output should looks like that

```bash
User created successfully: Username: johny_doe, Password: supersecretpassword, Email: johny@example.com
User created successfully: Username: janes_smith, Password: anotherpassword, Email: janes@example.com
```

#### **Team mode**

The ```add_team_and_user.py``` script automates the creation of both teams and users in the CTFd platform via the API. It reads data from a CSV file ```team_and_users.csv``` and performs the following tasks:

1. Creates teams in CTFd.
2. Creates users and assigns them to the appropriate teams.
3. Ensures that teams and users are linked correctly, facilitating the bulk management of teams and their associated users.

This script simplifies the process of setting up team-based competitions in CTFd.

+ Edit API token and URL of CTFd platform in script ```add_team_and_user.py``` 

```bash
nano add_team_and_user.py
```

```python
    url = "YOUR_CTFd_URL"  # Your CTFd URL
    token = "YOUR_API_TOKEN"  # Your API token
```

```python
import requests
from csv import DictReader
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# Function creating team
def create_team(session, base_url, team_name, team_password):
    #Create a team with a specific password
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
# Function create user
def create_user(session, base_url, username, email, password):
    #Create a user and return their ID"""
    r = session.post(
        f"{base_url}/api/v1/users?notify=true",  # Notify sends email with credentials if webmail is setuped
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
# Function assign user to team 
def add_user_to_team(session, base_url, team_id, user_id):
    #Add a user to an existing team by team ID
    r = session.post(f"{base_url}/api/v1/teams/{team_id}/members", 
                     json={"user_id": user_id},
                     headers={"Content-Type": "application/json"},
                     verify=False)
    
    if r.status_code == 200:
        print(f"User with ID {user_id} added to team ID {team_id}")
    else:
        print(f"Failed to add user {user_id} to team {team_id}: {r.status_code} - {r.text}")

def main():
    url = "YOUR_CTFd_URL"  # Your CTFd URL
    token = "YOUR_API_TOKEN"  # Your API token

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
            username = members[i]
            password = members[i + 1]
            email = members[i + 2]

            # Create user
            user_id = create_user(s, url, username, email, password)
            if user_id:
                # Add the user to the team
                add_user_to_team(s, url, team_id, user_id)

if __name__ == "__main__":
    main()

```



+ Edit team and users csv file ```team_and_users.csv```

```csv
team,team_password,members
CyberSquad,cyber1234,alice_smith|alice_pass123|alice.smith@example.com|bob_jones|bob_pass456|bob.jones@example.com
TechTitans,tech4567,charlie_brown|charlie_pass789|charlie.brown@example.com|diana_williams|diana_pass012|diana.williams@example.com
DevMasters,dev7890,emma_johnson|emma_pass345|emma.johnson@example.com|frank_martin|frank_pass678|frank.martin@example.com
Innovators,innovate1,grace_lee|grace_pass901|grace.lee@example.com|hank_clark|hank_pass234|hank.clark@example.com
```

| Headers       | Description                                                     |
| ------------- | --------------------------------------------------------------- |
| team          | Team name                                                       |
| team_password | Team password for future joining to team for users if necessary |
| members       | User details (username,password,email)                                          |

Members should be written in this order

```
username|password|email
```

You can write in csv multiple users for each team like is shown in CSV

+ Execute ```add_team_and_user.py``` python script

```bash
python3 add_team_and_user.py
```

+ Output should looks like that

```bash
Team 'C1berSquad' created with ID 15
User created successfully: Username: al1ce_smith, Password: al1ce_pass123, Email: al1ce.smith@example.com
User with ID 28 added to team ID 15
User created successfully: Username: b0b_jones, Password: b0b_pass456, Email: b0b.jones@example.com
User with ID 29 added to team ID 15
```

+ Check your admin panel on CTFd platform.
