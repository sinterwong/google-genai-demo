import threading
import uuid
import logging
from google import genai
from google.genai import types
from typing import List, Optional, Dict

manager_logger = logging.getLogger(__name__ + ".ConversationManager")


class ConversationHistory:
    def __init__(self):
        self._history: List[types.Content] = []

    def add_user_message(self, text: str):
        self._history.append(
            types.Content(role="user", parts=[types.Part.from_text(text=text)])
        )

    def add_model_response(self, text: str):
        if not self._history:
            raise ValueError(
                "Cannot add model response before any user message.")
        if self._history[-1].role == "model":
            print(
                "Warning: Adding model response immediately after another model response.")
        self._history.append(
            types.Content(role="model", parts=[
                types.Part.from_text(text=text)
            ])
        )

    @property
    def contents(self) -> List[types.Content]:
        """
        获取当前完整的对话历史记录列表，供 API 调用。
        """
        return self._history

    def send_message(
        self,
        model_name: str,
        client: genai.Client,
        message: str,
        generation_config: Optional[types.GenerateContentConfig] = None,
    ) -> types.GenerateContentResponse:
        self.add_user_message(message)
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=self.contents,
                config=generation_config,
            )
            if hasattr(response, 'text'):
                model_response_text = response.text
            elif response.candidates and response.candidates[0].content.parts:
                model_response_text = response.candidates[0].content.parts[0].text
            else:
                print("Warning: Received response with no usable text content.")
                block_reason = getattr(
                    getattr(response, 'prompt_feedback', None), 'block_reason', None)
                if block_reason:
                    model_response_text = f"[Blocked by Safety Setting: {
                        block_reason}]"
                else:
                    model_response_text = "[No response text found]"

            self.add_model_response(model_response_text)
            return response
        except Exception as e:
            print(f"Error during API call: {e}")
            self._history.pop()  # rollback
            raise

    def clear(self):
        self._history = []

    def __len__(self) -> int:
        return len(self._history)

    def __bool__(self) -> bool:
        return True


class SingletonBase(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class ConversationManager(metaclass=SingletonBase):
    def __init__(self):
        if hasattr(self, '_initialized_flag') and self._initialized_flag:
            return
        self.conversations: Dict[str, ConversationHistory] = {}
        self._lock = threading.Lock()
        manager_logger.info(
            f"ConversationManager Singleton initialized (id: {id(self)}).")
        self._initialized_flag = True

    def create_conversation(self) -> str:
        conversation_id = str(uuid.uuid4())
        with self._lock:
            self.conversations[conversation_id] = ConversationHistory()
        manager_logger.info(f"Created conversation: {conversation_id}")
        return conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[ConversationHistory]:
        with self._lock:
            conversation = self.conversations.get(conversation_id)
        if conversation:
            manager_logger.debug(f"Retrieved conversation: {conversation_id}")
        else:
            manager_logger.warning(
                f"Attempted to retrieve non-existent conversation: {conversation_id}")
        return conversation

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._lock:
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]
                manager_logger.info(f"Deleted conversation: {conversation_id}")
                return True
        manager_logger.warning(
            f"Attempted to delete non-existent conversation: {conversation_id}")
        return False

    def send_message_to_conversation(
        self,
        conversation_id: str,
        model_name: str,
        client: genai.Client,
        message: str,
        generation_config: Optional[types.GenerateContentConfig] = None,
    ) -> Optional[str]:
        manager_logger.info(
            f"Attempting to send message to conversation '{conversation_id}' using model '{model_name}'.")

        conversation = self.get_conversation(conversation_id)
        if not conversation:
            manager_logger.error(
                f"Conversation with ID '{conversation_id}' not found for sending message.")
            raise ValueError(
                f"Conversation with ID '{conversation_id}' not found.")

        try:
            response = conversation.send_message(
                model_name=model_name,
                client=client,
                message=message,
                generation_config=generation_config,
            )
            manager_logger.info(
                f"Successfully sent message and received response for conversation '{conversation_id}'.")
            return response.text
        except ValueError as ve:
            manager_logger.error(
                f"ValueError during message sending for conversation '{conversation_id}': {ve}", exc_info=False)
            raise
        except Exception as e:
            manager_logger.error(
                f"An unexpected error occurred while sending message to conversation '{
                    conversation_id}': {e}",
                exc_info=True
            )
            raise
