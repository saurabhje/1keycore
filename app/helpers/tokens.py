from tiktoken import Encoding

def count_tokens(text: str, system_prompt: str | None) -> int:
    enc = Encoding.get_encoding("cl100k_base")
    tokens = len(enc.encode(text))
    if system_prompt:
        tokens += len(enc.encode(system_prompt))
    tokens += 10
    return tokens

def extract_tokens(data: dict, provider: str) -> int:
    try:
        if provider == "openai":
            return data["usage"]["total_tokens"]

        elif provider == "anthropic":
            usage = data.get("usage", {})
            return usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

        elif provider in ["groq", "mistral"]:
            return data["usage"]["total_tokens"]

        elif provider == "gemini":
            meta = data.get("usageMetadata", {})
            return meta.get("totalTokenCount") or (
                meta.get("promptTokenCount", 0)
                + meta.get("candidatesTokenCount", 0)
            )

        elif provider == "cohere":
            meta = data.get("meta", {})
            tokens = meta.get("tokens") or meta.get("billed_units", {})
            return tokens.get("input_tokens", 0) + tokens.get("output_tokens", 0)

    except Exception:
        pass

    return 0