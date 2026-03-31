import { BellRing } from 'lucide-react';

export interface DashboardAlert {
  id: string;
  tone: 'warning' | 'success' | 'info';
  message: string;
}

export default function AlertsPanel({ alerts }: { alerts: DashboardAlert[] }) {
  if (!alerts.length) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <BellRing className="w-5 h-5 text-hospital-blue-600" />
        <h2 className="text-lg font-black text-slate-900">Alerts & Notifications</h2>
      </div>

      <div className="space-y-3">
        {alerts.map((alert) => (
          <div key={alert.id} className={`rounded-xl border px-4 py-3 text-sm font-medium ${toneClasses[alert.tone]}`}>
            {alert.message}
          </div>
        ))}
      </div>
    </div>
  );
}

const toneClasses = {
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  success: 'bg-green-50 border-green-200 text-green-800',
  info: 'bg-hospital-blue-50 border-hospital-blue-200 text-hospital-blue-800',
};
