import React from 'react';
import { Badge } from '../ui/Badge';
import type { FHIRPatient } from '../../types/fhir';

interface PatientBannerProps {
  patient: FHIRPatient;
  onViewDetails?: () => void;
}

const getAgeFromBirthDate = (birthDate?: string): number | null => {
  if (!birthDate) return null;
  const today = new Date();
  const birth = new Date(birthDate);
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
  return age;
};

export const PatientBanner: React.FC<PatientBannerProps> = ({ patient, onViewDetails }) => {
  const age = getAgeFromBirthDate(patient.birth_date);
  const fullName = [patient.name_given, patient.name_family].filter(Boolean).join(' ');

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div className="h-12 w-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
          <span className="text-blue-700 dark:text-blue-400 font-semibold text-lg">
            {(patient.name_given?.[0] || '').toUpperCase()}{(patient.name_family?.[0] || '').toUpperCase()}
          </span>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{fullName || 'Unknown Patient'}</h2>
          <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
            {patient.identifier_mrn && <span>MRN: {patient.identifier_mrn}</span>}
            {patient.gender && <span className="capitalize">{patient.gender}</span>}
            {age !== null && <span>{age} years</span>}
            {patient.birth_date && <span>DOB: {patient.birth_date}</span>}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant={patient.active ? 'success' : 'danger'} dot>
          {patient.active ? 'Active' : 'Inactive'}
        </Badge>
        {onViewDetails && (
          <button
            onClick={onViewDetails}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            View Details
          </button>
        )}
      </div>
    </div>
  );
};

export default PatientBanner;
