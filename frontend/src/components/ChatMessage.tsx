import React, { useState } from 'react';
import { User, Bot, ChevronDown, ChevronRight, Wrench, FileText, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../types';
import './ChatMessage.css';

interface ChatMessageProps {
  message: Message;
  toolCalls?: any[];
  toolResults?: any[];
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, toolCalls, toolResults }) => {
  const isUser = message.role === 'user';
  const [isToolCallExpanded, setIsToolCallExpanded] = useState(true);
  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set());
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  
  // Check if it's a tool call message
  const isToolCallMessage = message.content?.startsWith('🔍');
  
  const handleCopy = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };
  
  const toggleExpand = (index: number) => {
    setExpandedResults(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };
  
  return (
    <div className={`message ${isUser ? 'user-message' : 'assistant-message'}`}>
      <div className="message-icon">
        {isUser ? (
          <div className="icon-wrapper user-icon">
            <User size={18} />
          </div>
        ) : (
          <div className="icon-wrapper assistant-icon">
            <Bot size={18} />
          </div>
        )}
      </div>
      <div className="message-content">
        {isToolCallMessage && toolCalls ? (
          <div className="tool-call-container">
            <div 
              className="tool-call-header"
              onClick={() => setIsToolCallExpanded(!isToolCallExpanded)}
            >
              <Wrench size={16} className="tool-icon" />
              <span className="tool-call-title">Tool Call</span>
              {isToolCallExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            {isToolCallExpanded && (
              <div className="tool-call-details">
                {/* Display input parameters */}
                <div className="tool-section">
                  <div className="tool-section-title">
                    <Wrench size={14} />
                    <span>Input</span>
                  </div>
                  {toolCalls.map((toolCall, index) => {
                    try {
                      const args = JSON.parse(toolCall.function?.arguments || '{}');
                      return (
                        <div key={index} className="tool-call-item">
                          <div className="tool-call-files">
                            {args.file_paths?.map((path: string, i: number) => (
                              <span key={i} className="file-badge">{path}</span>
                            ))}
                          </div>
                        </div>
                      );
                    } catch (e) {
                      return null;
                    }
                  })}
                </div>

                {/* Display response */}
                {toolResults && toolResults.length > 0 && (
                  <div className="tool-section">
                    <div className="tool-section-title">
                      <FileText size={14} />
                      <span>Output</span>
                    </div>
                    {toolResults.map((result, index) => {
                      try {
                        const content = result.content || '';
                        const contentLength = content.length;
                        const MAX_DISPLAY_LENGTH = 500000;
                        const isTruncated = contentLength > MAX_DISPLAY_LENGTH;
                        const displayContent = isTruncated 
                          ? content.substring(0, MAX_DISPLAY_LENGTH) + '\n\n... (content truncated for display)'
                          : content;
                        const isExpanded = expandedResults.has(index);
                        
                        return (
                          <div key={index} className="tool-response">
                            <div className="tool-response-meta-row">
                              <span className="tool-response-meta">
                                {contentLength.toLocaleString()} characters retrieved
                                {isTruncated && ' (displaying first 500,000)'}
                              </span>
                              <div className="tool-response-actions">
                                <button
                                  className="icon-action-button"
                                  onClick={() => toggleExpand(index)}
                                  title={isExpanded ? "Collapse" : "Expand"}
                                >
                                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                </button>
                                <button
                                  className="icon-action-button copy-btn"
                                  onClick={() => handleCopy(content, index)}
                                  title="Copy full content to clipboard"
                                >
                                  {copiedIndex === index ? <Check size={16} /> : <Copy size={16} />}
                                </button>
                              </div>
                            </div>
                            {isExpanded && (
                              <div className="tool-response-content">
                                {displayContent}
                              </div>
                            )}
                          </div>
                        );
                      } catch (e) {
                        console.error('Error rendering tool result:', e);
                        return (
                          <div key={index} className="tool-response">
                            <div className="tool-response-meta" style={{ color: 'red' }}>
                              Error rendering content
                            </div>
                          </div>
                        );
                      }
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="message-text">
            {isUser ? (
              <div className="user-text">{message.content}</div>
            ) : (
              <div className="markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content || ''}
                </ReactMarkdown>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
