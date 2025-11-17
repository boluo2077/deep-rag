import React, { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { chatApi } from '../api';
import ReactMarkdown from 'react-markdown';
import './SystemPromptPanel.css';

interface SystemPromptPanelProps {
  onClose: () => void;
}

const SystemPromptPanel: React.FC<SystemPromptPanelProps> = ({ onClose }) => {
  const [systemPrompt, setSystemPrompt] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSystemPrompt();
  }, []);

  const loadSystemPrompt = async () => {
    try {
      setLoading(true);
      const data = await chatApi.getSystemPrompt();
      setSystemPrompt(data.system_prompt);
    } catch (error) {
      console.error('Failed to load system prompt:', error);
      setSystemPrompt('Error loading system prompt');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sp-overlay">
      <div className="sp-panel" onClick={(e) => e.stopPropagation()}>
        <div className="sp-header">
          <h2>System Prompt</h2>
          <button className="close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        
        <div className="sp-content">
          {loading ? (
            <div className="sp-loading">
              <Loader2 className="spinner" size={32} />
              <p>Loading system prompt...</p>
            </div>
          ) : (
            <div className="sp-markdown">
              <ReactMarkdown>{systemPrompt}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SystemPromptPanel;
