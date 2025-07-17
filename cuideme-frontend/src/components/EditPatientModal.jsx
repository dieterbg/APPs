import React, { useState, useEffect } from 'react';
import './EditPatientModal.css';

function EditPatientModal({ patient, onClose, onSave }) {
  const [name, setName] = useState('');

  useEffect(() => {
    // Preenche o campo com o nome atual do paciente quando o modal abre
    if (patient) {
      setName(patient.name || '');
    }
  }, [patient]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(name);
  };

  if (!patient) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Editar Paciente</h2>
          <button onClick={onClose} className="close-button">&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="input-group">
              <label htmlFor="patient-name">Nome do Paciente</label>
              <input
                id="patient-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" onClick={onClose} className="cancel-button">Cancelar</button>
            <button type="submit" className="save-button">Salvar</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default EditPatientModal;