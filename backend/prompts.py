import json
from typing import List, Dict
from datetime import datetime
from backend.knowledge_base import knowledge_base


def _create_base_system_prompt(file_summary: str) -> str:
    """Shared base system prompt"""
    current_time = datetime.now().strftime("%A, %B %d, %Y, at %I:%M:%S %p")
    
    return f"""
- Answers must strictly come from the knowledge base
- To answer completely, you may call the `retrieve_files` tool multiple times
- If you're 100% certain of the answer, you may skip calling the `retrieve_files` tool
- If after diligent multi-round retrieval you still haven't found relevant knowledge, please answer "I don't know"
- Current time: {current_time}

## Knowledge Base File Summary
```
{file_summary}
```

## retrieve_files
- NEVER answer "I don't know" without calling the `retrieve_files` tool
- Input format: {{"file_paths": ["path1", "path2"]}}

### Examples
- Retrieve specific files: ["Product-Line-A-Smartwatch-Series/SW-1500-Sport.md", "Product-Line-B-Smart-Earbuds-Series/AE-Sport-Athletic.md"]
- Retrieve multiple directories: ["2024-Market-Layout/", "2023-Market-Layout/"]
- Retrieve directories and files together: ["2024-Market-Layout/", "2023-Market-Layout/South-China-Region.md"]
- Retrieve all files: ["/"]

""".strip()


def create_system_prompt(file_summary: str) -> str:
    """System prompt for function calling mode"""
    return _create_base_system_prompt(file_summary)


def create_react_system_prompt(file_summary: str) -> str:
    """System prompt for ReAct mode with format instructions"""
    base_prompt = _create_base_system_prompt(file_summary)
    
    return f"""
{base_prompt}

## Direct Answer
- `Knowledge Base File Summary` has the answer

### Example
- Question: Besides AMOLED and OLED screens, what other display types do we have?
- Answer: LCD, TFT

## Tool Call
- `Knowledge Base File Summary` doesn't have enough details

### Pattern
- <|Thought|> Think about what information you need to answer the question
- <|Action|> Tool
- <|Action Input|> Input format
- <|Observation|> [The system will provide file contents here]
- ... (repeat Thought/Action/Observation as needed)
- <|Final Answer|> [Your final answer based on the retrieved information]

### Example
- Question: What are all the technical specifications of SW-2100?
- <|Thought|> The File Summary only mentions basic info. I need the complete product file for all specifications
- <|Action|> retrieve_files
- <|Action Input|> {{"file_paths": ["Product-Line-A-Smartwatch-Series/SW-2100-Flagship.md"]}}
- <|Observation|> [System provides file content]
- <|Final Answer|> [Complete specifications based on retrieved file]

""".strip()
    

def create_file_retrieval_tool() -> Dict:
    return {
        "type": "function",
        "function": {
            "name": "retrieve_files",
            "description": "Retrieve file contents from the knowledge base. You can retrieve specific files, entire directories, or all files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths or directory paths to retrieve. Use '/' to retrieve all files."
                    }
                },
                "required": ["file_paths"]
            }
        }
    }


async def process_tool_calls(tool_calls: List[Dict]) -> List[Dict]:
    results = []

    for tool_call in tool_calls:
        if tool_call.get("function", {}).get("name") == "retrieve_files":
            try:
                args = json.loads(tool_call["function"]["arguments"])
                file_paths = args.get("file_paths", [])

                content = await knowledge_base.retrieve_files(file_paths)

                results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": content
                })
            except Exception as e:
                results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": f"Error retrieving files: {str(e)}"
                })

    return results


def parse_react_response(text: str) -> tuple:
    """Parse ReAct-style response to extract action and input"""
    import re

    # 查找 <|Action|> 和 <|Action Input|> (新格式)
    action_pattern = r'<\|Action\|>\s*(\w+)'
    action_input_pattern = r'<\|Action Input\|>\s*(\{[^}]+\})'

    action_match = re.search(action_pattern, text)
    action_input_match = re.search(action_input_pattern, text)

    if action_match and action_input_match:
        action = action_match.group(1)
        try:
            action_input = json.loads(action_input_match.group(1))
            return action, action_input, True
        except:
            pass

    return None, None, False


async def process_react_response(text: str) -> tuple:
    """Process ReAct response and execute actions"""
    action, action_input, has_action = parse_react_response(text)

    if has_action and action == "retrieve_files":
        file_paths = action_input.get("file_paths", [])
        content = await knowledge_base.retrieve_files(file_paths)

        return {
            "action": action,
            "input": action_input,
            "observation": content
        }, True

    return None, False
