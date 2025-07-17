import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import PatientListItem from './PatientListItem';
import ChatMessage from './ChatMessage';
import SummaryModal from './SummaryModal';
import EditPatientModal from './EditPatientModal'; // Importa o novo modal

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const getAuthHeaders = () => {
  const token = localStorage.getItem('accessToken');
  if (!token) {
    console.error("Token de autenticação não encontrado.");
    return null; 
  }
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
};

function DashboardPage() {
  const [patients, setPatients] = useState([]);
  const navigate = useNavigate();
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const [isSummaryModalOpen, setIsSummaryModalOpen] = useState(false);
  const [summaryContent, setSummaryContent] = useState('');
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [patientToEdit, setPatientToEdit] = useState(null);
  const messageInputRef = useRef(null); 

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    navigate('/login');
  };

  const handleApiError = (err) => {
    console.error("Erro de API:", err);
    if (err.status === 401) {
      setError("Sua sessão expirou. Por favor, faça login novamente.");
      setTimeout(() => handleLogout(), 3000);
    } else {
      setError(err.message || 'Ocorreu um erro de comunicação com o servidor.');
    }
  };

  useEffect(() => {
    const fetchPatients = async () => {
      setError(null);
      setLoading(true);
      const headers = getAuthHeaders();
      if (!headers) {
          handleLogout();
          return;
      }
      try {
        const response = await fetch(`${API_BASE_URL}/api/patients`, { headers });
        if (!response.ok) throw { status: response.status, message: `Falha ao buscar pacientes.` };
        const data = await response.json();
        setPatients(data);
      } catch (e) {
        handleApiError(e);
      } finally {
        setLoading(false);
      }
    };
    fetchPatients();
  }, []);

  useEffect(() => {
    const fetchMessages = async () => {
      if (!selectedPatient) return;
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_BASE_URL}/api/messages/${selectedPatient.id}`, { headers: getAuthHeaders() });
        if (!response.ok) throw { status: response.status, message: "Erro ao buscar mensagens."};
        const data = await response.json();
        setMessages(data);
      } catch (e) {
        handleApiError(e);
      } finally {
        setLoading(false);
      }
    };
    fetchMessages();
  }, [selectedPatient]);
  
  useEffect(() => {
    if (!selectedPatient) return;
    const wsUrl = API_BASE_URL.replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsUrl}/ws/${selectedPatient.id}`);
    ws.onopen = () => console.log(`Conexão WebSocket aberta para o paciente ${selectedPatient.id}`);
    ws.onmessage = (event) => {
      const messageData = JSON.parse(event.data);
      setMessages(prevMessages => [...prevMessages, messageData]);
    };
    ws.onclose = () => console.log(`Conexão WebSocket fechada para o paciente ${selectedPatient.id}`);
    ws.onerror = (error) => console.error("Erro no WebSocket:", error);
    return () => ws.close();
  }, [selectedPatient]);

  const sendMessage = async (textToSend) => {
    if (!textToSend.trim() || !selectedPatient) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/messages/send/${selectedPatient.id}`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ text: textToSend }),
      });
      if (!response.ok) throw { status: response.status, message: "Falha ao enviar a mensagem."};
      const sentMessage = await response.json();
      setMessages(prevMessages => [...prevMessages, sentMessage]);
      setNewMessage('');
    } catch (e) {
      handleApiError(e);
    }
  };

  const handleSendMessage = (e) => { e.preventDefault(); sendMessage(newMessage); };
  const handleSendSuggestion = (suggestionText) => { sendMessage(suggestionText); };
  const handleCopySuggestion = (suggestionText) => { setNewMessage(suggestionText); messageInputRef.current?.focus(); };
  
  const handleToggleControl = async () => {
    if (!selectedPatient) return;
    const isAssuming = selectedPatient.status === 'automatico';
    const endpoint = isAssuming ? 'assume-control' : 'release-control';
    try {
      const response = await fetch(`${API_BASE_URL}/api/patients/${selectedPatient.id}/${endpoint}`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw { status: response.status };
      const updatedStatus = isAssuming ? 'manual' : 'automatico';
      const updatedPatient = {...selectedPatient, status: updatedStatus};
      setSelectedPatient(updatedPatient);
      setPatients(prev => prev.map(p => p.id === selectedPatient.id ? updatedPatient : p));
    } catch (e) {
      handleApiError(e);
    }
  };

  const handleSummarize = async () => {
    if (!selectedPatient) return;
    setIsSummarizing(true);
    setIsSummaryModalOpen(true);
    setSummaryContent('');
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/messages/${selectedPatient.id}/summarize`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!response.ok) {
        const errData = await response.json();
        throw { status: response.status, message: errData.detail || 'Falha ao gerar o resumo.'};
      }
      const data = await response.json();
      setSummaryContent(data.summary);
    } catch (e) {
      handleApiError(e);
      setSummaryContent(`Ocorreu um erro: ${e.message}`);
    } finally {
      setIsSummarizing(false);
    }
  };

  // ### NOVAS FUNÇÕES PARA O MODAL DE EDIÇÃO ###
  const handleOpenEditModal = (patient) => {
    setPatientToEdit(patient);
    setIsEditModalOpen(true);
  };

  const handleSavePatientName = async (newName) => {
    if (!patientToEdit) return;
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/patients/${patientToEdit.id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ name: newName }),
      });
      if (!response.ok) throw { status: response.status };
      const updatedPatient = await response.json();
      setPatients(prev => prev.map(p => p.id === updatedPatient.id ? updatedPatient : p));
      if (selectedPatient && selectedPatient.id === updatedPatient.id) {
        setSelectedPatient(updatedPatient);
      }
      setIsEditModalOpen(false);
      setPatientToEdit(null);
    } catch(e) {
      handleApiError(e);
    }
  };

  const isManualMode = selectedPatient?.status === 'manual';
  const controlButtonText = isManualMode ? 'Encerrar Conversa' : 'Assumir Conversa';

  return (
    <div className="app-container">
      <header className="main-header">
        <h1>Painel SAIP</h1>
        <button onClick={handleLogout} className="logout-button">Sair</button>
      </header>
      <div className="main-content">
        <PatientListItem
          patients={patients}
          selectedPatientId={selectedPatient?.id}
          onSelectPatient={setSelectedPatient}
          onEditPatient={handleOpenEditModal}
        />
        <div className="chat-container">
          {error && <div className="error-message">{error}</div>}
          <div className="chat-view">
            {!selectedPatient ? (
              <div className="chat-view placeholder">
                {loading && <div className="loading-spinner"></div>}
                {!loading && patients.length > 0 && "Selecione um paciente para ver a conversa."}
                {!loading && patients.length === 0 && "Nenhum paciente encontrado. Envie uma mensagem pelo WhatsApp para começar."}
              </div>
            ) : (
              <>
                <header className="chat-header">
                  <h2>{selectedPatient.name || selectedPatient.phone_number}</h2>
                  <div className="header-buttons">
                    <button onClick={handleSummarize} className="control-button summarize-button" disabled={isSummarizing}>
                      {isSummarizing ? 'Gerando...' : 'Resumir com IA'}
                    </button>
                    <button onClick={handleToggleControl} className="control-button">
                      {controlButtonText}
                    </button>
                  </div>
                </header>
                <div className="messages-list">
                  {loading && !isSummaryModalOpen ? (
                    <div className="loading-spinner"></div>
                  ) : messages.length === 0 ? (
                    <p>Nenhuma mensagem encontrada.</p>
                  ) : (
                    messages.map((msg) => (
                      <ChatMessage 
                        key={msg.id} 
                        message={msg}
                        onSendSuggestion={handleSendSuggestion}
                        onEditSuggestion={handleCopySuggestion}
                      />
                    ))
                  )}
                </div>
                {isManualMode && (
                  <footer className="chat-footer">
                    <form onSubmit={handleSendMessage} className="message-form">
                      <input
                        ref={messageInputRef}
                        type="text"
                        className="message-input"
                        placeholder="Digite sua mensagem ou edite a sugestão..."
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                      />
                      <button type="submit" className="send-button">Enviar</button>
                    </form>
                  </footer>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      {isSummaryModalOpen && (
        <SummaryModal 
          summary={summaryContent}
          isLoading={isSummarizing}
          onClose={() => setIsSummaryModalOpen(false)}
        />
      )}
      {isEditModalOpen && (
        <EditPatientModal 
          patient={patientToEdit}
          onClose={() => setIsEditModalOpen(false)}
          onSave={handleSavePatientName}
        />
      )}
    </div>
  );
}

export default DashboardPage;