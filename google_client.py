import os

from google import genai
from google.cloud import bigquery
from google.genai import types

GOOGLE_PROJECT_NAME = os.getenv("GOOGLE_PROJECT_NAME")
GOOGLE_REGION = os.getenv("GOOGLE_REGION")

print(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

client = genai.Client(
    vertexai=True,
    project=GOOGLE_PROJECT_NAME,
    location=GOOGLE_REGION,
)

bigquery_client = bigquery.Client(project=GOOGLE_PROJECT_NAME)


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


def test_genai_client():
    from config import RAG_ASSISTANT_CONFIG
    model_name = "gemini-2.5-flash-preview-05-20"
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


def test_bigquery_client():
    query = """
        SELECT
            table_catalog, table_schema, table_name
        FROM
            `{}.INFORMATION_SCHEMA.TABLES`
        LIMIT 100
    """.format(GOOGLE_PROJECT_NAME)

    query_job = bigquery_client.query(query)

    print("Tables:")
    for row in query_job:
        print("\t{}.{}.{}".format(row[0], row[1], row[2]))


if __name__ == "__main__":
    # test_genai_client()
    test_bigquery_client()
