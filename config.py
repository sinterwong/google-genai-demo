import json
from google.genai import types


COMMON_SAFETY_SETTINGS = [
    types.SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold="OFF"
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="OFF"
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold="OFF"
    ),
    types.SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold="OFF"
    )
]

RAG_ASSISTANT_CONFIG = types.GenerateContentConfig(
    temperature=1,
    top_p=0.95,
    seed=0,
    max_output_tokens=8192,
    response_modalities=["TEXT"],
    safety_settings=COMMON_SAFETY_SETTINGS,
    tools=[
        types.Tool(
            retrieval=types.Retrieval(
                vertex_ai_search=types.VertexAISearch(
                    datastore="projects/gemini-with-rag/locations/global/collections/default_collection/dataStores/test-data-stores_1746354976431_init-database")
            )
        ),
    ],
    thinking_config=types.ThinkingConfig(
        thinking_budget=1024,
    ),
    system_instruction=[types.Part.from_text(
        text=f"""你是一个新闻总结助手，语气要像一个萝莉一样可爱可亲，时不时的会发emoji来辅助表达感情。""")],
)

GOOGLE_SEARCH_CONFIG = types.GenerateContentConfig(
    temperature=1,
    top_p=0.95,
    seed=0,
    max_output_tokens=8192,
    response_modalities=["TEXT"],
    safety_settings=COMMON_SAFETY_SETTINGS,
    tools=[
        types.Tool(google_search=types.GoogleSearch()),
    ],
    thinking_config=types.ThinkingConfig(
        thinking_budget=1024,
    ),
    system_instruction=[types.Part.from_text(
        text=f"""你是一个新闻总结助手，语气要像一个萝莉一样可爱可亲，时不时的会发emoji来辅助表达感情。""")],
)


def create_config_from_json_data(data: dict) -> types.GenerateContentConfig:
    """
    Generates a types.GenerateContentConfig object from a dictionary (parsed JSON).
    """
    config_args = {}

    if "temperature" in data:
        config_args["temperature"] = float(data["temperature"])
    if "top_p" in data:
        config_args["top_p"] = float(data["top_p"])
    if "seed" in data:  # Added seed
        config_args["seed"] = int(data["seed"])
    if "max_output_tokens" in data:
        config_args["max_output_tokens"] = int(data["max_output_tokens"])
    if "response_modalities" in data:
        config_args["response_modalities"] = list(data["response_modalities"])

    if "tools" in data and data["tools"]:
        parsed_tools = []
        for tool_data in data["tools"]:
            if tool_data.get("type") == "google_search":
                parsed_tools.append(types.Tool(
                    google_search=types.GoogleSearch()))
            elif tool_data.get("type") == "retrieval":
                retrieval_data = tool_data.get("retrieval")
                if retrieval_data and retrieval_data.get("vertex_ai_search"):
                    vertex_ai_search_data = retrieval_data["vertex_ai_search"]
                    if "datastore" in vertex_ai_search_data:
                        parsed_tools.append(
                            types.Tool(
                                retrieval=types.Retrieval(
                                    vertex_ai_search=types.VertexAISearch(
                                        datastore=vertex_ai_search_data["datastore"]
                                    )
                                )
                            )
                        )
                    else:
                        raise ValueError(
                            "Missing 'datastore' in vertex_ai_search data.")
                else:
                    raise ValueError(
                        f"Invalid tool type: {tool_data.get('type')}")
        if parsed_tools:
            config_args["tools"] = parsed_tools

    if "thinking_config" in data and data["thinking_config"]:
        thinking_data = data["thinking_config"]
        thinking_args = {}
        if "thinking_budget" in thinking_data:
            thinking_args["thinking_budget"] = int(
                thinking_data["thinking_budget"])
        if thinking_args:
            config_args["thinking_config"] = types.ThinkingConfig(
                **thinking_args)

    if "system_instruction" in data and data["system_instruction"]:
        parsed_parts = []
        for part_data in data["system_instruction"]:
            if part_data.get("type") == "text" and "content" in part_data:
                parsed_parts.append(types.Part.from_text(
                    text=str(part_data["content"])))
        if parsed_parts:
            config_args["system_instruction"] = parsed_parts

    config_args["safety_settings"] = COMMON_SAFETY_SETTINGS
    return types.GenerateContentConfig(**config_args)


def create_config_from_json_string(json_string: str) -> types.GenerateContentConfig:
    """
    Parses a JSON string and then generates a types.GenerateContentConfig object.
    """
    data = json.loads(json_string)
    return create_config_from_json_data(data)


if __name__ == "__main__":
    json_config_str = """
    {
        "temperature": 1.0,
        "top_p": 0.95,
        "seed": 0,
        "max_output_tokens": 8192,
        "response_modalities": ["TEXT"],
        "tools": [
            {
            "type": "google_search"
            }
        ],
        "thinking_config": {
            "thinking_budget": 1024
        },
        "system_instruction": [
            {
            "type": "text",
            "content": "你是一个新闻总结助手。"
            }
        ]
    }
    """
    config = create_config_from_json_string(json_config_str)
    print(config)
