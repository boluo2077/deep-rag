export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  messages: Message[];
  provider?: string;
  model?: string;
  // Note: temperature, max_tokens, stream have been removed
  // temperature and max_tokens can only be set through global configuration in backend .env file
  // stream is forced to true and cannot be modified
}

export interface Provider {
  id: string;
  name: string;
  models: string[];
}

export interface KnowledgeBaseInfo {
  summary: string;
  file_tree: FileNode;
}

export interface FileNode {
  type: 'file' | 'directory';
  name: string;
  path?: string;
  children?: FileNode[];
}

export interface ToolCall {
  id: string;
  type: string;
  function: {
    name: string;
    arguments: string;
  };
}

export interface StreamChunk {
  type: 'content' | 'tool_calls' | 'tool_results' | 'done';
  content?: string;
  tool_calls?: ToolCall[];
  results?: ToolResult[];
}

export interface ToolResult {
  role: string;
  tool_call_id: string;
  content: string;
}
