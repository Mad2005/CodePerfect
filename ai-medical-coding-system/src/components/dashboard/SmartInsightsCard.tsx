import { Lightbulb } from 'lucide-react';

export default function SmartInsightsCard({ insight }: { insight: string }) {
  return (
    <div className="bg-gradient-to-r from-hospital-blue-600 to-hospital-blue-700 text-white rounded-2xl p-5 shadow-lg">
      <div className="flex items-center gap-2 mb-2">
        <Lightbulb className="w-5 h-5" />
        <h2 className="text-lg font-black">Smart Insights</h2>
      </div>
      <p className="text-sm leading-relaxed text-hospital-blue-50">{insight}</p>
    </div>
  );
}
