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
csv_file_path = "/csv_files/challenges.csv"  # Update this with your CSV file path
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