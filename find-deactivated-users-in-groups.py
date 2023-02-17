import requests
import csv
import time
import threading

# Set the Okta API token and base URL
api_token = 'yourOktaAPIToken'
base_url = 'https://YOURDOMAIN.okta.com/api/v1'

# Set the endpoint for getting all groups
groups_endpoint = base_url + '/groups'

# Set the endpoint for getting users in a group
group_users_endpoint = base_url + '/groups/{}/users'

# Set the headers for the API request
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'SSWS {api_token}'
}

# Set the CSV filename
csv_filename = 'deprovisioned_users_in_groups.csv'

# Set the API rate limit retry variables
max_retries = 6
retry_wait_time = 30

# Create an empty list to store the deprovisioned users
deprovisioned_users = []

# Set the number of concurrent threads to run
num_threads = 5

# Create a threading lock to synchronize access to the deprovisioned_users list
lock = threading.Lock()

# Define a function to get the users in a group
def get_group_users(group_id, group_name):
    global deprovisioned_users

    # Send the API request to get users in the current group
    print(f"Getting users in group: {group_name}...")
    response = requests.get(group_users_endpoint.format(group_id), headers=headers)

    # Check for API rate limit errors and retry up to max_retries times
    retry_count = 0
    while response.status_code == 429 and retry_count < max_retries:
        print(f"Rate limit exceeded. Retrying in {retry_wait_time} seconds...")
        time.sleep(retry_wait_time)
        response = requests.get(group_users_endpoint.format(group_id), headers=headers)
        retry_count += 1

    # If the response is successful, get the data from the JSON response
    if response.status_code == 200:
        data = response.json()

        # Loop through all the users in the current group
        for user in data:
            username = user['profile']['login']
            status = user['status']

            # If the user is deprovisioned, add it to the list
            if status == 'DEPROVISIONED':
                with lock:
                    deprovisioned_users.append([username, group_id, group_name])

# Send the API request to get all groups
print("Getting all groups from Okta...")
response = requests.get(groups_endpoint, headers=headers)

# Check for API rate limit errors and retry up to max_retries times
retry_count = 0
while response.status_code == 429 and retry_count < max_retries:
    print(f"Rate limit exceeded. Retrying in {retry_wait_time} seconds...")
    time.sleep(retry_wait_time)
    response = requests.get(groups_endpoint, headers=headers)
    retry_count += 1

# If the response is successful, get the data from the JSON response
if response.status_code == 200:
    data = response.json()

    # Loop through all the groups
    for group in data:
        group_id = group['id']
        group_name = group['profile']['name']

        # Create a thread to get the users in the current group
        t = threading.Thread(target=get_group_users, args=(group_id, group_name))
        t.start()

        # Wait for all threads to finish before proceeding to the next group
        while threading.active_count() >= num_threads:
            time.sleep(0.1)

# Write the deprovisioned users to a CSV file
print(f"Writing {len(deprovisioned_users)} deprovisioned users to CSV file...")
with open(csv_filename, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['Username', 'Group ID', 'Group Name'])
    writer.writerows(deprovisioned_users)

print("Export of deprovisioned users still assigned to Okta groups is completed!")