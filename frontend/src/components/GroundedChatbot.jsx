/**
 * GroundedChatbot — Slide-out chat drawer with evidence chips for map highlighting.
 * All answers are grounded in computed satellite analysis data.
 */

import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Shield, MapPin } from 'lucide-react';
import { api } from '../api/client';

export default function GroundedChatbot({ isOpen, onToggle, scanId, onHighlightFeatures }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Welcome to DrishtiAI Assistant. I can answer questions about the satellite imagery you\'ve scanned. Try asking:\n• "How many buildings are there?"\n• "Where are the water bodies?"\n• "What growth occurred since 2021?"',
      confidence: 'high',
      evidenceIds: [],
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setLoading(true);

    try {
      const response = await api.chat(question, scanId);
      const data = response.data;

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: data.answer,
          confidence: data.confidence,
          evidenceIds: data.evidence_ids || [],
          dataSource: data.data_source,
        },
      ]);
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'I cannot determine this from the available evidence. There was an error communicating with the analysis server.',
          confidence: 'none',
          evidenceIds: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleEvidenceClick = (evidenceIds) => {
    if (onHighlightFeatures && evidenceIds.length > 0) {
      onHighlightFeatures(evidenceIds);
    }
  };

  return (
    <>
      {/* Chat toggle button */}
      {!isOpen && (
        <button
          className="chat-toggle-btn"
          onClick={onToggle}
          id="btn-chat-toggle"
          title="Open AI Assistant"
        >
          <MessageSquare size={22} />
        </button>
      )}

      {/* Chat drawer */}
      <div className={`chat-drawer ${isOpen ? 'open' : ''}`} id="chat-drawer">
        <div className="chat-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Shield size={16} />
            <h3>DrishtiAI Assistant</h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="grounded-badge">Grounded</span>
            <button
              className="btn btn-ghost btn-icon"
              onClick={onToggle}
              style={{ color: 'white' }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`chat-message ${msg.role}`}>
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>

              {msg.confidence && msg.role === 'assistant' && (
                <div className={`confidence-badge ${msg.confidence}`}>
                  <Shield size={10} />
                  {msg.confidence === 'high' ? 'High confidence' :
                   msg.confidence === 'medium' ? 'Medium confidence' :
                   msg.confidence === 'low' ? 'Low confidence' : 'No evidence'}
                </div>
              )}

              {msg.evidenceIds?.length > 0 && (
                <div className="evidence-chips">
                  <button
                    className="evidence-chip"
                    onClick={() => handleEvidenceClick(msg.evidenceIds)}
                    title="Click to zoom to evidence on map"
                  >
                    <MapPin size={10} style={{ display: 'inline', verticalAlign: 'middle' }} />
                    {' '}Show {msg.evidenceIds.length} feature{msg.evidenceIds.length > 1 ? 's' : ''} on map
                  </button>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="chat-message assistant">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div className="spinner spinner-dark" style={{ width: 14, height: 14 }} />
                Analyzing spatial data...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask about the satellite imagery..."
            disabled={loading}
            id="chat-input"
          />
          <button
            className="btn btn-primary btn-icon"
            onClick={handleSend}
            disabled={!input.trim() || loading}
            id="btn-chat-send"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </>
  );
}
