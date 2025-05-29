from typing import Any, Dict
from flask import Flask, abort, request, jsonify
import os
from conversation import manager_logger, ConversationManager
from google.genai import types
from google_client import client
from config import RAG_ASSISTANT_CONFIG, GOOGLE_SEARCH_CONFIG, create_config_from_json_data

from dotenv import load_dotenv

load_dotenv()

print(f"--- SCRIPT TOP LEVEL ---")
print(f"WERKZEUG_RUN_MAIN: {os.environ.get('WERKZEUG_RUN_MAIN')}")
print(f"FLASK_DEBUG env: {os.environ.get('FLASK_DEBUG')}")
print(f"FLASK_ENV env: {os.environ.get('FLASK_ENV')}")

app = Flask(__name__)


# TODO: consider persistence in the future
conversation_manager = ConversationManager()
print(f"Global conversation_manager created, id: {id(conversation_manager)}")


DEFAULT_CHAT_MODEL_NAME = os.environ.get("DEFAULT_CHAT_MODEL_NAME")


def serialize_content(content: types.Content) -> Dict[str, Any]:
    part_text = ""
    if content.parts:
        part_text = " ".join(
            [part.text for part in content.parts if hasattr(part, 'text')])
    return {"role": content.role, "text": part_text}


@app.route("/conversations", methods=["POST"])
def create_conversation_api():
    """
    Creates a new conversation session.
    Returns:
        JSON: {"conversation_id": "new_uuid"}
    """
    conversation_id = conversation_manager.create_conversation()
    return jsonify({"conversation_id": conversation_id}), 201


@app.route("/conversations/<string:conversation_id>", methods=["GET"])
def get_conversation_api(conversation_id: str):
    """
    Retrieves the history of a specific conversation.
    Args:
        conversation_id (str): The ID of the conversation.
    Returns:
        JSON: {"conversation_id": "id", "history": [{"role": "user/model", "text": "..."}]}
              or 404 if not found.
    """
    conversation = conversation_manager.get_conversation(conversation_id)
    if not conversation:
        abort(
            404, description=f"Conversation with ID '{conversation_id}' not found.")

    serialized_history = [serialize_content(
        content) for content in conversation.contents]
    return jsonify({
        "conversation_id": conversation_id,
        "history": serialized_history,
        "length": len(conversation)
    })


@app.route("/conversations/<string:conversation_id>", methods=["DELETE"])
def delete_conversation_api(conversation_id: str):
    """
    Deletes a specific conversation.
    Args:
        conversation_id (str): The ID of the conversation.
    Returns:
        JSON: {"message": "Conversation deleted"} or 404 if not found.
    """
    if conversation_manager.delete_conversation(conversation_id):
        return jsonify({"message": f"Conversation '{conversation_id}' deleted successfully."}), 200
    else:
        abort(
            404, description=f"Conversation with ID '{conversation_id}' not found for deletion.")


@app.route("/conversations/<string:conversation_id>/messages", methods=["POST"])
def send_message_api(conversation_id: str):
    """
    Sends a message to a specific conversation and gets a response from the model.
    Args:
        conversation_id (str): The ID of the conversation.
    JSON Body:
        {
            "message": ,
            "model_name":,
            "generation_config": { ... optional override ... },
        }
    Returns:
        JSON: {"response": "Model's answer"} or 404/400/500 errors.
    """
    conversation = conversation_manager.get_conversation(conversation_id)
    if not conversation:
        abort(
            404, description=f"Conversation with ID '{conversation_id}' not found.")

    data = request.get_json()
    if not data or "message" not in data:
        abort(400, description="Missing 'message' in request body.")

    user_message = data["message"]

    # allow overriding model and generation config from request
    model_name_override = data.get("model_name", DEFAULT_CHAT_MODEL_NAME)

    gen_config_override_dict = data.get("generation_config")
    current_gen_config = GOOGLE_SEARCH_CONFIG
    if gen_config_override_dict and isinstance(gen_config_override_dict, dict):
        current_gen_config = create_config_from_json_data(
            gen_config_override_dict)

    try:
        model_response = conversation_manager.send_message_to_conversation(
            conversation_id=conversation_id,
            model_name=model_name_override,
            client=client,
            message=user_message,
            generation_config=current_gen_config,
        )
        if model_response is None and not conversation_manager.get_conversation(conversation_id):
            abort(
                404, description=f"Conversation with ID '{conversation_id}' not found after attempting to send message.")

        return jsonify({"response": model_response})
    except ValueError as ve:
        manager_logger.error(
            f"ValueError in send_message_api for {conversation_id}: {ve}")
        abort(400, description=str(ve))
    except Exception as e:
        manager_logger.error(
            f"Unexpected error in send_message_api for {conversation_id}: {e}", exc_info=True)
        abort(500, description="An internal server error occurred.")


@app.errorhandler(400)
def bad_request(error):
    return jsonify(error=str(error.description)), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify(error=str(error.description)), 404


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify(error=str(error.description)), 500


if __name__ == '__main__':
    print(f"--- RUNNING __main__ ---")
    print(f"Flask app debug actual: {app.debug}")
    print(
        f"Flask app use_reloader actual (config): {app.config.get('USE_RELOADER')}")
    app.run(host='0.0.0.0', port=9797, debug=False, use_reloader=False)
