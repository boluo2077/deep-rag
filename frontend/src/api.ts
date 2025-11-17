import axios from 'axios';
import type { ChatRequest, Provider, KnowledgeBaseInfo } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const chatApi = {
  sendMessage: async (request: ChatRequest) => {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    return response;
  },

  getConfig: async (): Promise<{ default_provider: string; default_model: string }> => {
    const response = await api.get('/config');
    return response.data;
  },

  getProviders: async (): Promise<{ providers: Provider[] }> => {
    const response = await api.get('/providers');
    return response.data;
  },

  getKnowledgeBaseInfo: async (): Promise<KnowledgeBaseInfo> => {
    const response = await api.get('/knowledge-base/info');
    return response.data;
  },

  getSystemPrompt: async (): Promise<{ system_prompt: string; mode: string }> => {
    const response = await api.get('/system-prompt');
    return response.data;
  },

  retrieveFiles: async (filePaths: string[]): Promise<{ content: string }> => {
    const response = await api.post('/knowledge-base/retrieve', {
      file_paths: filePaths,
    });
    return response.data;
  },
};

export default api;
