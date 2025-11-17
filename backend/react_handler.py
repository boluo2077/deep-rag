from typing import AsyncIterator
import json
from backend.prompts import process_react_response

async def handle_react_mode(provider, messages, max_iterations=5) -> AsyncIterator[str]:
    """Handle ReAct-style tool calling for LLMs without function calling support"""
    
    conversation_messages = messages.copy()
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        accumulated_response = ""
        action_detected = False
        
        # Get LLM response
        async for chunk_str in provider.chat_completion(
            messages=conversation_messages,
            tools=None,
            stream=True
        ):
            try:
                chunk = json.loads(chunk_str)
                
                if chunk["type"] == "content":
                    content = chunk["content"] or ""
                    accumulated_response += content
                    
                    if "<|Action Input|>" in accumulated_response and "{" in accumulated_response:
                        action_result, has_action = await process_react_response(accumulated_response)
                        if has_action:
                            action_detected = True
                            yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                            break
                    
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                    
            except json.JSONDecodeError:
                continue
        
        # Check if response contains action
        if not action_detected:
            action_result, has_action = await process_react_response(accumulated_response)
        else:
            has_action = True
        
        if not has_action:
            # No action found, this is the final answer
            break
        
        # Send tool call info to frontend
        tool_call_info = {
            "id": f"call_{iteration}",
            "type": "function",
            "function": {
                "name": action_result["action"],
                "arguments": json.dumps(action_result["input"])
            }
        }
        yield f"data: {json.dumps({'type': 'tool_calls', 'tool_calls': [tool_call_info]})}\n\n"
        
        content_length = len(action_result["observation"])
        
        if content_length > 50000:
            frontend_content = f"[Retrieved {content_length:,} characters from knowledge base. Content sent to LLM for analysis.]"
        else:
            frontend_content = action_result["observation"]
        
        tool_result_info = {
            "role": "tool",
            "tool_call_id": f"call_{iteration}",
            "content": frontend_content
        }
        
        result_json = json.dumps({'type': 'tool_results', 'results': [tool_result_info]})
        yield f"data: {result_json}\n\n"
        
        # Add to conversation
        conversation_messages.append({
            "role": "assistant",
            "content": accumulated_response
        })
        
        conversation_messages.append({
            "role": "user",
            "content": f"<|Observation|> {action_result['observation']}\n\nContinue with your reasoning."
        })
