from .remote import OpenAI, AzureOpenAI, BedrockAnthropic

def load_client(name="azure", **kwargs):
    if name == "openai":
        return OpenAI(**kwargs)
    elif name == "azure":
        return AzureOpenAI(**kwargs)
    elif name == "bedrock":
        return BedrockAnthropic(**kwargs)
    elif name == "vllm":
        raise RuntimeError(
            "vLLM client is disabled in this macOS/Ollama environment. "
            "Use client=openai with OPENAI_BASE_URL instead."
        )
    raise ValueError(f"Invalid client name: {name}")