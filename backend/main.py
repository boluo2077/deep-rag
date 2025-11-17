from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import os
import signal
from typing import AsyncIterator
from dotenv import load_dotenv, find_dotenv

from backend.config import settings
from backend.models import (
    ChatRequest, FileRetrievalRequest, FileRetrievalResponse,
    KnowledgeBaseInfo, HealthResponse
)
from backend.knowledge_base import knowledge_base
from backend.llm_provider import LLMProvider
from backend.prompts import create_system_prompt, create_file_retrieval_tool, create_react_system_prompt
from backend.react_handler import handle_react_mode

app = FastAPI(
    title="Deep RAG",
    version="1.0.0",
    description="A Deep RAG system that teaches AI to truly understand your knowledge base"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check"""
    providers = settings.list_available_providers()
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "providers": providers
    }

@app.get("/config")
async def get_config():
    """Get current configuration - dynamically return the current provider's model"""
    config = settings.get_provider_config(settings.api_provider)
    
    return {
        "default_provider": settings.api_provider,
        "default_model": config.get("model", "")
    }

@app.get("/api/config")
async def get_env_config():
    """Read the original content of .env file"""
    env_path = find_dotenv()
    if not env_path:
        raise HTTPException(status_code=404, detail=".env file not found")
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return {"content": content}

@app.post("/api/config")
async def update_env_config(request: dict):
    """Directly save .env file content"""
    env_path = find_dotenv()
    if not env_path:
        raise HTTPException(status_code=404, detail=".env file not found")
    
    content = request.get("content", "")
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Config content cannot be empty")
    
    try:
        # Write content directly
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Reload environment variables
        load_dotenv(override=True)
        
        # Reinitialize settings object
        global settings
        from backend.config import Settings
        settings = Settings()
        
        return {"status": "success", "message": "Configuration updated successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge-base/info", response_model=KnowledgeBaseInfo)
async def get_knowledge_base_info():
    try:
        summary = await knowledge_base.get_file_summary()
        file_tree = knowledge_base.list_files()
        return {
            "summary": summary,
            "file_tree": file_tree
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system-prompt")
async def get_system_prompt():
    """Return the system prompt currently in use"""
    try:
        file_summary = await knowledge_base.get_file_summary()
        
        # Return corresponding system prompt based on configuration
        if settings.tool_calling_mode == "react":
            system_prompt = create_react_system_prompt(file_summary)
        else:
            system_prompt = create_system_prompt(file_summary)
        
        return {
            "system_prompt": system_prompt,
            "mode": settings.tool_calling_mode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge-base/retrieve", response_model=FileRetrievalResponse)
async def retrieve_files(request: FileRetrievalRequest):
    try:
        content = await knowledge_base.retrieve_files(request.file_paths)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        provider = LLMProvider(provider=request.provider or settings.api_provider)
        
        file_summary = await knowledge_base.get_file_summary()
        
        # Check whether to use function calling or ReAct mode
        use_react = settings.tool_calling_mode == "react"
        
        if use_react:
            system_prompt = create_react_system_prompt(file_summary)
        else:
            system_prompt = create_system_prompt(file_summary)
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend([msg.dict() for msg in request.messages])
        
        if use_react:
            async def generate_response() -> AsyncIterator[str]:
                async for chunk in handle_react_mode(provider, messages):
                    yield chunk
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            return StreamingResponse(
                generate_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        tools = [create_file_retrieval_tool()]
        
        async def generate_response() -> AsyncIterator[str]:
            conversation_messages = messages.copy()
            max_iterations = 10
            iteration = 0
            has_content = False
            
            while iteration < max_iterations:
                iteration += 1
                accumulated_tool_call = None
                iteration_has_content = False
                
                async for chunk_str in provider.chat_completion(
                    messages=conversation_messages,
                    tools=tools,
                    stream=True
                ):
                    try:
                        chunk = json.loads(chunk_str)
                        
                        if chunk["type"] == "content":
                            has_content = True
                            iteration_has_content = True
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk['content']})}\n\n"
                        
                        elif chunk["type"] == "tool_calls":
                            tool_calls = chunk["tool_calls"]
                            
                            for tool_call in tool_calls:
                                if accumulated_tool_call is None:
                                    if tool_call.get("id") and tool_call.get("type"):
                                        accumulated_tool_call = {
                                            "index": tool_call.get("index", 0),
                                            "id": tool_call["id"],
                                            "type": tool_call["type"],
                                            "function": {
                                                "name": tool_call.get("function", {}).get("name", ""),
                                                "arguments": tool_call.get("function", {}).get("arguments", "")
                                            }
                                        }
                                else:
                                    if "function" in tool_call and "arguments" in tool_call["function"]:
                                        accumulated_tool_call["function"]["arguments"] += tool_call["function"]["arguments"]
                    
                    except json.JSONDecodeError:
                        continue
                
                if not accumulated_tool_call and iteration_has_content:
                    break
                
                if accumulated_tool_call:
                    yield f"data: {json.dumps({'type': 'tool_calls', 'tool_calls': [accumulated_tool_call]})}\n\n"
                    
                    from backend.prompts import process_tool_calls
                    tool_results = await process_tool_calls([accumulated_tool_call])
                    
                    yield f"data: {json.dumps({'type': 'tool_results', 'results': tool_results})}\n\n"
                    
                    conversation_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [accumulated_tool_call]
                    })
                    
                    conversation_messages.extend(tool_results)
                else:
                    break
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/providers")
async def list_providers():
    """List all configured providers - use dynamic scanning"""
    provider_ids = settings.list_available_providers()
    
    providers = []
    for provider_id in provider_ids:
        config = settings.get_provider_config(provider_id)
        if config.get("model"):
            providers.append({
                "id": provider_id,
                "name": provider_id.replace('_', ' ').title(),
                "models": [config["model"]]
            })
    
    return {"providers": providers}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
