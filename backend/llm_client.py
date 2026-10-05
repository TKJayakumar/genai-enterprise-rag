"""
Thin wrapper around Azure OpenAI so the rest of the pipeline never has to
know whether real credentials are configured. In local demo mode (no Azure
keys), it produces a deterministic extractive answer so every node in the
graph is still exercised end-to-end.
"""
import config

_client = None
if config.AZURE_CONFIGURED:
    from openai import AzureOpenAI
    _client = AzureOpenAI(
        api_key=config.AZURE_OPENAI_API_KEY,
        api_version=config.AZURE_OPENAI_API_VERSION,
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    )


def chat_completion(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    if _client is not None:
        response = _client.chat.completions.create(
            model=config.AZURE_OPENAI_CHAT_DEPLOYMENT,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    # ---- Local fallback (no Azure OpenAI configured) ----
    return _local_fallback_answer(user_prompt)


def _local_fallback_answer(user_prompt: str) -> str:
    """
    Extractive fallback: pulls the CONTEXT block out of the prompt and
    stitches the passages into a plain-language answer with citations,
    so the demo works with zero API keys.
    """
    if "CONTEXT:" not in user_prompt:
        return "I don't have enough retrieved context to answer that confidently."

    context_block = user_prompt.split("CONTEXT:", 1)[1].split("QUESTION:", 1)[0].strip()
    if not context_block:
        return "No relevant enterprise documents were retrieved for this question."

    # Each context line already starts with "[n] (Title) text..." — reuse those
    # lines directly so the [n] citation markers the guardrail checks for are
    # genuinely present in the answer, not just in the prompt.
    lines = [line.strip() for line in context_block.split("\n") if line.strip()]
    excerpt = "\n".join(lines[:2])
    return (
        f"Based on the retrieved enterprise knowledge:\n\n{excerpt}\n\n"
        f"(Local demo mode — set AZURE_OPENAI_* env vars for live GPT-4o generation.)"
    )
