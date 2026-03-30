import { motion } from 'motion/react';
import { CheckCircle2, Circle, Loader2, Workflow } from 'lucide-react';
import { LiveProcessState } from './types';

export default function LiveProcessStatus({ process }: { process: LiveProcessState | null }) {
  if (!process) return null;

  return (
    <div className="bg-white border border-hospital-blue-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Workflow className="w-5 h-5 text-hospital-blue-600" />
        <h2 className="text-lg font-black text-slate-900">Live Process Status</h2>
      </div>

      <div className="mb-4">
        <p className="text-sm text-slate-500">Current Step</p>
        <p className="text-base font-bold text-hospital-blue-700">{process.currentStep}</p>
        <p className="text-sm text-slate-600 mt-1">{process.message}</p>
      </div>

      <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden mb-5">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(0, Math.min(process.progress, 100))}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="h-full bg-hospital-blue-600 rounded-full"
        />
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        {process.steps.map((step) => (
          <div key={step.id} className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2">
            {step.status === 'completed' ? (
              <CheckCircle2 className="w-4 h-4 text-green-600" />
            ) : step.status === 'processing' ? (
              <Loader2 className="w-4 h-4 text-hospital-blue-600 animate-spin" />
            ) : (
              <Circle className="w-4 h-4 text-slate-400" />
            )}
            <span className={`text-xs font-semibold ${
              step.status === 'processing' ? 'text-hospital-blue-700' : step.status === 'completed' ? 'text-slate-800' : 'text-slate-500'
            }`}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
