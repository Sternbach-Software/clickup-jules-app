# ClickUp to Jules Integration

This is a Flask app that listens for ClickUp webhooks (specifically `taskCreated` events) and creates a corresponding session (task) in Google Jules.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   You need to set the following environment variables:
   - `CLICKUP_API_KEY`: Your ClickUp API Key (Personal Access Token).
   - `JULES_API_KEY`: Your Google Jules API Key.

   Example:
   ```bash
   export CLICKUP_API_KEY="pk_..."
   export JULES_API_KEY="AIza..."
   ```

3. **Run the App**
   ```bash
   python app.py
   ```
   The app will run on port 5000 by default (or the port specified in `PORT` env var).

## ClickUp Configuration

1. Go to your ClickUp List or Space.
2. Add a Webhook.
3. Set the Endpoint URL to your deployed app's URL (e.g., `https://your-app.com/webhook`).
4. Select `Task Created` event.
5. (Optional) Add a Custom Field named `Repository` or `Repo` to your ClickUp tasks. If present, the app will use this value to set the `sourceContext` for Jules (e.g., `https://github.com/owner/repo`).

## How it Works

1. When a task is created in ClickUp, a webhook is sent to `/webhook`.
2. The app extracts the `task_id` and acknowledges the webhook immediately.
3. In the background, it fetches the full task details from ClickUp API.
4. It extracts the Task Name (Title) and Description (Prompt).
5. It looks for a `Repository` custom field.
6. It sends a request to the Jules API to create a new session.

## Testing

Run the integration tests:
```bash
python3 test_integration.py
```
