import React from 'react';
import './ChatMessage.css';

// O componente agora recebe as funções de ação como props
function ChatMessage({ message, onSendSuggestion, onEditSuggestion }) {
  const messageClass = message.sender === 'professional' ? 'message professional' : 'message patient';
  
  const formattedTime = new Date(message.timestamp).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit'
  });

  return (
    <div className={messageClass}>
      <div className="message-bubble">
        <p className="message-text">{message.text}</p>
        <span className="message-time">{formattedTime}</span>
      </div>

      {/* ### NOVA LÓGICA ### */}
      {/* Se a mensagem tiver uma sugestão da IA, mostra a caixa */}
      {message.ai_suggestion && (
        <div className="ai-suggestion-box">
          <div className="suggestion-header">💡 Sugestão da IA</div>
          <p className="suggestion-text">{message.ai_suggestion}</p>
          <div className="suggestion-buttons">
            <button 
              className="suggestion-button send-suggestion"
              onClick={() => onSendSuggestion(message.ai_suggestion)}
            >
              Enviar
            </button>
            <button 
              className="suggestion-button edit-suggestion"
              onClick={() => onEditSuggestion(message.ai_suggestion)}
            >
              Editar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatMessage;