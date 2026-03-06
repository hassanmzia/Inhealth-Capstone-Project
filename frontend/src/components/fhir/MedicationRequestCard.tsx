import React from 'react';
import { Badge } from '../ui/Badge';

interface MedicationRequest {
  id: string;
  medication_code: string;
  medication_display: string;
  status: string;
  intent: string;
  dosage_instruction?: string;
  authored_on?: string;
  requester_name?: string;
}

interface MedicationRequestCardProps {
  medications: MedicationRequest[];
  title?: string;
}

const statusVariant = (status: string) => {
  switch (status) {
    case 'active': return 'success';
    case 'completed': return 'info';
    case 'on-hold': return 'warning';
    case 'cancelled': case 'stopped': return 'danger';
    default: return 'default';
  }
};

export const MedicationRequestCard: React.FC<MedicationRequestCardProps> = ({ medications, title = 'Medications' }) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
        <span className="text-sm text-gray-500 dark:text-gray-400">{medications.length} active</span>
      </div>
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {medications.map((med) => (
          <div key={med.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium text-gray-900 dark:text-white">{med.medication_display}</p>
                {med.dosage_instruction && (
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{med.dosage_instruction}</p>
                )}
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-400 dark:text-gray-500">
                  {med.medication_code && <span>RxNorm: {med.medication_code}</span>}
                  {med.requester_name && <span>Prescribed by: {med.requester_name}</span>}
                  {med.authored_on && <span>{new Date(med.authored_on).toLocaleDateString()}</span>}
                </div>
              </div>
              <Badge variant={statusVariant(med.status)}>{med.status}</Badge>
            </div>
          </div>
        ))}
        {medications.length === 0 && (
          <div className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
            No medications on record
          </div>
        )}
      </div>
    </div>
  );
};

export default MedicationRequestCard;
