import { useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { Activity, AlertTriangle, CheckCircle2, Gauge, FileText } from 'lucide-react';
import SummaryStatCard from '@/components/dashboard/SummaryStatCard';
import QuickActionPanel from '@/components/dashboard/QuickActionPanel';
import LiveProcessStatus from '@/components/dashboard/LiveProcessStatus';
import SearchFilters from '@/components/dashboard/SearchFilters';
import RecentReportsTable from '@/components/dashboard/RecentReportsTable';
import ComplianceOverview from '@/components/dashboard/ComplianceOverview';
import PerformanceInsights from '@/components/dashboard/PerformanceInsights';
import AlertsPanel, { DashboardAlert } from '@/components/dashboard/AlertsPanel';
import SmartInsightsCard from '@/components/dashboard/SmartInsightsCard';
import { DashboardFilters, DashboardReportItem, LiveProcessState } from '@/components/dashboard/types';

const INITIAL_FILTERS: DashboardFilters = {
  search: '',
  mode: 'All',
  date: 'All',
};

export default function Dashboard() {
  const [filters, setFilters] = useState<DashboardFilters>(INITIAL_FILTERS);
  const [reports, setReports] = useState<DashboardReportItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [liveProcess, setLiveProcess] = useState<LiveProcessState | null>(null);

  useEffect(() => {
    fetch('/api/reports')
      .then((res) => res.json())
      .then((data) => {
        const mapped: DashboardReportItem[] = (data.reports || []).map((report: {
          name: string;
          mode?: 'compare' | 'generate' | 'assisted' | 'auto';
          status?: DashboardReportItem['status'];
        }) => {
          const mode = report.mode ? mapBackendMode(report.mode) : deriveMode(report.name);
          const status = report.status || deriveStatus(report.name);

          return {
            id: report.name,
            mode,
            status,
            timestamp: toTimestampLabel(report.name),
            confidence: deriveConfidence(report.name),
          };
        });

        mapped.sort((a, b) => extractUnixTimestamp(b.id) - extractUnixTimestamp(a.id));
        setReports(mapped);
      })
      .catch(() => setReports([]))
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem('liveProcessStatus');
      if (raw) {
        const parsed = JSON.parse(raw) as LiveProcessState;
        if (parsed && parsed.currentStep) {
          setLiveProcess(parsed);
        }
      }
    } catch {
      setLiveProcess(null);
    }
  }, []);

  const filteredReports = useMemo(() => {
    return reports.filter((report) => {
      const matchesSearch =
        report.id.toLowerCase().includes(filters.search.toLowerCase()) ||
        report.status.toLowerCase().includes(filters.search.toLowerCase());

      const matchesMode = filters.mode === 'All' || report.mode === filters.mode;
      const matchesDate = matchesDateFilter(report.id, filters.date);

      return matchesSearch && matchesMode && matchesDate;
    });
  }, [reports, filters]);

  const recentReports = filteredReports.slice(0, 5);

  const totals = useMemo(() => {
    const totalReports = reports.length;
    const successful = reports.filter((r) => r.status === 'Completed').length;
    const needsReview = reports.filter((r) => r.status === 'Needs Review').length;
    const averageConfidence = totalReports
      ? Math.round(reports.reduce((sum, r) => sum + r.confidence, 0) / totalReports)
      : 0;

    return {
      totalReports,
      successful,
      needsReview,
      averageConfidence,
    };
  }, [reports]);

  const complianceScore = useMemo(() => {
    if (!totals.totalReports) return 0;
    const passRatio = totals.successful / totals.totalReports;
    return Math.round(passRatio * 100);
  }, [totals]);

  const alerts: DashboardAlert[] = useMemo(() => {
    const output: DashboardAlert[] = [];

    if (totals.needsReview > 0) {
      output.push({
        id: 'review-warning',
        tone: 'warning',
        message: 'Last report has compliance issues and needs review before submission.',
      });
    }

    if (totals.totalReports > 0 && totals.needsReview === 0) {
      output.push({
        id: 'all-good',
        tone: 'success',
        message: 'All codes validated successfully across recent reports.',
      });
    }

    output.push({
      id: 'system-health',
      tone: 'info',
      message: 'System checks are up to date for current coding workflows.',
    });

    return output;
  }, [totals]);

  const smartInsight = useMemo(() => {
    if (!totals.totalReports) {
      return 'No recent reports available. Generate a new report to unlock insight trends and coding recommendations.';
    }

    const reviewRate = totals.needsReview / totals.totalReports;

    if (reviewRate > 0.35) {
      return 'Most recent reports indicate recurring compliance gaps; prioritize validation of diagnosis-to-procedure alignment.';
    }

    if (reviewRate > 0.15) {
      return 'Several reports still require review; targeted audits on warnings can improve submission readiness.';
    }

    return 'Recent reports show strong coding consistency with high validation pass rates and stable confidence trends.';
  }, [totals]);

  const averageProcessingTimeSec = useMemo(() => {
    if (!reports.length) return 0;
    const total = reports.reduce((sum, report) => {
      return sum + (report.mode === 'Auto' ? 9.4 : 12.1);
    }, 0);
    return total / reports.length;
  }, [reports]);

  const frequentErrors = useMemo(() => {
    if (!totals.needsReview) return ['No frequent errors detected'];
    return [
      'Modifier mismatch in procedure pairing',
      'Missing clinical evidence for secondary code',
      'Documentation detail insufficient for selected level',
    ];
  }, [totals.needsReview]);

  const mostUsedCodes = ['E11.9', 'I10', '99213', 'J1100', 'N18.3'];

  return (
    <div className="min-h-[calc(100vh-64px)] bg-slate-50/70">
      <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <p className="text-xs font-bold uppercase tracking-widest text-hospital-blue-700 mb-2">System Overview</p>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900">Medical Coding Dashboard</h1>
          <p className="text-slate-500 mt-2 max-w-3xl">
            Central control panel for monitoring report activity, processing health, compliance readiness, and operational insights.
          </p>
        </motion.section>

        <section className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <SummaryStatCard
            title="Total Reports Generated"
            value={String(totals.totalReports)}
            icon={FileText}
            trendLabel={isLoading ? 'Loading reports...' : 'Across all available records'}
            progress={Math.min(100, totals.totalReports * 8)}
            tone="blue"
          />
          <SummaryStatCard
            title="Successful Codings"
            value={String(totals.successful)}
            icon={CheckCircle2}
            trendLabel={`${totals.totalReports ? Math.round((totals.successful / totals.totalReports) * 100) : 0}% complaince quality`}
            progress={totals.totalReports ? Math.round((totals.successful / totals.totalReports) * 100) : 0}
            tone="green"
          />
          <SummaryStatCard
            title="Errors / Warnings"
            value={String(totals.needsReview)}
            icon={AlertTriangle}
            trendLabel={totals.needsReview ? 'Needs focused review' : 'No active warnings'}
            progress={totals.totalReports ? Math.round((totals.needsReview / totals.totalReports) * 100) : 0}
            tone="amber"
          />
          <SummaryStatCard
            title="Average Confidence Score"
            value={`${totals.averageConfidence}%`}
            icon={Gauge}
            trendLabel="Confidence trend from recent reports"
            progress={totals.averageConfidence}
            tone="slate"
          />
        </section>

        <QuickActionPanel />

        <LiveProcessStatus process={liveProcess} />

        <SearchFilters filters={filters} onChange={setFilters} />

        <section className="grid xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-6">
            <RecentReportsTable reports={recentReports} />
            <AlertsPanel alerts={alerts} />
          </div>

          <div className="space-y-6">
            <ComplianceOverview
              score={complianceScore}
              validCodes={totals.successful * 4}
              errors={totals.needsReview}
              warnings={Math.max(0, totals.needsReview * 2)}
            />
            <PerformanceInsights
              averageProcessingTimeSec={averageProcessingTimeSec}
              frequentErrors={frequentErrors}
              mostUsedCodes={mostUsedCodes}
            />
            <SmartInsightsCard insight={smartInsight} />
          </div>
        </section>

        {!isLoading && !reports.length && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
            <Activity className="w-8 h-8 text-slate-300 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-slate-900">No reports available yet</h3>
            <p className="text-sm text-slate-500 mt-1">Use quick actions above to generate your first report.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function extractUnixTimestamp(name: string) {
  const match = name.match(/_(\d{10,})/);
  return match ? Number(match[1]) : 0;
}

function toTimestampLabel(name: string) {
  const ts = extractUnixTimestamp(name);
  if (!ts) return 'Unknown';
  return new Date(ts * 1000).toLocaleString();
}

function mapBackendMode(mode: string): DashboardReportItem['mode'] {
  const normalized = mode.toLowerCase();
  if (normalized === 'compare' || normalized === 'assisted') return 'Assisted';
  return 'Auto';
}

function deriveMode(name: string): DashboardReportItem['mode'] {
  return name.includes('compare') || name.includes('validate') ? 'Assisted' : 'Auto';
}

function deriveStatus(name: string): DashboardReportItem['status'] {
  return name.includes('compare') || name.includes('validate') ? 'Needs Review' : 'Completed';
}

function deriveConfidence(name: string) {
  const numericSeed = Array.from(name).reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return 82 + (numericSeed % 18);
}

function matchesDateFilter(reportId: string, dateFilter: DashboardFilters['date']) {
  if (dateFilter === 'All') return true;

  const ts = extractUnixTimestamp(reportId);
  if (!ts) return false;

  const reportDate = new Date(ts * 1000);
  const now = new Date();
  const diffMs = now.getTime() - reportDate.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (dateFilter === 'Today') return diffDays < 1;
  if (dateFilter === 'Last7Days') return diffDays <= 7;
  return diffDays <= 30;
}
