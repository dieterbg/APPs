import React from 'react';
import './PatientListItem.css';

function PatientListItem({ patients, selectedPatientId, onSelectPatient, onEditPatient }) {
  return (
    <aside className="patient-list">
      <header>
        <h1>Pacientes</h1>
      </header>
      <ul>
        {patients.map((patient) => (
          <li
            key={patient.id}
            className={patient.id === selectedPatientId ? 'selected' : ''}
            onClick={() => onSelectPatient(patient)}
          >
            <div className="patient-info">
              <span className="patient-name">{patient.name || patient.phone_number}</span>
              <div className="patient-actions">
                {patient.has_alert && <span className="alert-indicator">!</span>}
                <button 
                  className="edit-patient-button" 
                  onClick={(e) => {
                    e.stopPropagation(); // Impede que o clique selecione o paciente
                    onEditPatient(patient);
                  }}
                  title="Editar nome do paciente"
                >
                  ✏️
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}

export default PatientListItem;