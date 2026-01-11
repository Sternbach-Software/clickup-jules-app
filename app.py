import os
import json
import requests
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_config():
    return {
        'CLICKUP_API_KEY': os.environ.get('CLICKUP_API_KEY'),
        'JULES_API_KEY': os.environ.get('JULES_API_KEY')
    }

def get_custom_field_value(task_data, field_name):
    """
    Helper to extract value from a custom field by name.
    """
    custom_fields = task_data.get('custom_fields', [])
    for field in custom_fields:
        if field.get('name', '').lower() == field_name.lower():
            # Value might be directly in 'value' or nested depending on type
            # For text fields it's usually just 'value'
            return field.get('value')
    return None

def process_new_task(task_id):
    """
    Fetches task details from ClickUp and creates a session in Jules.
    """
    config = get_config()
    CLICKUP_API_KEY = config['CLICKUP_API_KEY']
    JULES_API_KEY = config['JULES_API_KEY']

    if not CLICKUP_API_KEY or not JULES_API_KEY:
        print("Error: CLICKUP_API_KEY or JULES_API_KEY not set.")
        return

    print(f"Processing task {task_id}...")

    # 1. Fetch Task Details from ClickUp
    clickup_url = f"https://api.clickup.com/api/v2/task/{task_id}"
    headers = {
        "Authorization": CLICKUP_API_KEY
    }

    try:
        response = requests.get(clickup_url, headers=headers)
        response.raise_for_status()
        task_data = response.json()
    except Exception as e:
        print(f"Error fetching task from ClickUp: {e}")
        return

    # 2. Extract Data
    task_name = task_data.get('name')
    task_description = task_data.get('description', '')

    # Try to find Repository in custom fields
    repo_url = get_custom_field_value(task_data, 'Repository') or get_custom_field_value(task_data, 'Repo')

    # 3. Construct Jules Payload
    jules_payload = {
        "title": task_name,
        "prompt": task_description,
    }

    if repo_url:
        # Assuming repo_url is like "https://github.com/owner/repo" or just "owner/repo"
        # Jules example showed "sources/github/owner/repo" for source
        # But let's stick to what we have or try to parse if needed.
        # The prompt example: "source": "sources/github/bobalover/boba"

        # Simple heuristic: if it looks like a github url, strip it
        if "github.com/" in repo_url:
            repo_path = repo_url.split("github.com/")[-1]
            if repo_path.endswith('.git'):
                repo_path = repo_path[:-4]
            source = f"sources/github/{repo_path}"
        elif "/" in repo_url: # Assume owner/repo format
             source = f"sources/github/{repo_url}"
        else:
             source = repo_url # Just pass it as is if unsure

        jules_payload["sourceContext"] = {
            "source": source,
            "githubRepoContext": {
                "startingBranch": "main" # Defaulting to main
            }
        }

    # 4. Create Session in Jules
    jules_url = "https://jules.googleapis.com/v1alpha/sessions"
    jules_headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": JULES_API_KEY
    }

    try:
        jules_response = requests.post(jules_url, headers=jules_headers, json=jules_payload)
        jules_response.raise_for_status()
        print(f"Successfully created Jules session for task {task_id}. Response: {jules_response.json()}")
    except Exception as e:
        print(f"Error creating Jules session: {e}")
        if 'jules_response' in locals():
            print(f"Jules Response Content: {jules_response.text}")


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    if not data:
        return jsonify({"message": "No data received"}), 400

    event = data.get('event')

    if event == 'taskCreated':
        task_id = data.get('task_id')
        if task_id:
            # Process in a separate thread to return 200 immediately
            thread = threading.Thread(target=process_new_task, args=(task_id,))
            thread.start()

    return jsonify({"message": "Webhook received"}), 200

if __name__ == '__main__':
    app.run(port=int(os.environ.get('PORT', 5000)))
