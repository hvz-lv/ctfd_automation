import os
import sys
import subprocess
from csv import DictReader, DictWriter
import requests
from requests.auth import HTTPBasicAuth
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

network = list()
s = requests.Session()

def get_server_uuid(opnsense_ip, api_user, api_password):
    r = s.get(
        f"https://{opnsense_ip}/api/wireguard/server/get",
        auth=HTTPBasicAuth(f"{api_user}", f"{api_password}"),
        verify=False
    )

    if r.status_code == 200:
        output = r.json()
        return str(''.join([key for key in output["server"]["servers"]["server"].keys()]))
    else:
        sys.exit(0)

def create_wireguard_peer(opnsense_ip, api_user, api_password, username, pubkey, tunneladdress, server_uuid, endpoit_ip, endpoint_port, psk):
    r = s.post(
        f"https://{opnsense_ip}/api/wireguard/client/addClient",
        auth=HTTPBasicAuth(f"{api_user}", f"{api_password}"),
        json={
            "client": {
                "enabled": "1",
                "name": f"{username}",
                "pubkey": f"{pubkey}",
                "tunneladdress": f"{tunneladdress}",
                "keepalive": "5",
                "servers": f"{server_uuid}",
                "serveraddress": f"{endpoit_ip}",
                "serverport": f"{endpoint_port}",
                "psk": f"{psk}",
            }
        },
        headers={"Content-Type": "application/json"},
        verify=False
    )

    if r.status_code != 200:
        print(False)

def firewall_reboot(opnsense_ip, api_user, api_password):
    r = s.post(
        f"https://{opnsense_ip}/api/core/system/reboot",
        auth=HTTPBasicAuth(f"{api_user}", f"{api_password}"),
        verify=False
    )

try:
    with open("apikey.txt", 'r') as tempfile:
        df = list(tempfile)
except:
    sys.exit(0)

for line in df:
    if "key" in line:
        api_user = line.split("\n")[0].split("key=")[1]
    elif "secret" in line:
        api_password = line.split("\n")[0].split("secret=")[1]

try:
    with open("wireguard.conf", 'r') as tempfile:
        df = list(tempfile)
except:
    sys.exit(0)

for line in df:
    if "Address" in line:
        tmp3 = []
        tmp = line.split("\n")[0].split("Address = ")[1]
        if "," in tmp:
            tmp = tmp.split(",")
            tmp1 = tmp[0].split("/32")[0].split(".")
            network_inc = int(tmp1[-1])
            for y in range(len(tmp1) - 1):
                tmp3.append(tmp1[y])
            network.append(".".join(tmp3) + ".")
            if "::" in tmp[1]:
                tmp2 = tmp[1].split("/128")[0].split("::")
                network.append(tmp2[0] + "::")
    elif "DNS" in line:
        tmp = line.split("\n")[0].split("DNS = ")[1]
        if "," in tmp:
            tmp = tmp.split(",")[0]
        opnsense_ip = tmp
    elif "Endpoint" in line:
        tmp = line.split("\n")[0].split("Endpoint = ")[1].split(":")
        endpoit_ip = tmp[0]
        endpoint_port = int(tmp[1])

server_uuid = get_server_uuid(opnsense_ip, api_user, api_password)
users = DictReader(open("users.csv"))
os.makedirs("./wireguard", exist_ok=True)

# Prepare for CSV export
export_data = []

for user in users:
    email = user["email"]
    username = email.split('@')[0]  # Extract username from email
    result = subprocess.run(["wg", "genkey"], stdout=subprocess.PIPE, text=True)
    privkey = result.stdout.strip()
    result = subprocess.run(["wg", "pubkey"], input=privkey, stdout=subprocess.PIPE, text=True)
    pubkey = result.stdout.strip()
    result = subprocess.run(["wg", "genpsk"], stdout=subprocess.PIPE, text=True)
    psk = result.stdout.strip()
    network_inc += 1
    tunneladdress = ""

    for x in range(len(network)):
        if x != 0:
            tunneladdress += f",{network[x]}{network_inc}/128"
        else:
            tunneladdress += f"{network[x]}{network_inc}/32"

    create_wireguard_peer(opnsense_ip, api_user, api_password, username, pubkey, tunneladdress, server_uuid, endpoit_ip, endpoint_port, psk)

    config_path = f"./wireguard/wg-ctfd-{username}.conf"
    with open(config_path, 'w') as tempfile:
        for line in df:
            if "PrivateKey" in line:
                tempfile.write(f"PrivateKey = {privkey}\n")
            elif "Address" in line:
                tempfile.write(f"Address = {tunneladdress}\n")
            elif "PresharedKey" in line:
                tempfile.write(f"PresharedKey = {psk}\n")
            else:
                tempfile.write(line)

    password = user["password"]
    # Append to export data
    export_data.append({"username": username, "email": email,"password": password, "config_path": config_path})

# Export to CSV
with open("mailmerge_database.csv", 'w', newline='') as csvfile:
    fieldnames = ["username", "email", "password", "config_path"]
    writer = DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(export_data)

firewall_reboot(opnsense_ip, api_user, api_password)
