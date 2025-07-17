import React from 'react';
import './SummaryModal.css';

function SummaryModal({ summary, isLoading, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Resumo da IA</h2>
          <button onClick={onClose} className="close-button">&times;</button>
        </div>
        <div className="modal-body">
          {isLoading ? (
            <div className="summary-loading-spinner"></div>
          ) : (
            // Usa <pre> para manter a formatação do texto, como quebras de linha e espaços
            <pre className="summary-text">{summary}</pre>
          )}
        </div>
      </div>
    </div>
  );
}

export default SummaryModal;