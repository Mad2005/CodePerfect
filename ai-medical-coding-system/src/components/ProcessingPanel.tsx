import { motion } from 'motion/react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';
import { ProcessingStep } from '@/types';

interface ProcessingPanelProps {
  steps: ProcessingStep[];
  currentStepId: number;
}

export default function ProcessingPanel({ steps, currentStepId }: ProcessingPanelProps) {
  const safeCurrentStep = Math.min(currentStepId + 1, steps.length);
  const completedCount = steps.filter((step) => step.status === 'completed').length;
  const processingStep = steps.find((step) => step.status === 'processing');
  const progressPercent = steps.length ? Math.round((completedCount / steps.length) * 100) : 0;

  let stageMessage = 'Initializing pipeline...';
  if (processingStep) {
    stageMessage = `Running: ${processingStep.label}`;
  } else if (completedCount === steps.length && steps.length > 0) {
    stageMessage = 'Completed: Preparing final report output...';
  }

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-2xl max-w-xl w-full p-8 border border-slate-100"
      >
        <div className="text-center mb-8">
          <h3 className="text-2xl font-bold text-slate-900 mb-2">Processing Report</h3>
          <p className="text-slate-500 text-sm">Our AI system is analyzing the clinical data...</p>
          <p className="text-xs text-slate-400 mt-2">
            Step {safeCurrentStep} of {steps.length}
          </p>
          <p className="text-sm font-semibold text-hospital-blue-700 mt-3">{stageMessage}</p>
          <div className="w-full h-2 bg-slate-100 rounded-full mt-4 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
              className="h-full bg-hospital-blue-600 rounded-full"
            />
          </div>
        </div>

        <div className="space-y-4 max-h-[55vh] overflow-y-auto pr-1">
          {steps.map((step) => (
            <div key={step.id} className="flex items-center gap-4">
              <div className="flex-shrink-0">
                {step.status === 'completed' ? (
                  <CheckCircle2 className="w-6 h-6 text-green-500" />
                ) : step.status === 'processing' ? (
                  <Loader2 className="w-6 h-6 text-hospital-blue-600 animate-spin" />
                ) : (
                  <Circle className="w-6 h-6 text-slate-300" />
                )}
              </div>
              <div className="flex-grow">
                <p
                  className={`text-sm font-medium ${
                    step.status === 'processing'
                      ? 'text-hospital-blue-700'
                      : step.status === 'completed'
                      ? 'text-slate-900'
                      : 'text-slate-400'
                  }`}
                >
                  {step.label}
                </p>
                {step.status === 'processing' && (
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="h-1 bg-hospital-blue-100 rounded-full mt-2 overflow-hidden"
                  >
                    <div className="h-full bg-hospital-blue-600 w-1/3 rounded-full" />
                  </motion.div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 pt-6 border-t border-slate-100 text-center">
          <p className="text-xs text-slate-400 italic">
            This process typically takes a few seconds depending on document length and complexity.
          </p>
        </div>
      </motion.div>
    </div>
  );
}
