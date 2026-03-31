import { Calendar, Filter, Search } from 'lucide-react';
import { DashboardFilters } from './types';

interface SearchFiltersProps {
  filters: DashboardFilters;
  onChange: (next: DashboardFilters) => void;
}

export default function SearchFilters({ filters, onChange }: SearchFiltersProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col lg:flex-row gap-3 lg:items-center">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          value={filters.search}
          onChange={(e) => onChange({ ...filters, search: e.target.value })}
          placeholder="Search reports by ID or status"
          className="w-full rounded-xl border border-slate-200 bg-slate-50 pl-10 pr-3 py-2.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-hospital-blue-500"
        />
      </div>

      <div className="flex gap-3">
        <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 bg-white text-sm text-slate-600">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={filters.mode}
            onChange={(e) => onChange({ ...filters, mode: e.target.value as DashboardFilters['mode'] })}
            className="bg-transparent focus:outline-none"
          >
            <option value="All">All Modes</option>
            <option value="Auto">Auto</option>
            <option value="Assisted">Assisted</option>
          </select>
        </label>

        <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 bg-white text-sm text-slate-600">
          <Calendar className="w-4 h-4 text-slate-400" />
          <select
            value={filters.date}
            onChange={(e) => onChange({ ...filters, date: e.target.value as DashboardFilters['date'] })}
            className="bg-transparent focus:outline-none"
          >
            <option value="All">All Dates</option>
            <option value="Today">Today</option>
            <option value="Last7Days">Last 7 Days</option>
            <option value="Last30Days">Last 30 Days</option>
          </select>
        </label>
      </div>
    </div>
  );
}
