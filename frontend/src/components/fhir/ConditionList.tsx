import React from 'react';
import { Badge } from '../ui/Badge';

interface Condition {
  id: string;
  code: string;
  code_display: string;
  clinical_status: string;
  verification_status: string;
  severity?: string;
  onset_datetime?: string;
  abatement_datetime?: string;
}

interface ConditionListProps {
  conditions: Condition[];
  title?: string;
}

const severityVariant = (severity?: string) => {
  switch (severity) {
    case 'severe': return 'danger';
    case 'moderate': return 'warning';
    case 'mild': return 'success';
    default: return 'default';
  }
};

const statusVariant = (status: string) => {
  switch (status) {
    case 'active': return 'danger';
    case 'recurrence': return 'warning';
    case 'resolved': return 'success';
    case 'inactive': return 'default';
    default: return 'default';
  }
};

export const ConditionList: React.FC<ConditionListProps> = ({ conditions, title = 'Active Conditions' }) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
      </div>
      <ul className="divide-y divide-gray-200 dark:divide-gray-700">
        {conditions.map((condition) => (
          <li key={condition.id} className="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {condition.code_display || condition.code}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400 font-mono mt-0.5">
                  ICD-10: {condition.code}
                </p>
                {condition.onset_datetime && (
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                    Onset: {new Date(condition.onset_datetime).toLocaleDateString()}
                    {condition.abatement_datetime && ` — Resolved: ${new Date(condition.abatement_datetime).toLocaleDateString()}`}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {condition.severity && (
                  <Badge variant={severityVariant(condition.severity)}>{condition.severity}</Badge>
                )}
                <Badge variant={statusVariant(condition.clinical_status)}>
                  {condition.clinical_status}
                </Badge>
              </div>
            </div>
          </li>
        ))}
        {conditions.length === 0 && (
          <li className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
            No conditions recorded
          </li>
        )}
      </ul>
    </div>
  );
};

export default ConditionList;
