import { ReactNode } from 'react';
import { ShieldCheck, AlertTriangle, CircleCheckBig } from 'lucide-react';

interface ComplianceOverviewProps {
  score: number;
  validCodes: number;
  errors: number;
  warnings: number;
}

export default function ComplianceOverview({
  score,
  validCodes,
  errors,
  warnings,
}: ComplianceOverviewProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <ShieldCheck className="w-5 h-5 text-hospital-blue-600" />
        <h2 className="text-lg font-black text-slate-900">Compliance Overview</h2>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-500">Overall Compliance Score</span>
          <span className="text-lg font-black text-hospital-blue-700">{score}%</span>
        </div>
        <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
          <div className="h-full bg-hospital-blue-600 rounded-full" style={{ width: `${Math.max(0, Math.min(score, 100))}%` }} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center">
        <MetricChip label="Valid Codes" value={validCodes} tone="green" icon={<CircleCheckBig className="w-4 h-4" />} />
        <MetricChip label="Errors" value={errors} tone="red" icon={<AlertTriangle className="w-4 h-4" />} />
        <MetricChip label="Warnings" value={warnings} tone="amber" icon={<AlertTriangle className="w-4 h-4" />} />
      </div>
    </div>
  );
}

function MetricChip({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: number;
  tone: 'green' | 'red' | 'amber';
  icon: ReactNode;
}) {
  const tones = {
    green: 'bg-green-50 text-green-700 border-green-100',
    red: 'bg-red-50 text-red-700 border-red-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
  };

  return (
    <div className={`rounded-xl border px-3 py-3 ${tones[tone]}`}>
      <div className="flex justify-center mb-1">{icon}</div>
      <p className="text-lg font-black">{value}</p>
      <p className="text-[10px] font-bold uppercase tracking-widest">{label}</p>
    </div>
  );
}
