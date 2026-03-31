import { motion } from 'motion/react';
import { LucideIcon } from 'lucide-react';

interface SummaryStatCardProps {
  title: string;
  value: string;
  icon: LucideIcon;
  trendLabel: string;
  progress: number;
  tone: 'blue' | 'green' | 'amber' | 'slate';
}

const toneClasses = {
  blue: {
    iconBg: 'bg-hospital-blue-50',
    iconText: 'text-hospital-blue-600',
    trend: 'text-hospital-blue-700',
    progress: 'bg-hospital-blue-600',
  },
  green: {
    iconBg: 'bg-green-50',
    iconText: 'text-green-600',
    trend: 'text-green-700',
    progress: 'bg-green-600',
  },
  amber: {
    iconBg: 'bg-amber-50',
    iconText: 'text-amber-600',
    trend: 'text-amber-700',
    progress: 'bg-amber-600',
  },
  slate: {
    iconBg: 'bg-slate-100',
    iconText: 'text-slate-700',
    trend: 'text-slate-700',
    progress: 'bg-slate-700',
  },
};

export default function SummaryStatCard({
  title,
  value,
  icon: Icon,
  trendLabel,
  progress,
  tone,
}: SummaryStatCardProps) {
  const palette = toneClasses[tone];

  return (
    <motion.div
      whileHover={{ y: -4 }}
      className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm hover:shadow-lg transition-all"
    >
      <div className="flex items-start justify-between mb-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400">{title}</p>
          <h3 className="text-3xl font-black text-slate-900 mt-2">{value}</h3>
        </div>
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${palette.iconBg}`}>
          <Icon className={`w-6 h-6 ${palette.iconText}`} />
        </div>
      </div>

      <div className="space-y-2">
        <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
          <div
            className={`h-full rounded-full ${palette.progress}`}
            style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }}
          />
        </div>
        <p className={`text-xs font-semibold ${palette.trend}`}>{trendLabel}</p>
      </div>
    </motion.div>
  );
}
