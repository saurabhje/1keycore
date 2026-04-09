PROVIDER_URLS = {
    "openai":    "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "gemini":    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "groq":      "https://api.groq.com/openai/v1/chat/completions",
    "mistral":   "https://api.mistral.ai/v1/chat/completions",
    "cohere":    "https://api.cohere.com/v2/chat",
}

PROVIDER_MODELS = {
    "openai":    ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
    "gemini":    ["gemini-1.5-pro", "gemini-1.5-flash"],
    "groq":      ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "openai/gpt-oss-120b"],
    "mistral":   ["mistral-large-latest", "mistral-small-latest"],
    "cohere":    ["command-r-plus", "command-r"],
}

DEFAULT_MAX_TOKENS = 1024