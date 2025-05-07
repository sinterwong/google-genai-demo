import unittest
import requests
import uuid

BASE_URL = "http://localhost:9797"


class TestConversationAPI(unittest.TestCase):

    def setUp(self):
        self.created_conversation_ids = []

    def tearDown(self):
        for conv_id in self.created_conversation_ids:
            try:
                requests.delete(
                    f"{BASE_URL}/conversations/{conv_id}", timeout=5)
            except requests.RequestException:
                pass

    def _create_conversation(self):
        response = requests.post(f"{BASE_URL}/conversations", timeout=5)
        self.assertEqual(response.status_code, 201,
                         f"Failed to create conversation: {response.text}")
        data = response.json()
        self.assertIn("conversation_id", data)
        conv_id = data["conversation_id"]
        # add to list for cleanup
        self.created_conversation_ids.append(conv_id)
        return conv_id

    def test_01_create_conversation(self):
        """Test creating a new conversation."""
        print("\nRunning test_01_create_conversation...")
        response = requests.post(f"{BASE_URL}/conversations", timeout=5)
        self.assertEqual(response.status_code, 201,
                         f"Response: {response.text}")
        data = response.json()
        self.assertIn("conversation_id", data)
        self.assertTrue(isinstance(data["conversation_id"], str))
        # add to created_conversation_ids so it can be cleaned up even if other tests fail
        if "conversation_id" in data:
            self.created_conversation_ids.append(data["conversation_id"])
        print(f"Created conversation: {data.get('conversation_id')}")

    def test_02_get_conversation_empty_history(self):
        """Test getting an existing conversation with empty history."""
        print("\nRunning test_02_get_conversation_empty_history...")
        conversation_id = self._create_conversation()
        print(f"Getting conversation: {conversation_id}")

        response = requests.get(
            f"{BASE_URL}/conversations/{conversation_id}", timeout=60)
        self.assertEqual(response.status_code, 200,
                         f"Response: {response.text}")
        data = response.json()
        self.assertEqual(data["conversation_id"], conversation_id)
        self.assertIn("history", data)
        self.assertEqual(data["history"], [])
        self.assertIn("length", data)
        self.assertEqual(data["length"], 0)

    def test_03_send_message_and_get_history(self):
        """Test sending a message and then retrieving the conversation history."""
        print("\nRunning test_03_send_message_and_get_history...")
        conversation_id = self._create_conversation()
        print(f"Conversation ID for send/get test: {conversation_id}")

        message_payload = {
            "message": "Hello, model!",
        }
        print(
            f"Sending message to {conversation_id}: {message_payload['message']}")
        send_response = requests.post(
            f"{BASE_URL}/conversations/{conversation_id}/messages",
            json=message_payload,
            timeout=300
        )
        self.assertEqual(send_response.status_code, 200,
                         f"Send message failed: {send_response.text}")
        send_data = send_response.json()
        self.assertIn("response", send_data)
        self.assertTrue(isinstance(send_data["response"], str))
        model_response_text = send_data["response"]
        print(f"Model response: {model_response_text}")

        # get conversation history
        print(
            f"Getting history for {conversation_id} after sending message...")
        get_response = requests.get(
            f"{BASE_URL}/conversations/{conversation_id}", timeout=5)
        self.assertEqual(get_response.status_code, 200,
                         f"Get history failed: {get_response.text}")
        get_data = get_response.json()

        self.assertEqual(get_data["conversation_id"], conversation_id)
        self.assertIn("history", get_data)
        # user message + Model response
        self.assertEqual(len(get_data["history"]), 2)
        self.assertEqual(get_data["length"], 2)

        # check user message
        self.assertEqual(get_data["history"][0]["role"], "user")
        self.assertEqual(get_data["history"][0]
                         ["text"], message_payload["message"])

        # check model response
        self.assertEqual(get_data["history"][1]["role"], "model")
        self.assertEqual(get_data["history"][1]["text"], model_response_text)

    def test_04_delete_conversation(self):
        """Test deleting an existing conversation."""
        print("\nRunning test_04_delete_conversation...")
        conversation_id = self._create_conversation()
        print(f"Deleting conversation: {conversation_id}")

        delete_response = requests.delete(
            f"{BASE_URL}/conversations/{conversation_id}", timeout=5)
        self.assertEqual(delete_response.status_code, 200,
                         f"Delete failed: {delete_response.text}")
        delete_data = delete_response.json()
        self.assertIn("message", delete_data)
        self.assertIn(conversation_id, delete_data["message"])

        # verify it's gone
        print(f"Verifying deletion of {conversation_id}...")
        get_response = requests.get(
            f"{BASE_URL}/conversations/{conversation_id}", timeout=5)
        self.assertEqual(get_response.status_code, 404,
                         "Conversation was not actually deleted.")
        # remove from list as it's successfully deleted by the test itself
        if conversation_id in self.created_conversation_ids:
            self.created_conversation_ids.remove(conversation_id)

    def test_05_get_non_existent_conversation(self):
        """Test getting a conversation that does not exist."""
        print("\nRunning test_05_get_non_existent_conversation...")
        non_existent_id = str(uuid.uuid4())
        print(f"Attempting to get non-existent ID: {non_existent_id}")
        response = requests.get(
            f"{BASE_URL}/conversations/{non_existent_id}", timeout=5)
        self.assertEqual(response.status_code, 404)

    def test_06_delete_non_existent_conversation(self):
        """Test deleting a conversation that does not exist."""
        print("\nRunning test_06_delete_non_existent_conversation...")
        non_existent_id = str(uuid.uuid4())
        print(f"Attempting to delete non-existent ID: {non_existent_id}")
        response = requests.delete(
            f"{BASE_URL}/conversations/{non_existent_id}", timeout=5)
        self.assertEqual(response.status_code, 404)

    def test_07_send_message_to_non_existent_conversation(self):
        """Test sending a message to a conversation that does not exist."""
        print("\nRunning test_07_send_message_to_non_existent_conversation...")
        non_existent_id = str(uuid.uuid4())
        message_payload = {"message": "Hello?"}
        print(
            f"Attempting to send message to non-existent ID: {non_existent_id}")
        response = requests.post(
            f"{BASE_URL}/conversations/{non_existent_id}/messages",
            json=message_payload,
            timeout=5
        )
        self.assertEqual(response.status_code, 404)

    def test_08_send_message_bad_request_missing_message(self):
        """Test sending a message with a missing 'message' field."""
        print("\nRunning test_08_send_message_bad_request_missing_message...")
        conversation_id = self._create_conversation()
        print(f"Sending bad request (missing message) to: {conversation_id}")

        bad_payload = {"model_name": "some_model"}  # Missing "message"
        response = requests.post(
            f"{BASE_URL}/conversations/{conversation_id}/messages",
            json=bad_payload,
            timeout=5
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("Missing 'message'", data["error"])

    def test_09_conversation_persistence_across_requests(self):
        """
        Tests if a conversation created in one request is available and updated by subsequent requests.
        This specifically tests the core issue you were facing.
        """
        print("\nRunning test_09_conversation_persistence_across_requests...")
        response_create = requests.post(f"{BASE_URL}/conversations", timeout=5)
        self.assertEqual(response_create.status_code, 201)
        conv_id = response_create.json()["conversation_id"]
        self.created_conversation_ids.append(conv_id)  # For cleanup
        print(f"Persistence Test: Created conversation {conv_id}")

        msg1_payload = {"message": "First message for persistence test."}
        response_msg1 = requests.post(
            f"{BASE_URL}/conversations/{conv_id}/messages", json=msg1_payload, timeout=30)
        self.assertEqual(response_msg1.status_code, 200,
                         f"Response: {response_msg1.text}")
        model_response1 = response_msg1.json()["response"]
        print(
            f"Persistence Test: Sent first message, got response: '{model_response1}'")

        response_get1 = requests.get(
            f"{BASE_URL}/conversations/{conv_id}", timeout=5)
        self.assertEqual(response_get1.status_code, 200)
        history1 = response_get1.json()["history"]
        self.assertEqual(len(history1), 2)
        self.assertEqual(history1[0]["text"], msg1_payload["message"])
        self.assertEqual(history1[1]["text"], model_response1)
        print(
            f"Persistence Test: History after 1st message has {len(history1)} items.")

        msg2_payload = {"message": "Second message, are you still there?"}
        response_msg2 = requests.post(
            f"{BASE_URL}/conversations/{conv_id}/messages", json=msg2_payload, timeout=30)
        self.assertEqual(response_msg2.status_code, 200,
                         f"Response: {response_msg2.text}")
        model_response2 = response_msg2.json()["response"]
        print(
            f"Persistence Test: Sent second message, got response: '{model_response2}'")

        response_get2 = requests.get(
            f"{BASE_URL}/conversations/{conv_id}", timeout=5)
        self.assertEqual(response_get2.status_code, 200)
        history2 = response_get2.json()["history"]
        self.assertEqual(len(
            history2), 4, f"Expected 4 messages, got {len(history2)}. History: {history2}")
        self.assertEqual(history2[0]["text"], msg1_payload["message"])
        self.assertEqual(history2[1]["text"], model_response1)
        self.assertEqual(history2[2]["text"], msg2_payload["message"])
        self.assertEqual(history2[3]["text"], model_response2)
        print(
            f"Persistence Test: History after 2nd message has {len(history2)} items. Test passed.")


if __name__ == '__main__':
    unittest.main()
