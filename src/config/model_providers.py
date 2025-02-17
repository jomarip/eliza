"""Model provider configurations."""

# Currently active providers
ACTIVE_PROVIDERS = ["openai"]

# Provider configurations
PROVIDER_CONFIGS = {
    "openai": {
        "embeddings": "langchain_community.embeddings.OpenAIEmbeddings",
        "chat": "langchain_openai.ChatOpenAI",
        "default_model": "gpt-4-1106-preview",
        "default_embedding_model": "text-embedding-3-small"
    },
    "anthropic": {
        "chat": "langchain_anthropic.ChatAnthropic",
        "default_model": "claude-3-sonnet-20240229"
    }
} 