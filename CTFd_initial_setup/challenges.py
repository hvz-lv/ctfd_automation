import requests
import csv
import os
import sys
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define API base URL
api_url = "https://127.0.0.1/api/v1"

# CSV file path (Update this with your actual file path)
csv_file_path = "/home/ubuntu/ctfd_automation/csv_files/challenges.csv"

# Define API endpoints
file_upload_url = f"{api_url}/files"
hint_url = f"{api_url}/hints"
flag_url = f"{api_url}/flags"
challenges_url = f"{api_url}/challenges"

# Function to create challenge
def create_challenge(challenge_data, headers):
    response = requests.post(challenges_url, headers=headers, json=challenge_data, verify=False)
    if response.status_code == 200:
        challenge_id = response.json()["data"]["id"]
        print(f"Challenge '{challenge_data['name']}' created successfully with ID {challenge_id}.")
        return challenge_id
    else:
        print(f"Unexpected response status: {response.status_code}")
        print("Response text:", response.text)
        return None

# Function to update challenge
def update_challenge(challenge_id, update_data, headers):
    update_url = f"{challenges_url}/{challenge_id}"
    response = requests.patch(update_url, headers=headers, json=update_data, verify=False)
    if response.status_code == 200:
        print(f"Challenge '{challenge_id}' updated successfully.")
    else:
        print(f"Failed to update challenge '{challenge_id}': {response.status_code}")
        print("Response text:", response.text)

# Function to upload a file
def upload_file(file_path, challenge_id, headers):
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        return None
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'challenge_id': challenge_id, 'type': 'challenge'}
        response = requests.post(file_upload_url, headers=headers, files=files, data=data, verify=False)
        if response.status_code == 200:
            file_data = response.json()["data"][0]
            print(f"File '{file_path}' uploaded and associated with challenge ID {challenge_id}.")
            return file_data
        else:
            print(f"Failed to upload file '{file_path}': {response.status_code} - {response.text}")
            return None

# Function to add a flag
def add_flag(challenge_id, content, flag_type, headers):
    flag_data = {"challenge_id": challenge_id, "content": content, "type": flag_type}
    response = requests.post(flag_url, headers=headers, json=flag_data, verify=False)
    if response.status_code == 200:
        print(f"Successfully added flag to challenge ID {challenge_id}")
    else:
        print(f"Failed to add flag: {response.status_code} - {response.text}")

# Function to add a hint
def add_hint(challenge_id, content, headers, cost=0, prerequisites=None):
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

def update_hint(hint_id, prerequisites, headers):
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

def main(api_token):
    api_token = api_token.strip()
    headers = {"Authorization": f"Bearer {api_token}"}
    hint_ids, ch_dict = {}, {}
    

    with open(csv_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            challenge_type = row.get("Type", "standard")
            challenge_data = {
                "name": row["Name"],
                "category": row["Category"],
                "description": row["Description"],
                "max_attempts": int(row["Max Attempts"]),
                "state": row["State"],
                "type": challenge_type,
                "connection_info": row.get("Connection_Info", ""),
                "value": int(row["Value"])
            }

            # Handle firstblood and dynamic challenges
            if challenge_type == "firstblood":
                first_blood_bonus = list(map(int, row["First_Blood_Bonus"].split("|")))
                challenge_data.update({
                    "first_blood_bonus[0]": first_blood_bonus[0],
                    "first_blood_bonus[1]": first_blood_bonus[1],
                    "first_blood_bonus[2]": first_blood_bonus[2]
                })
            elif challenge_type == "dynamic":
                challenge_data["initial"] = int(row["Initial"])
                challenge_data["decay"] = int(row["Decay"])
                challenge_data["minimum"] = int(row["Minimum"])

            hints = row["Hints"].split("|")
            hints_cost = list(map(int, row["Hints_Cost"].split("|")))
            challenge_prerequisites = list(row.get("Challenge_Prerequisites", "").split("|"))

            challenge_id = create_challenge(challenge_data, headers)
            if challenge_id:
                file_path = row.get("File_Path")
                if file_path:
                    upload_file(file_path, challenge_id, headers)

                flag_content = row.get("Flag")
                flag_type = row.get("Flag_Type", "static")
                if flag_content:
                    add_flag(challenge_id, flag_content, flag_type, headers)

                hint_ids[challenge_id] = []
                for hint_content, hint_cost in zip(hints, hints_cost):
                    hint_id = add_hint(challenge_id, hint_content, headers, hint_cost)
                    if hint_id:
                        hint_ids[challenge_id].append(hint_id)

                for index, hint_id in enumerate(hint_ids[challenge_id]):
                    prerequisites = [hid for hid in hint_ids[challenge_id][:index]]
                    update_hint(hint_id, prerequisites, headers)

                ch_dict[challenge_id] = [challenge_data["name"], challenge_prerequisites]
                time.sleep(0.5)

    # Resolve challenge prerequisites
    for key in ch_dict.keys():
        if ch_dict[key][1][0] != "":
            for x in range(len(ch_dict[key][1])):
                for k, value in ch_dict.items():
                    if value[0] == ch_dict[key][1][x]:
                        ch_dict[key][1][x] = k

    for key in ch_dict.keys():
        if ch_dict[key][1][0] != "":
            update_challenge(key, {"requirements": {"prerequisites": ch_dict[key][1]}}, headers)

if __name__ == "__main__":
    api_token = str(sys.argv[1])
    main(api_token)