import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Upload, 
  FileText, 
  Send, 
  AlertCircle, 
  Hash, 
  CheckCircle, 
  FileSpreadsheet,
  Info,
  UserCheck,
  Zap,
  ArrowRight,
  X,
  Loader2,
  FileJson,
  FileType,
  RefreshCw,
  Plus,
  Trash2
} from 'lucide-react';
import ProcessingPanel from '@/components/ProcessingPanel';
import { ReportView } from './Report';
import { ProcessingStep } from '@/types';
import { cn } from '@/lib/utils';

const ASSISTED_PIPELINE_STEPS = [
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
  'Comparison',
  'Justification Generation',
  'Confidence Scoring',
  'Report Generation',
];

export default function AssistedCoding() {
  const navigate = useNavigate();
  const [noteInputMode, setNoteInputMode] = useState<'typed' | 'file'>('typed');
  const [typedClinicalNote, setTypedClinicalNote] = useState('');
  const [uploadedNoteFileName, setUploadedNoteFileName] = useState('');
  const [uploadedNoteFileType, setUploadedNoteFileType] = useState<'txt' | 'pdf' | 'docx' | 'doc' | 'unknown'>('unknown');
  const [extractedClinicalNote, setExtractedClinicalNote] = useState('');
  const [noteUploadStatus, setNoteUploadStatus] = useState<'idle' | 'uploading' | 'processing' | 'complete' | 'error'>('idle');
  const [noteUploadMessage, setNoteUploadMessage] = useState('');

  const [humanCodeMode, setHumanCodeMode] = useState<'manual' | 'file'>('manual');
  
  // Manual code input state for each code type
  const [manualIcd10Codes, setManualIcd10Codes] = useState<string[]>([]);
  const [manualCptCodes, setManualCptCodes] = useState<string[]>([]);
  const [manualHcpcsCodes, setManualHcpcsCodes] = useState<string[]>([]);
  
  // Temporary input values for new codes
  const [icd10Input, setIcd10Input] = useState('');
  const [cptInput, setCptInput] = useState('');
  const [hcpcsInput, setHcpcsInput] = useState('');
  
  const [uploadedCodesFileName, setUploadedCodesFileName] = useState('');
  const [codesUploadStatus, setCodesUploadStatus] = useState<'idle' | 'uploading' | 'processing' | 'complete' | 'error'>('idle');
  const [codesUploadMessage, setCodesUploadMessage] = useState('');
  const [parsedCodes, setParsedCodes] = useState<{ icd10: any[]; cpt: any[]; hcpcs: any[] }>({
    icd10: [],
    cpt: [],
    hcpcs: [],
  });

  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isCodesDragging, setIsCodesDragging] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [reportData, setReportData] = useState<any>(null);
  const noteFileInputRef = useRef<HTMLInputElement>(null);
  const codesFileInputRef = useRef<HTMLInputElement>(null);
  const pipelineTimerRef = useRef<number | null>(null);

  const steps: ProcessingStep[] = ASSISTED_PIPELINE_STEPS.map((label, id) => ({
    id,
    label,
    status: 'pending',
  }));

  const [activeSteps, setActiveSteps] = useState<ProcessingStep[]>(steps);

  const activeClinicalNote = noteInputMode === 'typed' ? typedClinicalNote : extractedClinicalNote;

  const getFileType = (name: string): 'txt' | 'pdf' | 'docx' | 'doc' | 'unknown' => {
    const ext = name.split('.').pop()?.toLowerCase();
    if (ext === 'txt') return 'txt';
    if (ext === 'pdf') return 'pdf';
    if (ext === 'docx') return 'docx';
    if (ext === 'doc') return 'doc';
    return 'unknown';
  };

  const noteFileIcon = () => {
    if (uploadedNoteFileType === 'pdf') return <FileJson className="w-4 h-4 text-red-600" />;
    if (uploadedNoteFileType === 'txt') return <FileText className="w-4 h-4 text-hospital-blue-600" />;
    if (uploadedNoteFileType === 'docx' || uploadedNoteFileType === 'doc') return <FileType className="w-4 h-4 text-indigo-600" />;
    return <FileText className="w-4 h-4 text-slate-500" />;
  };

  const manualCodesList = [
    ...manualIcd10Codes,
    ...manualCptCodes,
    ...manualHcpcsCodes,
  ].filter(Boolean);

  const uploadedCodesList = [
    ...parsedCodes.icd10.map((c) => c.code),
    ...parsedCodes.cpt.map((c) => c.code),
    ...parsedCodes.hcpcs.map((c) => c.code),
  ].filter(Boolean);

  const activeHumanCodes = Array.from(new Set(humanCodeMode === 'manual' ? manualCodesList : uploadedCodesList));

  const handleNoteFileUpload = (e: React.ChangeEvent<HTMLInputElement> | React.DragEvent) => {
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

  const processClinicalNoteFile = async (file: File) => {
    const allowedTypes = ['txt', 'pdf', 'docx', 'doc'];
    const fileType = getFileType(file.name);

    if (!allowedTypes.includes(fileType)) {
      setNoteUploadStatus('error');
      setNoteUploadMessage('Unsupported file format. Use .txt, .pdf, .docx, or .doc.');
      return;
    }

    setNoteInputMode('file');
    setUploadedNoteFileName(file.name);
    setUploadedNoteFileType(fileType);
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

  const resetNoteFile = () => {
    setUploadedNoteFileName('');
    setUploadedNoteFileType('unknown');
    setExtractedClinicalNote('');
    setNoteUploadStatus('idle');
    setNoteUploadMessage('');
  };

  const handleCodesFileUpload = (e: React.ChangeEvent<HTMLInputElement> | React.DragEvent) => {
    let file: File | undefined;
    if ('files' in e.target && e.target.files) {
      file = e.target.files[0];
    } else if ('dataTransfer' in e && e.dataTransfer.files) {
      file = e.dataTransfer.files[0];
    }
    if (file) {
      processCodesFile(file);
    }
  };

  const processCodesFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !['txt', 'csv'].includes(ext)) {
      setCodesUploadStatus('error');
      setCodesUploadMessage('Unsupported code file format. Use .txt or .csv.');
      return;
    }

    setHumanCodeMode('file');
    setUploadedCodesFileName(file.name);
    setCodesUploadStatus('uploading');
    setCodesUploadMessage('Uploading...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      setCodesUploadStatus('processing');
      setCodesUploadMessage('Processing file...');

      const response = await fetch('/api/parse-codes', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.message || data.error || 'Unable to parse code file.');
      }

      setParsedCodes({
        icd10: data.icd10 || [],
        cpt: data.cpt || [],
        hcpcs: data.hcpcs || [],
      });
      setCodesUploadStatus('complete');
      setCodesUploadMessage('Extraction complete');
    } catch (error: any) {
      setCodesUploadStatus('error');
      setCodesUploadMessage(error.message || 'Could not parse file.');
      setParsedCodes({ icd10: [], cpt: [], hcpcs: [] });
    }
  };

  const resetCodesFile = () => {
    setUploadedCodesFileName('');
    setParsedCodes({ icd10: [], cpt: [], hcpcs: [] });
    setCodesUploadStatus('idle');
    setCodesUploadMessage('');
  };

  // Manual code handlers
  const addIcd10Code = () => {
    if (icd10Input.trim()) {
      setManualIcd10Codes([...manualIcd10Codes, icd10Input.trim().toUpperCase()]);
      setIcd10Input('');
    }
  };

  const addCptCode = () => {
    if (cptInput.trim()) {
      setManualCptCodes([...manualCptCodes, cptInput.trim().toUpperCase()]);
      setCptInput('');
    }
  };

  const addHcpcsCode = () => {
    if (hcpcsInput.trim()) {
      setManualHcpcsCodes([...manualHcpcsCodes, hcpcsInput.trim().toUpperCase()]);
      setHcpcsInput('');
    }
  };

  const removeIcd10Code = (index: number) => {
    setManualIcd10Codes(manualIcd10Codes.filter((_, i) => i !== index));
  };

  const removeCptCode = (index: number) => {
    setManualCptCodes(manualCptCodes.filter((_, i) => i !== index));
  };

  const removeHcpcsCode = (index: number) => {
    setManualHcpcsCodes(manualHcpcsCodes.filter((_, i) => i !== index));
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
    handleNoteFileUpload(e);
  };

  const onCodesDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsCodesDragging(true);
  };

  const onCodesDragLeave = () => {
    setIsCodesDragging(false);
  };

  const onCodesDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsCodesDragging(false);
    handleCodesFileUpload(e);
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

      const codesList = activeHumanCodes;

      const response = await fetch('/api/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          clinical_note: activeClinicalNote,
          human_codes: codesList
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'API request failed');
      }

      const data = await response.json();

      clearPipelineTimer();
      setCurrentStep(steps.length - 1);
      updatePipelineState(null, true);
      
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
        className="mb-10"
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="p-2 bg-hospital-blue-100 rounded-lg">
            <UserCheck className="w-5 h-5 text-hospital-blue-600" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Assisted Coding Mode</h1>
        </div>
        <p className="text-slate-500">Validate your own codes and get AI-powered enhancement suggestions.</p>
      </motion.div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {/* Clinical Notes Input */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-100 bg-slate-50/50 space-y-4">
              <div className="flex items-center gap-2 text-slate-700 font-semibold">
                <FileText className="w-5 h-5 text-hospital-blue-600" />
                Clinical Note Input
              </div>

              <div className="inline-flex rounded-xl border border-slate-200 bg-white p-1">
                <button
                  onClick={() => setNoteInputMode('typed')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    noteInputMode === 'typed' ? 'bg-hospital-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'
                  }`}
                >
                  Typing Mode
                </button>
                <button
                  onClick={() => setNoteInputMode('file')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    noteInputMode === 'file' ? 'bg-hospital-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'
                  }`}
                >
                  File Upload Mode
                </button>
              </div>
            </div>

            {noteInputMode === 'typed' ? (
              <div className="p-6">
                <textarea
                  value={typedClinicalNote}
                  onChange={(e) => setTypedClinicalNote(e.target.value)}
                  placeholder="Type clinical notes here..."
                  className="w-full h-64 p-4 rounded-xl border border-slate-200 focus:border-hospital-blue-400 outline-none resize-none text-slate-700 leading-relaxed bg-white"
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
                    onClick={() => noteFileInputRef.current?.click()}
                    className="mt-4 px-4 py-2 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-700 hover:bg-slate-50"
                  >
                    Browse File
                  </button>
                </div>

                <input
                  type="file"
                  ref={noteFileInputRef}
                  onChange={handleNoteFileUpload}
                  className="hidden"
                  accept=".txt,.pdf,.docx,.doc"
                />

                {uploadedNoteFileName && (
                  <div className="rounded-xl border border-slate-200 p-4 bg-white">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                        {noteFileIcon()}
                        Uploaded File: {uploadedNoteFileName}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => noteFileInputRef.current?.click()}
                          className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 flex items-center gap-1"
                        >
                          <RefreshCw className="w-3 h-3" /> Replace
                        </button>
                        <button
                          onClick={resetNoteFile}
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
                        <CheckCircle className="w-4 h-4 text-green-600" />
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

          {/* Human Code Input */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden group focus-within:ring-2 focus-within:ring-hospital-blue-500 transition-all">
            <div className="p-6 border-b border-slate-100 bg-slate-50/50">
              <div className="flex items-center gap-2 text-slate-700 font-semibold">
                <Hash className="w-5 h-5 text-hospital-blue-600" />
                Your Initial Codes
              </div>

              <div className="inline-flex mt-3 rounded-xl border border-slate-200 bg-white p-1">
                <button
                  onClick={() => setHumanCodeMode('manual')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    humanCodeMode === 'manual' ? 'bg-hospital-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'
                  }`}
                >
                  Manual Input
                </button>
                <button
                  onClick={() => setHumanCodeMode('file')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    humanCodeMode === 'file' ? 'bg-hospital-blue-600 text-white' : 'text-slate-500 hover:bg-slate-50'
                  }`}
                >
                  Upload TXT/CSV
                </button>
              </div>
            </div>
            <div className="p-6">
              {humanCodeMode === 'manual' ? (
                <div className="space-y-6">
                  {/* ICD-10 Section */}
                  <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                        <h3 className="font-semibold text-slate-900">ICD-10-CM Diagnosis Codes</h3>
                        <span className="ml-2 inline-block px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-semibold">
                          {manualIcd10Codes.length}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {/* Code Input */}
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={icd10Input}
                          onChange={(e) => setIcd10Input(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && addIcd10Code()}
                          placeholder="E.g., E11.9, I10"
                          className="flex-1 px-3 py-2 border border-slate-200 rounded-lg font-mono text-sm focus:border-hospital-blue-400 focus:outline-none"
                        />
                        <button
                          onClick={addIcd10Code}
                          className="px-4 py-2 bg-blue-500 text-white rounded-lg font-semibold text-sm hover:bg-blue-600 transition-all flex items-center gap-1"
                        >
                          <Plus className="w-4 h-4" /> Add
                        </button>
                      </div>

                      {/* Added Codes List */}
                      {manualIcd10Codes.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-200">
                          {manualIcd10Codes.map((code, idx) => (
                            <div
                              key={idx}
                              className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-blue-200 rounded-lg font-mono text-sm text-blue-700"
                            >
                              {code}
                              <button
                                onClick={() => removeIcd10Code(idx)}
                                className="text-blue-500 hover:text-blue-700 hover:bg-blue-50 p-0.5 rounded"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* CPT Section */}
                  <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                        <h3 className="font-semibold text-slate-900">CPT Procedure Codes</h3>
                        <span className="ml-2 inline-block px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-semibold">
                          {manualCptCodes.length}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {/* Code Input */}
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={cptInput}
                          onChange={(e) => setCptInput(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && addCptCode()}
                          placeholder="E.g., 99213, 71046"
                          className="flex-1 px-3 py-2 border border-slate-200 rounded-lg font-mono text-sm focus:border-hospital-blue-400 focus:outline-none"
                        />
                        <button
                          onClick={addCptCode}
                          className="px-4 py-2 bg-green-500 text-white rounded-lg font-semibold text-sm hover:bg-green-600 transition-all flex items-center gap-1"
                        >
                          <Plus className="w-4 h-4" /> Add
                        </button>
                      </div>

                      {/* Added Codes List */}
                      {manualCptCodes.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-200">
                          {manualCptCodes.map((code, idx) => (
                            <div
                              key={idx}
                              className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-green-200 rounded-lg font-mono text-sm text-green-700"
                            >
                              {code}
                              <button
                                onClick={() => removeCptCode(idx)}
                                className="text-green-500 hover:text-green-700 hover:bg-green-50 p-0.5 rounded"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* HCPCS Section */}
                  <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                        <h3 className="font-semibold text-slate-900">HCPCS Level II Codes</h3>
                        <span className="ml-2 inline-block px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-semibold">
                          {manualHcpcsCodes.length}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {/* Code Input */}
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={hcpcsInput}
                          onChange={(e) => setHcpcsInput(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && addHcpcsCode()}
                          placeholder="E.g., J1100, E1390"
                          className="flex-1 px-3 py-2 border border-slate-200 rounded-lg font-mono text-sm focus:border-hospital-blue-400 focus:outline-none"
                        />
                        <button
                          onClick={addHcpcsCode}
                          className="px-4 py-2 bg-purple-500 text-white rounded-lg font-semibold text-sm hover:bg-purple-600 transition-all flex items-center gap-1"
                        >
                          <Plus className="w-4 h-4" /> Add
                        </button>
                      </div>

                      {/* Added Codes List */}
                      {manualHcpcsCodes.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-200">
                          {manualHcpcsCodes.map((code, idx) => (
                            <div
                              key={idx}
                              className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-purple-200 rounded-lg font-mono text-sm text-purple-700"
                            >
                              {code}
                              <button
                                onClick={() => removeHcpcsCode(idx)}
                                className="text-purple-500 hover:text-purple-700 hover:bg-purple-50 p-0.5 rounded"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div
                    onDragOver={onCodesDragOver}
                    onDragLeave={onCodesDragLeave}
                    onDrop={onCodesDrop}
                    className={cn(
                      "rounded-xl border-2 border-dashed p-6 text-center transition-all",
                      isCodesDragging ? "border-hospital-blue-500 bg-hospital-blue-50" : "border-slate-200 bg-slate-50"
                    )}
                  >
                    <FileSpreadsheet className="w-7 h-7 mx-auto mb-2 text-slate-400" />
                    <p className="text-sm font-semibold text-slate-700">Drop TXT/CSV code file</p>
                    <p className="text-xs text-slate-500 mt-1">Supports code, description, type columns</p>
                    <button
                      onClick={() => codesFileInputRef.current?.click()}
                      className="mt-3 px-4 py-2 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-700 hover:bg-slate-50"
                    >
                      Browse Code File
                    </button>
                  </div>

                  <input
                    type="file"
                    ref={codesFileInputRef}
                    onChange={handleCodesFileUpload}
                    className="hidden"
                    accept=".txt,.csv"
                  />

                  {uploadedCodesFileName && (
                    <div className="rounded-xl border border-slate-200 p-4 bg-white">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                          <FileSpreadsheet className="w-4 h-4 text-hospital-blue-600" />
                          Uploaded File: {uploadedCodesFileName}
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => codesFileInputRef.current?.click()}
                            className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-bold text-slate-600 hover:bg-slate-50 flex items-center gap-1"
                          >
                            <RefreshCw className="w-3 h-3" /> Replace
                          </button>
                          <button
                            onClick={resetCodesFile}
                            className="px-3 py-1.5 rounded-lg border border-red-100 bg-red-50 text-xs font-bold text-red-700 hover:bg-red-100 flex items-center gap-1"
                          >
                            <X className="w-3 h-3" /> Remove
                          </button>
                        </div>
                      </div>

                      <div className="mt-3 text-xs font-semibold flex items-center gap-2">
                        {codesUploadStatus === 'uploading' || codesUploadStatus === 'processing' ? (
                          <Loader2 className="w-4 h-4 text-hospital-blue-600 animate-spin" />
                        ) : codesUploadStatus === 'complete' ? (
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        ) : codesUploadStatus === 'error' ? (
                          <AlertCircle className="w-4 h-4 text-red-600" />
                        ) : (
                          <Info className="w-4 h-4 text-slate-400" />
                        )}
                        <span className={codesUploadStatus === 'error' ? 'text-red-700' : 'text-slate-600'}>
                          {codesUploadMessage || 'Waiting for upload'}
                        </span>
                      </div>

                      {(parsedCodes.icd10.length > 0 || parsedCodes.cpt.length > 0 || parsedCodes.hcpcs.length > 0) && (
                        <div className="mt-4 grid md:grid-cols-3 gap-3 text-xs">
                          <CodeList title="ICD" codes={parsedCodes.icd10} />
                          <CodeList title="CPT" codes={parsedCodes.cpt} />
                          <CodeList title="HCPCS" codes={parsedCodes.hcpcs} />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="mt-4 flex items-start gap-2 text-xs text-slate-400">
                <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                <p>Our AI will cross-reference these codes with the clinical text to ensure accuracy and compliance. Active codes: {activeHumanCodes.length}</p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <Zap className="w-4 h-4 text-amber-500" />
              Advanced validation engine active.
            </div>
            <button
              onClick={simulateProcessing}
              disabled={!activeClinicalNote.trim() || activeHumanCodes.length === 0 || isProcessing || (noteInputMode === 'file' && noteUploadStatus !== 'complete') || (humanCodeMode === 'file' && codesUploadStatus !== 'complete')}
              className="group px-10 py-4 bg-hospital-blue-600 text-white font-bold rounded-xl hover:bg-hospital-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 shadow-xl shadow-hospital-blue-100 active:scale-95"
            >
              <CheckCircle className="w-4 h-4 group-hover:scale-110 transition-transform" />
              Validate & Enhance
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Info className="w-4 h-4 text-hospital-blue-600" />
              Assisted Workflow
            </h3>
            <div className="space-y-6">
              <WorkflowStep 
                number="1" 
                title="Input Data" 
                desc="Provide clinical notes and any codes you've already identified." 
              />
              <WorkflowStep 
                number="2" 
                title="AI Validation" 
                desc="System checks your codes for accuracy against the clinical evidence." 
              />
              <WorkflowStep 
                number="3" 
                title="Gap Analysis" 
                desc="AI identifies missing codes or potential compliance issues." 
              />
            </div>
          </div>

          <div className="bg-hospital-blue-50 rounded-2xl p-6 border border-hospital-blue-100">
            <h4 className="font-bold text-hospital-blue-900 mb-2">Compliance Engine</h4>
            <p className="text-sm text-hospital-blue-700 leading-relaxed mb-4">
              Our system validates against the latest NCCI edits and medical necessity policies.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <ComplianceBadge label="NCCI" />
              <ComplianceBadge label="MUE" />
              <ComplianceBadge label="LCD" />
              <ComplianceBadge label="NCD" />
            </div>
          </div>
        </div>
      </div>

      {isProcessing && (
        <ProcessingPanel steps={activeSteps} currentStepId={currentStep} />
      )}
    </div>
  );
}

function CodeList({ title, codes }: { title: string; codes: any[] }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">{title} ({codes.length})</p>
      <div className="space-y-1 max-h-28 overflow-y-auto">
        {codes.map((c, idx) => (
          <div key={`${title}-${idx}`} className="font-mono text-[11px] text-slate-700 bg-white border border-slate-200 rounded px-2 py-1">
            {c.code}
          </div>
        ))}
      </div>
    </div>
  );
}

function WorkflowStep({ number, title, desc }: { number: string, title: string, desc: string }) {
  return (
    <div className="flex gap-4">
      <div className="w-6 h-6 rounded-full bg-hospital-blue-600 text-white flex-shrink-0 flex items-center justify-center text-[10px] font-bold">
        {number}
      </div>
      <div>
        <h4 className="text-sm font-bold text-slate-900">{title}</h4>
        <p className="text-xs text-slate-500 mt-1">{desc}</p>
      </div>
    </div>
  );
}

function ComplianceBadge({ label }: { label: string }) {
  return (
    <div className="px-2 py-1 bg-white border border-hospital-blue-200 rounded text-[10px] font-bold text-hospital-blue-600 text-center">
      {label} Verified
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
  const sections = parseClinicalNote(note);
  
  return (
    <div className="text-sm text-slate-700 space-y-3 max-h-56 overflow-y-auto">
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

function parseClinicalNote(text: string): Array<{ title?: string; content: string }> {
  const lines = text.split('\n');
  const sections: Array<{ title?: string; lines: string[] }> = [];
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
      sections.push(currentSection);
      currentSection = { title: line.replace(':', '').trim(), lines: [] };
    } else if (isSectionHeader) {
      currentSection.title = line.replace(':', '').trim();
    } else if (line.trim()) {
      currentSection.lines.push(line);
    }
  }
  
  if (currentSection.lines.length > 0 || currentSection.title) {
    sections.push(currentSection);
  }
  
  return sections.length > 0
    ? sections.map(s => ({ title: s.title, content: s.lines.join('\n').trim() }))
    : [{ content: text }];
}
