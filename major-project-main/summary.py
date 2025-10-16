# pip install openai python-dotenv
def summarize_openrouter(text: str,
                         model: str = "openrouter/auto",
                         base_url: str = "https://openrouter.ai/api/v1") -> str:
    import os
    from openai import OpenAI

    api_key = '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'
    if not api_key:
        raise ValueError("Set OPENROUTER_API_KEY in your environment")

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        default_headers={"HTTP-Referer": "http://localhost"}  # use your app URL in production
    )
    messages = [
        {"role": "system", "content": "Summarize the user's text clearly and concisely in 3-5 sentences."},
        {"role": "user", "content": text},
    ]
    resp = client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content.strip()


print(summarize_openrouter("OpenRouter is an open-source platform that provides access to various large language models (LLMs) through a unified API. It allows developers to easily integrate and utilize different LLMs in their applications without needing to manage multiple APIs or services. OpenRouter supports models from various providers, enabling users to choose the best model for their specific use cases. The platform aims to simplify the process of working with LLMs and promote the adoption of AI technologies across different industries."))
