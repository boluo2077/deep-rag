from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    provider: Optional[str] = None
    model: Optional[str] = None

class FileRetrievalRequest(BaseModel):
    file_paths: List[str] = Field(..., example=[
        "Product-Line-A-Smartwatch-Series/SW-2100-Flagship.md",
        "2023-Market-Layout/"
    ])

class FileRetrievalResponse(BaseModel):
    content: str

class KnowledgeBaseInfo(BaseModel):
    summary: str
    file_tree: Dict[str, Any]

class ProviderConfig(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    providers: List[str]
