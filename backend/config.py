from pydantic_settings import BaseSettings
from pydantic import Field
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Core configuration class - all settings loaded from .env with defaults"""
    
    api_provider: str = Field(default="google")
    tool_calling_mode: str = Field(default="function")
    temperature: float = Field(default=0.0)
    max_tokens: int = Field(default=8192)
    knowledge_base: str = Field(default="./Knowledge-Base")
    knowledge_base_chunks: str = Field(default="./Knowledge-Base")
    knowledge_base_file_summary: str = Field(default="./Knowledge-Base-File-Summary/summary.txt")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_provider_config(self, provider: str) -> dict:
        """Dynamically get provider configuration from .env"""
        prefix = provider.upper()
        
        config = {
            "api_key": os.getenv(f"{prefix}_API_KEY"),
            "base_url": os.getenv(f"{prefix}_BASE_URL"),
            "model": os.getenv(f"{prefix}_MODEL"),
            "headers": {}
        }
        
        headers_str = os.getenv(f"{prefix}_HEADERS")
        if headers_str:
            import json
            try:
                config["headers"] = json.loads(headers_str)
            except json.JSONDecodeError:
                pass
        
        return config
    
    def list_available_providers(self) -> list:
        """List all configured providers by scanning {PROVIDER}_MODEL environment variables"""
        providers = []
        for key in os.environ:
            if key.endswith('_MODEL'):
                provider = key[:-6].lower()
                providers.append(provider)
        return sorted(providers)

settings = Settings()
