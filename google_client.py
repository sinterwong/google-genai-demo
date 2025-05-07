from google import genai
import os
from google.genai import types
from config import RAG_ASSISTANT_CONFIG

GOOGLE_PROJECT_NAME = os.getenv("GOOGLE_PROJECT_NAME")
GOOGLE_REGION = os.getenv("GOOGLE_REGION")

print(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

client = genai.Client(
    vertexai=True,
    project=GOOGLE_PROJECT_NAME,
    location=GOOGLE_REGION,
)


# class Rensponse():
#     text = "hello world"

#     def __init__(self):
#         pass


# class Model:
#     def __init__(self):
#         pass

#     def generate_content(self, model: str, contents: list, config):
#         return Rensponse()


# class Client:
#     models = Model()

#     def __init__(self):
#         pass


# client = Client()


def test():
    model_name = "gemini-2.5-flash-preview-04-17"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""请介绍一下你自己。""")
            ]
        ),
    ]
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=RAG_ASSISTANT_CONFIG
    )

    print(response)
    print(response.text)


if __name__ == "__main__":
    test()
