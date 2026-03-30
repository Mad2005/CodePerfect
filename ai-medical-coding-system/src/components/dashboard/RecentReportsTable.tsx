import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { DashboardReportItem } from './types';

export default function RecentReportsTable({ reports }: { reports: DashboardReportItem[] }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-black text-slate-900">Recent Reports</h2>
        <Link to="/history" className="text-xs font-bold text-hospital-blue-700 hover:text-hospital-blue-800">
          View All
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-widest text-slate-400 border-b border-slate-100">
              <th className="pb-3 font-semibold">Report ID</th>
              <th className="pb-3 font-semibold">Mode</th>
              <th className="pb-3 font-semibold">Date & Time</th>
              <th className="pb-3 font-semibold">Status</th>
              <th className="pb-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {reports.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="py-3 font-mono text-xs text-slate-700">{item.id}</td>
                <td className="py-3">
                  <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                    item.mode === 'Auto' ? 'bg-hospital-blue-50 text-hospital-blue-700' : 'bg-indigo-50 text-indigo-700'
                  }`}>
                    {item.mode}
                  </span>
                </td>
                <td className="py-3 text-slate-600">{item.timestamp}</td>
                <td className="py-3">
                  <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                    item.status === 'Completed' ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
                  }`}>
                    {item.status}
                  </span>
                </td>
                <td className="py-3 text-right">
                  <a
                    href={`/report/${item.id}`}
                    className="inline-flex items-center gap-1 text-hospital-blue-700 font-semibold hover:text-hospital-blue-800"
                  >
                    Open
                    <ChevronRight className="w-4 h-4" />
                  </a>
                </td>
              </tr>
            ))}
            {reports.length === 0 && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500 italic">
                  No reports matched your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
