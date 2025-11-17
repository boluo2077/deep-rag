import React, { useState, useEffect, useRef } from 'react';
import { X, Save, RefreshCw } from 'lucide-react';
import './ConfigPanel.css';

interface ConfigPanelProps {
  onClose: () => void;
  onConfigUpdated: () => void;
}

const ConfigPanel: React.FC<ConfigPanelProps> = ({ onClose, onConfigUpdated }) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/config');
      const data = await response.json();
      setContent(data.content || '');
    } catch (error) {
      console.error('Failed to load config:', error);
      alert('Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(''), 3000);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch('http://localhost:8000/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        throw new Error('Failed to save config');
      }

      const result = await response.json();
      
      // Configuration takes effect immediately on backend, directly refresh frontend state
      await onConfigUpdated();
      
      showToast(result.message || 'Configuration saved and applied!');
      
      // Delay close to show toast
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (error) {
      console.error('Failed to save config:', error);
      showToast('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="config-panel-overlay">
      <div className="config-panel editor-mode" ref={panelRef}>
        <div className="config-panel-header">
          <h2>.env Configuration File</h2>
          <button className="close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {loading ? (
          <div className="config-loading">
            <RefreshCw className="spin" size={24} />
            <p>Loading configuration...</p>
          </div>
        ) : (
          <>
            <div className="config-editor">
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="env-editor"
                spellCheck={false}
                placeholder="Edit .env file content here..."
              />
            </div>

            <div className="config-panel-footer">
              <button onClick={handleSave} disabled={saving} className="save-button">
                {saving ? (
                  <>
                    <RefreshCw className="spin" size={16} />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save size={16} />
                    Save Configuration
                  </>
                )}
              </button>
            </div>
          </>
        )}

        {toastMessage && (
          <div className="toast-notification">
            {toastMessage}
          </div>
        )}
      </div>
    </div>
  );
};

export default ConfigPanel;
