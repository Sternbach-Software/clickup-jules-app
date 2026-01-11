import unittest
from unittest.mock import patch, MagicMock
import json
import os
import time
from app import app, process_new_task

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['CLICKUP_API_KEY'] = 'test_clickup_key'
        os.environ['JULES_API_KEY'] = 'test_jules_key'

    @patch('app.process_new_task')
    def test_webhook_triggers_processing(self, mock_process):
        payload = {
            "event": "taskCreated",
            "task_id": "test_task_123"
        }
        response = self.app.post('/webhook',
                                 data=json.dumps(payload),
                                 content_type='application/json')

        self.assertEqual(response.status_code, 200)
        # Allow some time for the thread to start (though here we mocked the function called in thread,
        # but the thread target is the function wrapper.
        # Wait, app.py calls process_new_task in a thread.
        # Since we mocked process_new_task, we just need to ensure it was called.
        # However, threading might make the call happen after the test checks.
        # But `process_new_task` is imported in app.py.
        # `threading.Thread(target=process_new_task...` uses the function object.
        # If we patch `app.process_new_task`, we are patching the name in `app` module.
        # So it should work.

        # We need to wait a bit because it's in a thread
        time.sleep(0.1)
        mock_process.assert_called_with('test_task_123')

    @patch('app.requests.post')
    @patch('app.requests.get')
    def test_process_new_task_logic(self, mock_get, mock_post):
        # Mock ClickUp response
        mock_clickup_response = MagicMock()
        mock_clickup_response.status_code = 200
        mock_clickup_response.json.return_value = {
            "id": "test_task_123",
            "name": "Implement Login",
            "description": "Create a login page using Flask.",
            "custom_fields": [
                {
                    "name": "Repository",
                    "value": "https://github.com/myuser/myrepo"
                }
            ]
        }
        mock_get.return_value = mock_clickup_response

        # Mock Jules response
        mock_jules_response = MagicMock()
        mock_jules_response.status_code = 200
        mock_jules_response.json.return_value = {"name": "sessions/123"}
        mock_post.return_value = mock_jules_response

        # Run the function directly (bypass threading)
        process_new_task("test_task_123")

        # Verify ClickUp GET
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertIn("api.clickup.com/api/v2/task/test_task_123", args[0])
        self.assertEqual(kwargs['headers']['Authorization'], 'test_clickup_key')

        # Verify Jules POST
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://jules.googleapis.com/v1alpha/sessions")
        self.assertEqual(kwargs['headers']['X-Goog-Api-Key'], 'test_jules_key')

        expected_payload = {
            "title": "Implement Login",
            "prompt": "Create a login page using Flask.",
            "sourceContext": {
                "source": "sources/github/myuser/myrepo",
                "githubRepoContext": {
                    "startingBranch": "main"
                }
            }
        }
        self.assertEqual(kwargs['json'], expected_payload)

if __name__ == '__main__':
    unittest.main()
