import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, FilePlus2, Activity, UserCheck } from 'lucide-react';

export default function QuickActionPanel() {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <h2 className="text-lg font-black text-slate-900 mb-4">Quick Actions</h2>
      <div className="grid sm:grid-cols-3 gap-3">
        <ActionButton
          to="/auto-coding"
          title="Generate New Report"
          subtitle="Start a fresh coding run"
          icon={<FilePlus2 className="w-5 h-5" />}
          primary
        />
        <ActionButton
          to="/auto-coding"
          title="Auto Coding Mode"
          subtitle="Fully automated flow"
          icon={<Activity className="w-5 h-5" />}
        />
        <ActionButton
          to="/assisted-coding"
          title="Assisted Coding Mode"
          subtitle="Validate and enhance"
          icon={<UserCheck className="w-5 h-5" />}
        />
      </div>
    </div>
  );
}

function ActionButton({
  to,
  title,
  subtitle,
  icon,
  primary,
}: {
  to: string;
  title: string;
  subtitle: string;
  icon: ReactNode;
  primary?: boolean;
}) {
  return (
    <Link
      to={to}
      className={`group rounded-xl border p-4 transition-all flex items-center justify-between gap-4 ${
        primary
          ? 'bg-hospital-blue-600 border-hospital-blue-600 text-white hover:bg-hospital-blue-700'
          : 'bg-white border-slate-200 text-slate-700 hover:border-hospital-blue-300 hover:bg-hospital-blue-50/40'
      }`}
    >
      <div>
        <p className="text-sm font-bold">{title}</p>
        <p className={`text-xs mt-1 ${primary ? 'text-hospital-blue-100' : 'text-slate-500'}`}>{subtitle}</p>
      </div>
      <div className="flex items-center gap-2">
        {icon}
        <ArrowRight className="w-4 h-4 opacity-70 group-hover:translate-x-1 transition-transform" />
      </div>
    </Link>
  );
}
