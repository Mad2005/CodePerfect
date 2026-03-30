import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Search, 
  Filter, 
  Calendar, 
  FileText, 
  ChevronRight, 
  Download, 
  Trash2, 
  Eye,
  Clock,
  User,
  CheckCircle2,
  ArrowUpDown,
  X,
  Activity,
  ExternalLink
} from 'lucide-react';
import { HistoryItem } from '@/types';

export default function History() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMode, setFilterMode] = useState<'All' | 'Auto' | 'Assisted'>('All');
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetch('/api/reports')
      .then(res => res.json())
      .then(data => {
        if (data.reports) {
          const mapped = data.reports.map((r: any) => {
            const tsStr = r.name.split('_')[1]?.split('.')[0];
            let dateStr = 'Unknown';
            if (tsStr) {
              dateStr = new Date(parseInt(tsStr) * 1000).toLocaleString();
            }
            return {
              id: r.name,
              title: r.mode === 'compare' ? 'Assisted Coding Report' : 'Auto Coding Report',
              timestamp: dateStr,
              mode: r.mode === 'compare' ? 'Assisted' : 'Auto',
              patientId: `P-${Math.floor(Math.random() * 9000) + 1000}`
            };
          });
          setItems(mapped);
        }
      })
      .catch(err => console.error(err))
      .finally(() => setIsLoading(false));
  }, []);

  const filteredHistory = items.filter(item => {
    const matchesSearch = item.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                         item.patientId.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterMode === 'All' || item.mode === filterMode;
    return matchesSearch && matchesFilter;
  });

  const deleteItem = (id: string) => {
    // Call API to delete the file
    fetch(`/api/delete/${id}`, { method: 'DELETE' })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'ok') {
          setItems(items.filter(item => item.id !== id));
        } else {
          console.error('Delete failed:', data.message);
          alert('Failed to delete report: ' + data.message);
        }
      })
      .catch(err => {
        console.error('Delete error:', err);
        alert('Error deleting report');
      });
  };

  const downloadItem = (id: string) => {
    // Download the report as HTML. Users can print to PDF using browser's print dialog (Ctrl+P / Cmd+P)
    window.location.href = `/api/download/${id}`;
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div>
          <h1 className="text-5xl font-black text-slate-900 tracking-tight mb-4">Coding History</h1>
          <p className="text-slate-500 font-medium max-w-md leading-relaxed">
            Access and manage all previously generated medical coding reports and audits.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="bg-white border border-slate-200 rounded-2xl p-1 flex shadow-sm">
            {(['All', 'Auto', 'Assisted'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setFilterMode(mode)}
                className={`px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                  filterMode === mode 
                    ? 'bg-hospital-blue-600 text-white shadow-lg shadow-hospital-blue-100' 
                    : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-white rounded-3xl border border-slate-200 p-4 mb-8 shadow-sm flex flex-col md:flex-row gap-4 items-center">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
          <input
            type="text"
            placeholder="Search by report title or patient ID..."
            className="w-full pl-12 pr-4 py-3 bg-slate-50 border-none rounded-2xl text-sm font-medium focus:ring-2 focus:ring-hospital-blue-500 transition-all placeholder:text-slate-400"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button 
              onClick={() => setSearchTerm('')}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-1 hover:bg-slate-200 rounded-full transition-colors"
            >
              <X className="w-3 h-3 text-slate-500" />
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <button 
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-6 py-3 rounded-2xl border transition-all font-bold text-sm ${
              showFilters ? 'bg-slate-900 border-slate-900 text-white' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <button className="flex items-center gap-2 px-6 py-3 rounded-2xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition-all font-bold text-sm">
            <ArrowUpDown className="w-4 h-4" />
            Sort
          </button>
        </div>
      </div>

      {/* History List */}
      <div className="space-y-4">
        <AnimatePresence mode="popLayout">
          {filteredHistory.length > 0 ? (
            filteredHistory.map((item, idx) => (
              <motion.div
                layout
                key={item.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: idx * 0.05 }}
                className="group bg-white border border-slate-200 rounded-3xl p-6 hover:border-hospital-blue-300 hover:shadow-xl hover:shadow-hospital-blue-100/20 transition-all"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div className="flex items-start gap-5">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-110 ${
                      item.mode === 'Auto' ? 'bg-purple-50 text-purple-600' : 'bg-blue-50 text-blue-600'
                    }`}>
                      {item.mode === 'Auto' ? <Activity className="w-7 h-7" /> : <FileText className="w-7 h-7" />}
                    </div>
                    <div>
                      <h3 className="text-xl font-black text-slate-900 group-hover:text-hospital-blue-600 transition-colors mb-1">
                        {item.title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-y-2 gap-x-4">
                        <span className="flex items-center gap-1.5 text-xs font-bold text-slate-400">
                          <User className="w-3.5 h-3.5" />
                          ID: {item.patientId}
                        </span>
                        <div className="w-1 h-1 bg-slate-200 rounded-full hidden sm:block" />
                        <span className="flex items-center gap-1.5 text-xs font-bold text-slate-400">
                          <Clock className="w-3.5 h-3.5" />
                          {item.timestamp}
                        </span>
                        <div className="w-1 h-1 bg-slate-200 rounded-full hidden sm:block" />
                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-widest ${
                          item.mode === 'Auto' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                        }`}>
                          {item.mode}
                        </span>
                        <div className="w-1 h-1 bg-slate-200 rounded-full hidden sm:block" />
                        <span className="flex items-center gap-1 text-[10px] font-black text-green-600 uppercase tracking-widest">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Validated
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 self-end md:self-center">
                    <a 
                      href={`/report/${item.id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="p-3 rounded-xl border border-slate-100 text-slate-400 hover:text-hospital-blue-600 hover:bg-hospital-blue-50 transition-all"
                      title="View Report"
                    >
                      <Eye className="w-5 h-5" />
                    </a>
                    <button 
                      onClick={() => downloadItem(item.id)}
                      className="p-3 rounded-xl border border-slate-100 text-slate-400 hover:text-hospital-blue-600 hover:bg-hospital-blue-50 transition-all"
                      title="Download HTML (use Ctrl+P or Cmd+P to print as PDF)"
                    >
                      <Download className="w-5 h-5" />
                    </button>
                    <button 
                      onClick={() => deleteItem(item.id)}
                      className="p-3 rounded-xl border border-slate-100 text-slate-400 hover:text-red-600 hover:bg-red-50 transition-all"
                      title="Delete"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                    <div className="w-px h-8 bg-slate-100 mx-2 hidden md:block" />
                    <a 
                      href={`/report/${item.id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-2 px-6 py-3 bg-slate-50 text-slate-900 font-black rounded-2xl hover:bg-hospital-blue-600 hover:text-white transition-all text-sm group/btn"
                    >
                      Open
                      <ChevronRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
                    </a>
                  </div>
                </div>
              </motion.div>
            ))
          ) : isLoading ? (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="py-24 text-center bg-slate-50 rounded-3xl border border-slate-200"
            >
              <h3 className="text-xl font-bold text-slate-500">Loading history...</h3>
            </motion.div>
          ) : (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="py-24 text-center bg-slate-50 rounded-3xl border-2 border-dashed border-slate-200"
            >
              <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm">
                <Search className="w-10 h-10 text-slate-200" />
              </div>
              <h3 className="text-2xl font-black text-slate-900 mb-2">No reports found</h3>
              <p className="text-slate-500 font-medium max-w-xs mx-auto">
                Try adjusting your search or filters to find what you're looking for.
              </p>
              <button 
                onClick={() => { setSearchTerm(''); setFilterMode('All'); }}
                className="mt-8 px-8 py-3 bg-white border border-slate-200 text-slate-900 font-bold rounded-2xl hover:bg-slate-50 transition-all"
              >
                Clear all filters
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Pagination Mock */}
      {filteredHistory.length > 0 && (
        <div className="mt-12 flex items-center justify-between">
          <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">
            Showing <span className="text-slate-900">{filteredHistory.length}</span> of <span className="text-slate-900">{items.length}</span> reports
          </p>
          <div className="flex items-center gap-2">
            <button className="px-4 py-2 rounded-xl border border-slate-200 text-slate-400 font-bold text-sm disabled:opacity-50" disabled>Previous</button>
            <button className="w-10 h-10 rounded-xl bg-hospital-blue-600 text-white font-bold text-sm">1</button>
            <button className="w-10 h-10 rounded-xl border border-slate-200 text-slate-600 font-bold text-sm hover:bg-slate-50">2</button>
            <button className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 font-bold text-sm hover:bg-slate-50">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
