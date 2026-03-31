import { BarChart3, Clock3, TriangleAlert, Tags } from 'lucide-react';

interface PerformanceInsightsProps {
  averageProcessingTimeSec: number;
  frequentErrors: string[];
  mostUsedCodes: string[];
}

export default function PerformanceInsights({
  averageProcessingTimeSec,
  frequentErrors,
  mostUsedCodes,
}: PerformanceInsightsProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-5 h-5 text-hospital-blue-600" />
        <h2 className="text-lg font-black text-slate-900">Performance Insights</h2>
      </div>

      <div className="space-y-4">
        <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
          <p className="text-xs uppercase tracking-widest font-bold text-slate-400 mb-1">Average Processing Time</p>
          <div className="flex items-center gap-2 text-slate-800 font-bold">
            <Clock3 className="w-4 h-4 text-hospital-blue-600" />
            {averageProcessingTimeSec.toFixed(1)} seconds
          </div>
        </div>

        <div>
          <p className="text-xs uppercase tracking-widest font-bold text-slate-400 mb-2 flex items-center gap-2">
            <TriangleAlert className="w-4 h-4 text-amber-600" /> Most Frequent Errors
          </p>
          <ul className="space-y-2">
            {frequentErrors.map((error) => (
              <li key={error} className="text-sm text-slate-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                {error}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-xs uppercase tracking-widest font-bold text-slate-400 mb-2 flex items-center gap-2">
            <Tags className="w-4 h-4 text-hospital-blue-600" /> Most Used Codes
          </p>
          <div className="flex flex-wrap gap-2">
            {mostUsedCodes.map((code) => (
              <span key={code} className="px-2.5 py-1 rounded-full bg-hospital-blue-50 text-hospital-blue-700 text-xs font-bold font-mono">
                {code}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
