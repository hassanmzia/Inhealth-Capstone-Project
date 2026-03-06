import React from 'react';
import { Badge } from '../ui/Badge';

interface Observation {
  id: string;
  code: string;
  code_display: string;
  value_quantity?: number;
  value_unit?: string;
  value_string?: string;
  status: string;
  effective_datetime: string;
  category?: string;
}

interface ObservationTableProps {
  observations: Observation[];
  title?: string;
}

const statusVariant = (status: string) => {
  switch (status) {
    case 'final': return 'success';
    case 'preliminary': return 'warning';
    case 'cancelled': return 'danger';
    default: return 'default';
  }
};

export const ObservationTable: React.FC<ObservationTableProps> = ({ observations, title = 'Observations' }) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-900/50 text-left text-sm text-gray-500 dark:text-gray-400">
              <th className="px-6 py-3 font-medium">Test</th>
              <th className="px-6 py-3 font-medium">LOINC</th>
              <th className="px-6 py-3 font-medium">Value</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {observations.map((obs) => (
              <tr key={obs.id} className="hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors">
                <td className="px-6 py-3 text-sm font-medium text-gray-900 dark:text-white">
                  {obs.code_display || obs.code}
                </td>
                <td className="px-6 py-3 text-sm text-gray-500 dark:text-gray-400 font-mono">
                  {obs.code}
                </td>
                <td className="px-6 py-3 text-sm text-gray-900 dark:text-white">
                  {obs.value_quantity != null
                    ? `${obs.value_quantity} ${obs.value_unit || ''}`
                    : obs.value_string || '—'}
                </td>
                <td className="px-6 py-3">
                  <Badge variant={statusVariant(obs.status)}>{obs.status}</Badge>
                </td>
                <td className="px-6 py-3 text-sm text-gray-500 dark:text-gray-400">
                  {new Date(obs.effective_datetime).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {observations.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  No observations found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ObservationTable;
