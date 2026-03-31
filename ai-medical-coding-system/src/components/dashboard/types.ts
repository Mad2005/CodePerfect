export type ReportMode = 'Auto' | 'Assisted';

export type ReportStatus = 'Completed' | 'Needs Review';

export interface DashboardReportItem {
  id: string;
  mode: ReportMode;
  timestamp: string;
  status: ReportStatus;
  confidence: number;
}

export interface DashboardFilters {
  search: string;
  mode: 'All' | ReportMode;
  date: 'All' | 'Today' | 'Last7Days' | 'Last30Days';
}

export interface LiveProcessState {
  currentStep: string;
  message: string;
  progress: number;
  steps: Array<{
    id: number;
    label: string;
    status: 'pending' | 'processing' | 'completed';
  }>;
}
