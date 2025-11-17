import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Settings, FileCode } from 'lucide-react';
import { chatApi } from './api';
import type { Message, Provider, StreamChunk } from './types';
import ChatMessage from './components/ChatMessage';
import SystemPromptPanel from './components/SystemPromptPanel';
import ConfigPanel from './components/ConfigPanel';
import './App.css';

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [showConfigPanel, setShowConfigPanel] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [messageToolCalls, setMessageToolCalls] = useState<Map<number, any[]>>(new Map());
  const [messageToolResults, setMessageToolResults] = useState<Map<number, any[]>>(new Map());
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConfig();
    loadProviders();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  const loadConfig = async () => {
    try {
      const config = await chatApi.getConfig();
      setSelectedProvider(config.default_provider);
      setSelectedModel(config.default_model);
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  };

  const loadProviders = async () => {
    try {
      const data = await chatApi.getProviders();
      setProviders(data.providers);
    } catch (error) {
      console.error('Failed to load providers:', error);
    }
  };

  const handleSendMessage = async (messageText?: string) => {
    const textToSend = messageText || inputValue;
    if (!textToSend.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: textToSend,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // Scroll to bottom immediately
    setTimeout(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
      }
    }, 50);

    try {
      const response = await chatApi.sendMessage({
        messages: [...messages, userMessage],
        provider: selectedProvider,
        model: selectedModel,
      });

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';
      let toolCallsInfo = '';
      let currentToolCalls: any[] = [];
      let hasToolCall = false; // Flag for tool calls
      let buffer = ''; // Buffer for handling cross-block JSON

      const processChunk = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          buffer += chunk;
          const lines = buffer.split('\n');
          
          // Keep the last incomplete line
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              try {
                const parsed: StreamChunk = JSON.parse(data);

                if (parsed.type === 'content') {
                  assistantMessage += parsed.content || '';
                  
                  // Check if it contains <|Final Answer|>, if not, may still be in Thought/Action phase
                  const hasFinalAnswer = assistantMessage.includes('<|Final Answer|>');
                  
                  // Only show message when there is <|Final Answer|>
                  if (hasFinalAnswer) {
                    // Extract content after <|Final Answer|>
                    const finalAnswerMatch = assistantMessage.match(/<\|Final Answer\|>\s*([\s\S]*)/);
                    const finalAnswerContent = finalAnswerMatch ? finalAnswerMatch[1].trim() : assistantMessage;
                    
                    setMessages((prev) => {
                      const newMessages = [...prev];
                      const lastMessage = newMessages[newMessages.length - 1];
                      
                      // If just completed tool call, create new message
                      if (hasToolCall && (!lastMessage || lastMessage.content?.startsWith('🔍'))) {
                        newMessages.push({
                          role: 'assistant',
                          content: finalAnswerContent,
                        });
                      } else if (lastMessage && lastMessage.role === 'assistant' && !lastMessage.content?.startsWith('🔍')) {
                        lastMessage.content = finalAnswerContent;
                      } else if (!hasToolCall) {
                        newMessages.push({
                          role: 'assistant',
                          content: finalAnswerContent,
                        });
                      }
                      return newMessages;
                    });
                  }
                } else if (parsed.type === 'tool_calls' && parsed.tool_calls) {
                  hasToolCall = true;
                  currentToolCalls = parsed.tool_calls;
                  toolCallsInfo = '🔍 Retrieving files...';
                  
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages.push({
                      role: 'assistant',
                      content: toolCallsInfo,
                    });
                    
                  // Save tool calls
                    const messageIndex = newMessages.length - 1;
                    setMessageToolCalls(prev => {
                      const newMap = new Map(prev);
                      newMap.set(messageIndex, currentToolCalls);
                      return newMap;
                    });
                    
                    return newMessages;
                  })
                } else if (parsed.type === 'tool_results' && parsed.results) {
                  // Save tool call results
                  console.log('[DEBUG] Received tool_results:', parsed.results.length, 'results');
                  
                  parsed.results.forEach((result: any, index: number) => {
                    console.log(`[DEBUG] Result ${index}: ${result.content?.length || 0} characters`);
                  });
                  
                  setMessages((prev) => {
                    const messageIndex = prev.length - 1;
                    setMessageToolResults(prevResults => {
                      const newMap = new Map(prevResults);
                      newMap.set(messageIndex, parsed.results || []);
                      return newMap;
                    });
                    // Force re-render
                    return [...prev];
                  });
                  // Reset assistantMessage, prepare to receive new content
                  assistantMessage = '';
                } else if (parsed.type === 'done') {
                  // If LLM answers directly without using ReAct format, show complete content on done
                  if (assistantMessage && !assistantMessage.includes('<|Final Answer|>')) {
                    setMessages((prev) => {
                      const newMessages = [...prev];
                      const lastMessage = newMessages[newMessages.length - 1];
                      
                      if (lastMessage && lastMessage.role === 'assistant' && !lastMessage.content?.startsWith('🔍')) {
                        lastMessage.content = assistantMessage;
                      } else {
                        newMessages.push({
                          role: 'assistant',
                          content: assistantMessage,
                        });
                      }
                      return newMessages;
                    });
                  }
                  break;
                }
              } catch (e) {
                console.error('Failed to parse chunk:', e);
              }
            }
          }
        }
      };

      await processChunk();
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="header-title">
            <h1>🔍 Deep RAG</h1>
          </div>
          <div className="header-actions">
            <button
              className="icon-button"
              onClick={() => setShowSystemPrompt(!showSystemPrompt)}
              title="System Prompt"
            >
              <FileCode size={20} />
            </button>
            <button
              className="icon-button"
              onClick={() => setShowConfigPanel(!showConfigPanel)}
              title="Configuration"
            >
              <Settings size={20} />
            </button>
          </div>
        </div>
      </header>

      <div className="main-content">
        {showConfigPanel && (
          <ConfigPanel
            onClose={() => setShowConfigPanel(false)}
            onConfigUpdated={() => {
              loadConfig();
              loadProviders();
            }}
          />
        )}

        {showSystemPrompt && (
          <SystemPromptPanel onClose={() => setShowSystemPrompt(false)} />
        )}

        <div className="chat-container" ref={chatContainerRef}>
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <h2>Welcome to Deep RAG</h2>
              <p>
                Ask questions about your knowledge base and I'll help you find the answers.
              </p>
              <div className="example-questions">
                <h3>Example Questions:</h3>
                <ul>
                  <li onClick={() => handleSendMessage('What display types do we have besides AMOLED and OLED?')}>
                    What display types do we have besides AMOLED and OLED?
                  </li>
                  <li onClick={() => handleSendMessage('Which devices have waterproof ratings higher than IP67?')}>
                    Which devices have waterproof ratings higher than IP67?
                  </li>
                  <li onClick={() => handleSendMessage('Which Bluetooth audio device has the longest battery life?')}>
                    Which Bluetooth audio device has the longest battery life?
                  </li>
                  <li onClick={() => handleSendMessage('What was the total number of retail stores nationwide last year?')}>
                    What was the total number of retail stores nationwide last year?
                  </li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <ChatMessage 
                  key={index} 
                  message={message}
                  toolCalls={messageToolCalls.get(index)}
                  toolResults={messageToolResults.get(index)}
                />
              ))}
              {isLoading && (
                <div className="loading-indicator">
                  <Loader2 className="spinner" size={20} />
                  <span>Thinking...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="input-container">
          <div className="input-wrapper">
            {messages.length > 0 && (
              <button
                className="clear-button"
                onClick={handleClearChat}
                title="Clear chat"
              >
                Clear
              </button>
            )}
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              onFocus={() => setTimeout(scrollToBottom, 100)}
              placeholder="Ask a question about your knowledge base..."
              rows={1}
              disabled={isLoading}
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || isLoading}
              className="send-button"
            >
              {isLoading ? <Loader2 className="spinner" size={20} /> : <Send size={20} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
