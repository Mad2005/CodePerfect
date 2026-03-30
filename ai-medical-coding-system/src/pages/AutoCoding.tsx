import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Upload, 
  FileText, 
  Send, 
  AlertCircle, 
  X, 
  FileSpreadsheet,
  FileJson,
  Info,
  Sparkles,
  ArrowRight,
  Activity,
  FileType,
  Loader2,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import ProcessingPanel from '@/components/ProcessingPanel';
import { ReportView } from './Report';
import { ProcessingStep } from '@/types';
import { cn } from '@/lib/utils';

const AUTO_PIPELINE_STEPS = [
  'Clinical Note Received',
  'Text Processing',
  'Clinical Language Understanding',
  'Diagnosis Mapping',
  'Medication Mapping',
  'Knowledge Retrieval',
  'Code Generation',
  'Multi-Agent Debate',
  'Compliance Validation',
  'Audit',
  'Justification Generation',
  'Confidence Scoring',
  'Report Generation',
];

export default function AutoCoding() {
  const navigate = useNavigate();
  const [inputMode, setInputMode] = useState<'typed' | 'file'>('typed');
  const [typedClinicalNote, setTypedClinicalNote] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [uploadedFileType, setUploadedFileType] = useState<'txt' | 'pdf' | 'docx' | 'doc' | 'unknown'>('unknown');
  const [extractedClinicalNote, setExtractedClinicalNote] = useState('');
  const [noteUploadStatus, setNoteUploadStatus] = useState<'idle' | 'uploading' | 'processing' | 'complete' | 'error'>('idle');
  const [noteUploadMessage, setNoteUploadMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [reportData, setReportData] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pipelineTimerRef = useRef<number | null>(null);

  const steps: ProcessingStep[] = AUTO_PIPELINE_STEPS.map((label, id) => ({
    id,
    label,
    status: 'pending',
  }));

  const [activeSteps, setActiveSteps] = useState<ProcessingStep[]>(steps);

  const activeClinicalNote = inputMode === 'typed' ? typedClinicalNote : extractedClinicalNote;

  const getFileType = (name: string): 'txt' | 'pdf' | 'docx' | 'doc' | 'unknown' => {
    const ext = name.split('.').pop()?.toLowerCase();
    if (ext === 'txt') return 'txt';
    if (ext === 'pdf') return 'pdf';
    if (ext === 'docx') return 'docx';
    if (ext === 'doc') return 'doc';
    return 'unknown';
  };

  const getFileIcon = () => {
    if (uploadedFileType === 'pdf') return <FileJson className="w-4 h-4 text-red-600" />;
    if (uploadedFileType === 'txt') return <FileText className="w-4 h-4 text-hospital-blue-600" />;
    if (uploadedFileType === 'docx' || uploadedFileType === 'doc') return <FileType className="w-4 h-4 text-indigo-600" />;
    return <FileText className="w-4 h-4 text-slate-500" />;
  };

  const resetUploadedFile = () => {
    setUploadedFileName('');
    setUploadedFileType('unknown');
    setExtractedClinicalNote('');
    setNoteUploadStatus('idle');
    setNoteUploadMessage('');
  };

  const processClinicalNoteFile = async (file: File) => {
    const allowedTypes = ['txt', 'pdf', 'docx', 'doc'];
    const fileType = getFileType(file.name);

    if (!allowedTypes.includes(fileType)) {
      setNoteUploadStatus('error');
      setNoteUploadMessage('Unsupported file format. Use .txt, .pdf, .docx, or .doc.');
      return;
    }

    setInputMode('file');
    setUploadedFileName(file.name);
    setUploadedFileType(fileType);
    setExtractedClinicalNote('');
    setNoteUploadStatus('uploading');
    setNoteUploadMessage('Uploading...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      setNoteUploadStatus('processing');
      setNoteUploadMessage('Processing file...');

      const response = await fetch('/api/extract-note-file', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.status !== 'ok') {
        throw new Error(data.message || 'Could not extract text from file.');
      }

      const normalized = normalizeExtractedText(data.extracted_text || '');
      if (!normalized.trim()) {
        throw new Error('No usable clinical note text found after extraction.');
      }

      setExtractedClinicalNote(normalized);
      setNoteUploadStatus('complete');
      setNoteUploadMessage('Extraction complete');
    } catch (error: any) {
      setNoteUploadStatus('error');
      setNoteUploadMessage(error.message || 'Failed to process file.');
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement> | React.DragEvent) => {
    let file: File | undefined;

    if ('files' in e.target && e.target.files) {
      file = e.target.files[0];
    } else if ('dataTransfer' in e && e.dataTransfer.files) {
      file = e.dataTransfer.files[0];
    }

    if (file) {
      processClinicalNoteFile(file);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileUpload(e);
  };

  const simulateProcessing = async () => {
    if (!activeClinicalNote.trim()) return;

    setIsProcessing(true);

    const updatePipelineState = (activeIndex: number | null, completeAll = false) => {
      setActiveSteps(
        steps.map((step, index) => ({
          ...step,
          status: completeAll || (activeIndex !== null && index < activeIndex)
            ? 'completed'
            : activeIndex === index
            ? 'processing'
            : 'pending',
        }))
      );
    };

    const clearPipelineTimer = () => {
      if (pipelineTimerRef.current !== null) {
        window.clearInterval(pipelineTimerRef.current);
        pipelineTimerRef.current = null;
      }
    };

    try {
      let animatedStepIndex = 0;
      setCurrentStep(animatedStepIndex);
      updatePipelineState(animatedStepIndex);

      pipelineTimerRef.current = window.setInterval(() => {
        animatedStepIndex = Math.min(animatedStepIndex + 1, steps.length - 1);
        setCurrentStep(animatedStepIndex);
        updatePipelineState(animatedStepIndex);
      }, 900);

      const response = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ clinical_note: activeClinicalNote }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'API request failed');
      }

      const data = await response.json();

      clearPipelineTimer();
      setCurrentStep(steps.length - 1);
      updatePipelineState(null, true);
      
      // Show report inline
      setTimeout(() => {
        setIsProcessing(false);
        setReportData(data);
        setCurrentStep(0);
      }, 800);
      
    } catch (err: any) {
      clearPipelineTimer();
      setCurrentStep(0);
      updatePipelineState(null);
      console.error('Processing error:', err);
      alert('Error during processing: ' + err.message);
      setIsProcessing(false);
    }
  };

  if (reportData) {
    return <ReportView apiData={reportData} onBack={() => setReportData(null)} />;
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-10 flex items-end justify-between"
      >
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="p-2 bg-hospital-blue-100 rounded-lg">
              <Sparkles className="w-5 h-5 text-hospital-blue-600" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900">Auto Coding Mode</h1>
          </div>
          <p className="text-slate-500">Fully automated clinical language understanding and code generation.</p>
        </div>
        <div className="hidden lg:flex items-center gap-4 text-xs font-medium text-slate-400">
          <div className="flex items-center gap-1">
            <FileText className="w-3 h-3" /> TXT
          </div>
          <div className="flex items-center gap-1">
            <FileType className="w-3 h-3" /> DOCX
          </div>
          <div className="flex items-center gap-1">
            <FileJson className="w-3 h-3" /> PDF
          </div>
        </div>
      </motion.div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 bg-slate-50/50 space-y-4">
              <div className="flex items-center gap-2 text-slate-700 font-semibold">
                <FileText className="w-5 h-5 text-hospital-blue-600" />
                Clinical Note Input
              </div>

              <div className="inline-flex rounded-xl border border-slate-200 bg-white p-1">
                <button
                  onClick={() => setInputMode('typed')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    inputMode === 'typed' ? 'bg-hospital-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'
                  }`}
                >
                  Typing Mode
                </button>
                <button
                  onClick={() => setInputMode('file')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    inputMode === 'file' ? 'bg-hospital-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'
                  }`}
                >
                  File Upload Mode
                </button>
              </div>
            </div>

            {inputMode === 'typed' ? (
              <div className="p-6">
                <textarea
                  value={typedClinicalNote}
                  onChange={(e) => setTypedClinicalNote(e.target.value)}
                  placeholder="Type clinical notes here..."
                  className="w-full h-[320px] p-4 rounded-xl border border-slate-200 focus:border-hospital-blue-400 outline-none resize-none text-slate-700 leading-relaxed bg-white"
                />
              </div>
            ) : (
              <div className="p-6 space-y-4">
                <div
                  onDragOver={onDragOver}
                  onDragLeave={onDragLeave}
                  onDrop={onDrop}
                  className={cn(
                    "rounded-xl border-2 border-dashed p-8 text-center transition-all",
                    isDragging ? "border-hospital-blue-500 bg-hospital-blue-50" : "border-slate-200 bg-slate-50"
                  )}
                >
                  <Upload className="w-8 h-8 mx-auto mb-3 text-slate-400" />
                  <p className="text-sm font-semibold text-slate-700">Drag and drop clinical note file</p>
                  <p className="text-xs text-slate-500 mt-1">Supported: .txt, .pdf, .docx</p>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="mt-4 px-4 py-2 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-700 hover:bg-slate-50"
                  >
                    Browse File
                  </button>
                </div>

                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                  accept=".txt,.pdf,.docx,.doc"
                />

                {uploadedFileName && (
                  <div className="rounded-xl border border-slate-200 p-4 bg-white">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                        {getFileIcon()}
                        Uploaded File: {uploadedFileName}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => fileInputRef.current?.click()}
                          className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 flex items-center gap-1"
                        >
                          <RefreshCw className="w-3 h-3" /> Replace
                        </button>
                        <button
                          onClick={resetUploadedFile}
                          className="px-3 py-1.5 rounded-lg border border-red-100 bg-red-50 text-xs font-bold text-red-700 hover:bg-red-100 flex items-center gap-1"
                        >
                          <X className="w-3 h-3" /> Remove
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 text-xs font-semibold flex items-center gap-2">
                      {noteUploadStatus === 'uploading' || noteUploadStatus === 'processing' ? (
                        <Loader2 className="w-4 h-4 text-hospital-blue-600 animate-spin" />
                      ) : noteUploadStatus === 'complete' ? (
                        <CheckCircle2 className="w-4 h-4 text-green-600" />
                      ) : noteUploadStatus === 'error' ? (
                        <AlertCircle className="w-4 h-4 text-red-600" />
                      ) : (
                        <Info className="w-4 h-4 text-slate-400" />
                      )}
                      <span className={noteUploadStatus === 'error' ? 'text-red-700' : 'text-slate-600'}>
                        {noteUploadMessage || 'Waiting for upload'}
                      </span>
                    </div>
                  </div>
                )}

                <AnimatePresence>
                  {extractedClinicalNote && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                    >
                      <p className="text-xs uppercase tracking-widest font-bold text-slate-400 mb-3">Uploaded File Preview</p>
                      <FormattedClinicalNotePreview note={extractedClinicalNote} />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <Info className="w-4 h-4" />
              Processing is compliant with HIPAA standards.
            </div>
            <button
              onClick={simulateProcessing}
              disabled={!activeClinicalNote.trim() || isProcessing || (inputMode === 'file' && noteUploadStatus !== 'complete')}
              className="group px-10 py-4 bg-hospital-blue-600 text-white font-bold rounded-xl hover:bg-hospital-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 shadow-xl shadow-hospital-blue-100 active:scale-95"
            >
              <Send className="w-4 h-4 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
              Generate Codes
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-hospital-blue-600" />
              Instructions
            </h3>
            <ul className="space-y-4 text-sm text-slate-600">
              <li className="flex gap-3">
                <div className="w-5 h-5 rounded-full bg-hospital-blue-50 text-hospital-blue-600 flex-shrink-0 flex items-center justify-center text-[10px] font-bold">1</div>
                Paste or upload clinical documentation including history, physical, and assessment.
              </li>
              <li className="flex gap-3">
                <div className="w-5 h-5 rounded-full bg-hospital-blue-50 text-hospital-blue-600 flex-shrink-0 flex items-center justify-center text-[10px] font-bold">2</div>
                The system will automatically identify diagnoses, procedures, and supplies.
              </li>
              <li className="flex gap-3">
                <div className="w-5 h-5 rounded-full bg-hospital-blue-50 text-hospital-blue-600 flex-shrink-0 flex items-center justify-center text-[10px] font-bold">3</div>
                Review the generated ICD-10, CPT, and HCPCS codes in the final report.
              </li>
            </ul>
          </div>

          <div className="bg-slate-900 rounded-2xl p-6 text-white overflow-hidden relative">
            <div className="relative z-10">
              <h3 className="font-bold text-lg mb-2">System Status</h3>
              <div className="flex items-center gap-2 text-green-400 text-sm mb-4">
                <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                All engines operational
              </div>
              <div className="space-y-3">
                <StatusItem label="Language Engine" status="Optimal" />
                <StatusItem label="Compliance Rules" status="Updated" />
                <StatusItem label="Mapping Accuracy" status="99.2%" />
              </div>
            </div>
            <Activity className="absolute -right-4 -bottom-4 w-32 h-32 text-white/5" />
          </div>
        </div>
      </div>

      {isProcessing && (
        <ProcessingPanel steps={activeSteps} currentStepId={currentStep} />
      )}
    </div>
  );
}

function StatusItem({ label, status }: { label: string, status: string }) {
  return (
    <div className="flex justify-between items-center text-xs">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono font-bold">{status}</span>
    </div>
  );
}

function normalizeExtractedText(input: string) {
  return input
    .replace(/\r/g, '\n')
    .replace(/\t/g, ' ')
    .replace(/[ ]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join('\n');
}

function FormattedClinicalNotePreview({ note }: { note: string }) {
  const sections = parseClinicaNote(note);
  
  return (
    <div className="text-sm text-slate-700 space-y-3 max-h-64 overflow-y-auto">
      {sections.map((section, idx) => (
        <div key={idx}>
          {section.title && (
            <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wide text-hospital-blue-700 mb-1">
              {section.title}
            </h4>
          )}
          <div className="text-slate-700 leading-relaxed whitespace-pre-wrap text-xs">
            {section.content}
          </div>
        </div>
      ))}
    </div>
  );
}

function parseClinicaNote(text: string): Array<{ title?: string; content: string }> {
  const lines = text.split('\n');
  const sections: Array<{ title?: string; content: string }> = [];
  let currentSection: { title?: string; lines: string[] } = { lines: [] };
  
  const sectionKeywords = [
    'patient', 'name', 'age', 'chief complaint', 'history',
    'examination', 'exam', 'vital', 'diagnosis', 'procedure',
    'medication', 'assessment', 'plan', 'impression', 'note'
  ];
  
  for (const line of lines) {
    const lowerLine = line.toLowerCase();
    const isSectionHeader = sectionKeywords.some(kw => 
      lowerLine.startsWith(kw) && (lowerLine.includes(':') || line.endsWith('.'))
    );
    
    if (isSectionHeader && currentSection.lines.length > 0) {
      sections.push({
        title: currentSection.title,
        content: currentSection.lines.join('\n').trim()
      });
      currentSection = { title: line.replace(':', '').trim(), lines: [] };
    } else if (isSectionHeader) {
      currentSection.title = line.replace(':', '').trim();
    } else if (line.trim()) {
      currentSection.lines.push(line);
    }
  }
  
  if (currentSection.lines.length > 0 || currentSection.title) {
    sections.push({
      title: currentSection.title,
      content: currentSection.lines.join('\n').trim()
    });
  }
  
  return sections.length > 0 ? sections : [{ content: text }];
}
