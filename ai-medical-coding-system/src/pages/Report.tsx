import React, { useState } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { 
  FileText, Activity, CheckCircle2, AlertTriangle, 
  ChevronLeft, Download, Printer, 
  ClipboardCheck, Copy, Check, Shield, Users, 
  Scale, BookOpen, AlertOctagon, Info, Heart
} from 'lucide-react';
import { exportReportAsPdf } from '@/lib/exportReportPdf';


export function ReportView({ apiData, onBack }: { apiData: any, onBack?: () => void }) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'FINAL' | 'DEBATE' | 'COMPLIANCE' | 'JUSTIFICATIONS'>('FINAL');

  const report = apiData?.report || {};
  const reportUrl = apiData?.report_url || '';
  const reportFilename = reportUrl.split('/').pop() || 'report.html';

  const title = apiData?.mode === 'auto' ? 'Autonomous Coding Final Report' : 'Assisted Coding Analysis Report';
  const confidence = report.confidence_scores?.overall_coding_confidence || 0;
  const riskLevel = report.confidence_scores?.risk_level || 'Low';

  const finalIcd10 = report.icd10_codes || [];
  const finalCpt = report.cpt_codes || [];
  const finalHcpcs = report.hcpcs_codes || [];
  const comparison = report.comparison_result || null;
  const hasComparison = !!comparison?.has_human_input;
  const humanInput = report.human_code_input || null;
  const matchedCodes = comparison?.matched_codes || [];
  const aiOnlyCodes = (comparison?.discrepancies || []).filter((d: any) => d.discrepancy_type === 'ai_only');
  const humanOnlyCodes = (comparison?.discrepancies || []).filter((d: any) => d.discrepancy_type === 'human_only');
  const unitMismatchCodes = (comparison?.discrepancies || []).filter((d: any) => d.discrepancy_type === 'units_mismatch');
  const clinicalAgentCodes = report.clinical_agent_codes || null;
  const revenueAgentCodes = report.revenue_agent_codes || null;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(text);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const handlePrint = () => window.print();

  const handleDownload = () => {
    window.location.href = `/api/download/${reportFilename}`;
  };

  // ✅ Clean PDF export — no print dialog, real .pdf file download
  const handleExportPDF = () => exportReportAsPdf(apiData);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 bg-white text-slate-900 rounded-2xl shadow-sm border border-slate-100 my-8">
      <style>{`
        @media print {
          body { font-size: 11pt; background: #fff !important; margin: 0; padding: 20px; }
          .no-print { display: none !important; }
          .print-only { display: block !important; }
          .shadow-sm, .shadow-xl { box-shadow: none !important; }
          * { float: none !important; position: relative !important; }
          .rounded-2xl { border-radius: 8px !important; }
          .max-w-6xl { max-width: 100% !important; }
          table { page-break-inside: avoid; }
          .p-6 { page-break-inside: avoid; }
          .grid { page-break-inside: avoid; }
        }
      `}</style>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10 pb-6 border-b border-slate-100 no-print">
        <div>
          {onBack && (
            <button onClick={onBack} className="text-hospital-blue-600 hover:text-hospital-blue-700 flex items-center gap-1 text-sm font-bold mb-4 group">
              <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
              Start New Note
            </button>
          )}
          <h1 className="text-3xl font-black tracking-tight">{title}</h1>
          <p className="text-sm text-slate-500 mt-2 flex items-center gap-2">
            <Shield className="w-4 h-4 text-hospital-blue-500" />
            AI-Verified Medical Codes & Compliance Analysis
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* ✅ Export PDF button — triggers real PDF download */}
          <button
            onClick={handleExportPDF}
            className="p-3 rounded-xl border border-slate-200 hover:bg-red-50 hover:border-red-300 text-slate-600 transition-all font-bold flex items-center gap-2"
            title="Export as PDF"
          >
            <FileText className="w-4 h-4 text-red-500" />
            <span className="hidden sm:inline">Export PDF</span>
          </button>

          <button
            onClick={handlePrint}
            className="p-3 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-all font-bold flex items-center gap-2"
          >
            <Printer className="w-4 h-4" />
            <span className="hidden sm:inline">Print</span>
          </button>

          <button
            onClick={handleDownload}
            className="p-3 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-all font-bold flex items-center gap-2"
            title="Download HTML (use Ctrl+P or Cmd+P to print as PDF)"
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">Download HTML</span>
          </button>
        </div>
      </div>

      {/* Dashboard Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100">
          <div className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-2 flex items-center gap-2">
            <Activity className="w-4 h-4" /> Overall Confidence
          </div>
          <span className="text-4xl font-black text-hospital-blue-600">
            {Math.round(confidence * 100)}%
          </span>
        </div>

        <div className={`p-6 rounded-2xl border ${
          riskLevel.toLowerCase() === 'high' ? 'bg-red-50 border-red-100' :
          riskLevel.toLowerCase() === 'medium' ? 'bg-amber-50 border-amber-100' :
          'bg-green-50 border-green-100'
        }`}>
          <div className={`text-sm font-bold uppercase tracking-widest mb-2 flex items-center gap-2 ${
            riskLevel.toLowerCase() === 'high' ? 'text-red-400' :
            riskLevel.toLowerCase() === 'medium' ? 'text-amber-400' :
            'text-green-500'
          }`}>
            <AlertOctagon className="w-4 h-4" /> Compliance Risk
          </div>
          <div className={`text-3xl font-black ${
            riskLevel.toLowerCase() === 'high' ? 'text-red-700' :
            riskLevel.toLowerCase() === 'medium' ? 'text-amber-700' :
            'text-green-700'
          }`}>
            {riskLevel.toUpperCase()}
          </div>
        </div>

        {hasComparison && (
          <div className="p-6 bg-purple-50 rounded-2xl border border-purple-100">
            <div className="text-sm font-bold text-purple-400 uppercase tracking-widest mb-2 flex items-center gap-2">
              <Users className="w-4 h-4" /> Human Match Rate
            </div>
            <span className="text-4xl font-black text-purple-700">
              {Math.round((report.confidence_scores?.human_agreement_rate || 0) * 100)}%
            </span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 mb-8 no-print overflow-x-auto pb-2">
        <TabButton active={activeTab === 'FINAL'} onClick={() => setActiveTab('FINAL')} icon={<FileText className="w-4 h-4" />} label="Final Codes" />
        {report.debate_result && (
          <TabButton active={activeTab === 'DEBATE'} onClick={() => setActiveTab('DEBATE')} icon={<Scale className="w-4 h-4" />} label="Agent Debate" />
        )}
        <TabButton active={activeTab === 'COMPLIANCE'} onClick={() => setActiveTab('COMPLIANCE')} icon={<ClipboardCheck className="w-4 h-4" />} label="Compliance & Audit" />
        <TabButton active={activeTab === 'JUSTIFICATIONS'} onClick={() => setActiveTab('JUSTIFICATIONS')} icon={<BookOpen className="w-4 h-4" />} label="Justifications" />
      </div>

      {/* Tab Content */}
      <div className="space-y-12">

        {/* FINAL CODES */}
        {activeTab === 'FINAL' && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {report.patient_note_excerpt && (
              <div className="p-6 bg-slate-50 border border-slate-100 rounded-2xl">
                <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <Heart className="w-4 h-4" /> Clinical Note Excerpt
                </h3>
                <p className="font-mono text-sm text-slate-600 leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap break-words">
                  {report.patient_note_excerpt}
                </p>
              </div>
            )}

            {(clinicalAgentCodes || revenueAgentCodes) && (
              <div className="p-6 bg-white border border-slate-200 rounded-2xl">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <Users className="w-5 h-5 text-hospital-blue-600" /> Clinical Accuracy vs Revenue Optimization Agent Output
                </h3>
                <p className="text-xs text-slate-500 mb-4">These are the proposed code sets before final debate resolution.</p>
                <div className="grid md:grid-cols-2 gap-4">
                  {clinicalAgentCodes && <AgentCodePanel title="Clinical Accuracy Agent" panelColor="cyan" codes={clinicalAgentCodes} />}
                  {revenueAgentCodes && <AgentCodePanel title="Revenue Optimization Agent" panelColor="green" codes={revenueAgentCodes} />}
                </div>
              </div>
            )}

            <div>
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                <CheckCircle2 className="w-6 h-6 text-green-500" /> Verified Codes for Billing
              </h3>

              {humanInput && (humanInput.icd10_codes?.length > 0 || humanInput.cpt_codes?.length > 0 || humanInput.hcpcs_codes?.length > 0) && (
                <div className="mb-8 p-6 bg-purple-50 border border-purple-200 rounded-2xl">
                  <h4 className="font-bold text-purple-900 mb-4 flex items-center gap-2">
                    <Users className="w-5 h-5" /> Human Coder Input
                  </h4>
                  <div className="grid md:grid-cols-3 gap-4">
                    {humanInput.icd10_codes?.length > 0 && (
                      <div className="p-4 bg-white rounded-xl border border-purple-100">
                        <div className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">ICD-10 ({humanInput.icd10_codes.length})</div>
                        <div className="space-y-2">
                          {humanInput.icd10_codes.map((c: any, i: number) => (
                            <div key={i} className="p-2 bg-purple-50 rounded font-mono text-sm font-bold text-purple-700">{c.code}</div>
                          ))}
                        </div>
                      </div>
                    )}
                    {humanInput.cpt_codes?.length > 0 && (
                      <div className="p-4 bg-white rounded-xl border border-purple-100">
                        <div className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">CPT ({humanInput.cpt_codes.length})</div>
                        <div className="space-y-2">
                          {humanInput.cpt_codes.map((c: any, i: number) => (
                            <div key={i} className="p-2 bg-purple-50 rounded font-mono text-sm font-bold text-purple-700">{c.code}</div>
                          ))}
                        </div>
                      </div>
                    )}
                    {humanInput.hcpcs_codes?.length > 0 && (
                      <div className="p-4 bg-white rounded-xl border border-purple-100">
                        <div className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">HCPCS ({humanInput.hcpcs_codes.length})</div>
                        <div className="space-y-2">
                          {humanInput.hcpcs_codes.map((c: any, i: number) => (
                            <div key={i} className="p-2 bg-purple-50 rounded font-mono text-sm font-bold text-purple-700">{c.code}</div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="space-y-8">
                {finalIcd10.length > 0 && <CodeTable title={`ICD-10-CM Diagnoses (${finalIcd10.length})`} codes={finalIcd10} onCopy={copyToClipboard} copied={copiedCode} />}
                  {finalCpt.length > 0 && <CodeTable title={`CPT Procedures (${finalCpt.length})`} codes={finalCpt} showUnits onCopy={copyToClipboard} copied={copiedCode} />}
                  {finalHcpcs.length > 0 && <CodeTable title={`HCPCS Supplies / Drugs (${finalHcpcs.length})`} codes={finalHcpcs} showUnits onCopy={copyToClipboard} copied={copiedCode} />}
                {finalIcd10.length === 0 && finalCpt.length === 0 && finalHcpcs.length === 0 && (
                  <div className="p-8 text-center text-slate-500 italic bg-slate-50 rounded-2xl">
                    No billable codes were finalized for this document.
                  </div>
                )}
              </div>
            </div>

            {hasComparison && comparison && (
              <div className="p-6 bg-slate-50 border border-slate-200 rounded-2xl">
                <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                  <Users className="w-5 h-5 text-hospital-blue-600" /> Human vs AI Comparison
                </h3>
                <div className="space-y-4 mb-6">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <MiniStat label="Matches" value={comparison.summary?.exact_matches || 0} color="text-green-600" />
                    <MiniStat label="Differences(unit/quantity mismatches)" value={comparison.summary?.discrepancies || 0} color="text-amber-600" />
                    <MiniStat label="AI Only" value={comparison.summary?.ai_only_codes || 0} color="text-hospital-blue-600" />
                    <MiniStat label="Human Only" value={comparison.summary?.human_only_codes || 0} color="text-red-600" />
                  </div>
                  {comparison.summary && (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <MiniStat label="AI Accuracy vs Human" value={`${Math.round((comparison.summary.ai_accuracy_vs_human || 0) * 100)}%`} color="text-purple-600" />
                      <MiniStat label="Human Accuracy vs AI" value={`${Math.round((comparison.summary.human_accuracy_vs_ai || 0) * 100)}%`} color="text-indigo-600" />
                      <MiniStat label="Overall Match Rate" value={`${Math.round((comparison.summary.overall_match_rate || 0) * 100)}%`} color="text-cyan-600" />
                    </div>
                  )}
                  <p className="text-xs text-slate-500">Accuracy is calculated from unique normalized codes with exact unit match.</p>
                </div>
                {aiOnlyCodes.length > 0 && (
                  <div className="text-sm mb-6">
                    <h4 className="font-bold text-slate-700 mb-3 text-hospital-blue-600">🤖 Codes Identified by AI Only:</h4>
                    <ul className="space-y-2">
                      {aiOnlyCodes.map((code: any, idx: number) => (
                        <li key={idx} className="p-3 bg-hospital-blue-50 border border-hospital-blue-200 rounded-lg">
                          <span className="font-bold text-hospital-blue-800">{code.code}</span>
                          <span className="text-hospital-blue-700 ml-2">{code.ai_description || code.human_description || ''}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {humanOnlyCodes.length > 0 && (
                  <div className="text-sm mb-6">
                    <h4 className="font-bold text-slate-700 mb-3 text-red-600">👤 Codes Identified by Human Only:</h4>
                    <ul className="space-y-2">
                      {humanOnlyCodes.map((code: any, idx: number) => (
                        <li key={idx} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                          <span className="font-bold text-red-800">{code.code}</span>
                          <span className="text-red-700 ml-2">{code.human_description || code.ai_description || ''}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {matchedCodes.length > 0 && (
                  <div className="text-sm mb-6">
                    <h4 className="font-bold text-slate-700 mb-3 text-green-600">✓ Codes Agreed Upon (AI + Human):</h4>
                    <ul className="space-y-2">
                      {matchedCodes.map((code: any, idx: number) => (
                        <li key={idx} className="p-3 bg-green-50 border border-green-200 rounded-lg">
                          <span className="font-bold text-green-800">{code.code}</span>
                          <span className="text-green-700 ml-2">{code.description}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {unitMismatchCodes.length > 0 && (
                  <div className="text-sm">
                    <h4 className="font-bold text-slate-700 mb-3">Discrepancies Detected:</h4>
                    <ul className="space-y-3">
                      {unitMismatchCodes.map((d: any, idx: number) => (
                        <li key={idx} className="flex flex-col gap-1 p-3 bg-white border border-slate-200 rounded-lg hover:shadow-md transition-all">
                          <span className="font-bold text-slate-800">{d.discrepancy_type.replace('_', ' ').toUpperCase()} - {d.code}</span>
                          <span className="text-slate-600"><strong>AI:</strong> {d.ai_code || 'Not coded'} | <strong>Human:</strong> {d.human_code || 'Not coded'}</span>
                          <span className="text-slate-500 italic">Impact: {d.clinical_impact}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* DEBATE */}
        {activeTab === 'DEBATE' && report.debate_result && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="p-6 bg-slate-50 border border-slate-200 rounded-2xl">
              <h3 className="text-lg font-bold text-slate-800 mb-4">{report.debate_result.debate_summary}</h3>
              <div className="flex gap-4 mb-2">
                <span className="px-3 py-1 bg-green-100 text-green-800 rounded-lg font-bold text-sm">Clinical Wins: {report.debate_result.clinical_wins}</span>
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-lg font-bold text-sm">Revenue Wins: {report.debate_result.revenue_wins}</span>
              </div>
            </div>
            {report.debate_result.debate_points?.map((pt: any, idx: number) => (
              <div key={idx} className="border border-slate-200 rounded-2xl overflow-hidden bg-white shadow-sm">
                <div className="bg-slate-50 p-4 border-b border-slate-200 flex justify-between items-center">
                  <div className="font-bold text-hospital-blue-900 text-lg">
                    {pt.final_code} <span className="text-xs font-normal text-slate-500 uppercase tracking-wider ml-2">{pt.code_type}</span>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                    pt.winning_agent === 'clinical' ? 'bg-green-100 text-green-700' :
                    pt.winning_agent === 'revenue' ? 'bg-blue-100 text-blue-700' :
                    'bg-purple-100 text-purple-700'
                  }`}>
                    Winner: {pt.winning_agent}
                  </span>
                </div>
                <div className="p-6 grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-sm font-bold text-slate-400 uppercase mb-2">🏥 Clinical Agent Said</h4>
                    <p className="text-slate-700 text-sm leading-relaxed">{pt.clinical_position}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-400 uppercase mb-2">💰 Revenue Agent Said</h4>
                    <p className="text-slate-700 text-sm leading-relaxed">{pt.revenue_position}</p>
                  </div>
                </div>
                <div className="bg-hospital-blue-50 p-4 border-t border-hospital-blue-100 text-sm text-hospital-blue-900">
                  <span className="font-bold">Resolution:</span> {pt.resolution}<br />
                  <span className="text-hospital-blue-700 mt-1 block">{pt.reasoning}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* COMPLIANCE */}
        {activeTab === 'COMPLIANCE' && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {report.compliance_result ? (
              <div className="space-y-6">
                {report.compliance_result.is_compliant ? (
                  <div className="p-6 bg-green-50 border border-green-200 text-green-800 rounded-2xl flex items-center gap-4">
                    <CheckCircle2 className="w-8 h-8 flex-shrink-0" />
                    <div>
                      <h3 className="font-bold text-lg">Fully Compliant</h3>
                      <p className="text-sm opacity-90">No critical NCCI/MUE/LCD violations detected.</p>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 bg-red-50 border border-red-200 text-red-800 rounded-2xl flex items-center gap-4">
                    <AlertTriangle className="w-8 h-8 flex-shrink-0" />
                    <div>
                      <h3 className="font-bold text-lg">Compliance Violations Detected</h3>
                      <p className="text-sm opacity-90">Please review the edits below before submission.</p>
                    </div>
                  </div>
                )}
                {report.compliance_result.ncci_violations?.length > 0 && <ViolationSection title="NCCI Edits" items={report.compliance_result.ncci_violations} color="red" />}
                {report.compliance_result.mue_violations?.length > 0 && <ViolationSection title="MUE Limits" items={report.compliance_result.mue_violations} color="amber" />}
                {!report.compliance_result.is_compliant && report.compliance_result.lcd_issues?.length > 0 && <ViolationSection title="LCD Issues" items={report.compliance_result.lcd_issues} color="hospital-blue" />}
                {!report.compliance_result.is_compliant && report.compliance_result.ncd_issues?.length > 0 && <ViolationSection title="NCD Issues" items={report.compliance_result.ncd_issues} color="hospital-blue" />}
                
                {/* Advisory Issues Section — shows for compliant claims with advisory items */}
                {report.compliance_result.is_compliant && (report.compliance_result.missed_codes?.length > 0 || report.compliance_result.lcd_issues?.length > 0 || report.compliance_result.ncd_issues?.length > 0) && (
                  <div className="p-5 rounded-2xl border border-amber-100 bg-amber-50 text-amber-900 space-y-4">
                    <h4 className="font-bold text-amber-800 flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5" /> ⚠️ Advisory Issues — Review Before Submission
                    </h4>
                    
                    {report.compliance_result.missed_codes?.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-sm font-bold text-amber-700">Potentially Missed Billable Codes ({report.compliance_result.missed_codes.length}):</div>
                        <ul className="space-y-2 ml-4">
                          {report.compliance_result.missed_codes.map((code: string, idx: number) => (
                            <li key={idx} className="text-sm text-amber-800 flex items-start gap-2">
                              <span className="text-amber-600 font-bold mt-0.5">•</span>
                              <span>{code}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {report.compliance_result.lcd_issues?.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-sm font-bold text-amber-700">Local Coverage Requirements:</div>
                        <ul className="space-y-2 ml-4">
                          {report.compliance_result.lcd_issues.map((issue: any, idx: number) => (
                            <li key={idx} className="text-sm text-amber-800 flex items-start gap-2">
                              <span className="text-amber-600 font-bold mt-0.5">•</span>
                              <span><strong>{issue.rule_id}</strong>: {issue.description}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {report.compliance_result.ncd_issues?.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-sm font-bold text-amber-700">National Coverage Requirements:</div>
                        <ul className="space-y-2 ml-4">
                          {report.compliance_result.ncd_issues.map((issue: any, idx: number) => (
                            <li key={idx} className="text-sm text-amber-800 flex items-start gap-2">
                              <span className="text-amber-600 font-bold mt-0.5">•</span>
                              <span><strong>{issue.rule_id}</strong>: {issue.description}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : <p className="text-slate-500 italic p-6 text-center">No compliance data available.</p>}

            {report.audit_findings?.length > 0 && (
              <div>
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                  <Info className="w-5 h-5 text-hospital-blue-500" /> AI Audit Findings
                </h3>
                <div className="space-y-3">
                  {report.audit_findings.map((finding: any, idx: number) => (
                    <div key={idx} className="p-4 border border-slate-200 rounded-xl bg-white shadow-sm flex flex-col gap-2">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                          finding.severity === 'high' ? 'bg-red-100 text-red-700' :
                          finding.severity === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'
                        }`}>
                          {finding.severity}
                        </span>
                        <span className="font-mono font-bold text-slate-800">{finding.code}</span>
                      </div>
                      <p className="text-sm text-slate-700">{finding.description}</p>
                      <p className="text-xs text-hospital-blue-700 font-medium">Rec: {finding.recommendation}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* JUSTIFICATIONS */}
        {activeTab === 'JUSTIFICATIONS' && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {report.justifications?.length > 0 ? (
              report.justifications.map((j: any, idx: number) => (
                <div key={idx} className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="font-mono font-black text-xl text-hospital-blue-600">{j.code}</span>
                    <span className="px-2 py-1 bg-slate-100 text-slate-500 text-xs font-bold uppercase rounded">{j.code_type}</span>
                    {j.comparison_verdict !== 'no_comparison' && (
                      <span className="ml-auto text-xs font-bold uppercase text-purple-600 bg-purple-50 px-2 py-1 rounded">
                        {j.comparison_verdict.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                  <div className="space-y-3 text-sm">
                    <p><strong className="text-slate-400 uppercase tracking-widest text-[10px]">Evidence:</strong><br /><span className="text-slate-700 font-medium">{j.clinical_evidence}</span></p>
                    <p><strong className="text-slate-400 uppercase tracking-widest text-[10px]">Guideline:</strong><br /><span className="text-slate-600">{j.guideline_reference}</span></p>
                    <p><strong className="text-slate-400 uppercase tracking-widest text-[10px]">Explanation:</strong><br /><span className="text-slate-600">{j.explanation}</span></p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-center text-slate-500 italic p-10">No justifications generated for these codes.</p>
            )}
          </div>
        )}

      </div>
    </div>
  );
}


// ── Helper Components ────────────────────────────────────────────────────────

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2.5 rounded-full text-sm font-bold flex items-center gap-2 transition-all shrink-0 ${
        active
          ? 'bg-hospital-blue-600 text-white shadow-md shadow-hospital-blue-200'
          : 'bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-800 border border-slate-200'
      }`}
    >
      {icon} {label}
    </button>
  );
}

function CodeTable({ title, codes, showUnits, onCopy, copied }: { title: string; codes: any[]; showUnits?: boolean; onCopy: (c: string) => void; copied: string | null }) {
  return (
    <div className="overflow-hidden border border-slate-200 rounded-2xl shadow-sm bg-white">
      <div className="bg-slate-50 border-b border-slate-200 p-4 font-bold text-hospital-blue-900">{title}</div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-white text-slate-400 text-xs uppercase tracking-widest">
            <tr>
              <th className="p-4 font-medium">Code</th>
              <th className="p-4 font-medium">Description</th>
              {showUnits && <th className="p-4 font-medium">Units</th>}
              <th className="p-4 font-medium">Confidence</th>
              <th className="p-4 font-medium text-right no-print">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {codes.map((c, i) => (
              <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                <td className="p-4 font-mono font-bold text-hospital-blue-600 whitespace-nowrap">{c.code}</td>
                <td className="p-4 text-slate-700 min-w-[200px]">{c.description}</td>
                {showUnits && <td className="p-4 text-slate-500 font-mono">{c.units || 1}</td>}
                <td className="p-4 whitespace-nowrap">
                  {Number.isFinite(Number(c.confidence)) ? (
                    <span className="font-bold text-hospital-blue-600">{Math.round(c.confidence * 100)}%</span>
                  ) : (
                    <span className="text-[10px] font-bold text-slate-300 italic">N/A</span>
                  )}
                </td>
                <td className="p-4 text-right no-print">
                  <button onClick={() => onCopy(c.code)} className="p-1.5 text-slate-400 hover:text-hospital-blue-600 transition-colors rounded-md hover:bg-hospital-blue-50">
                    {copied === c.code ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AgentCodePanel({ title, panelColor, codes }: { title: string; panelColor: 'cyan' | 'green'; codes: any }) {
  const accent = panelColor === 'cyan'
    ? 'border-cyan-200 bg-cyan-50 text-cyan-900'
    : 'border-green-200 bg-green-50 text-green-900';

  return (
    <div className={`p-4 border rounded-xl ${accent}`}>
      <h4 className="font-bold mb-3">{title}</h4>
      <div className="space-y-3 text-sm">
        <div>
          <div className="text-[10px] uppercase tracking-widest font-bold opacity-70 mb-1">ICD-10 ({codes.icd10_codes?.length || 0})</div>
          <div className="font-mono text-xs break-words">{(codes.icd10_codes || []).map((c: any) => c.code).join(', ') || 'None'}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-widest font-bold opacity-70 mb-1">CPT ({codes.cpt_codes?.length || 0})</div>
          <div className="font-mono text-xs break-words">{(codes.cpt_codes || []).map((c: any) => c.code).join(', ') || 'None'}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-widest font-bold opacity-70 mb-1">HCPCS ({codes.hcpcs_codes?.length || 0})</div>
          <div className="font-mono text-xs break-words">{(codes.hcpcs_codes || []).map((c: any) => c.code).join(', ') || 'None'}</div>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="flex items-center gap-3 p-4 bg-white border border-slate-100 rounded-xl hover:shadow-md transition-all">
      <div className={`text-3xl font-black ${color}`}>{value}</div>
      <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">{label}</div>
    </div>
  );
}

function ViolationSection({ title, items, color }: { title: string; items: any[]; color: 'red' | 'amber' | 'hospital-blue' }) {
  const containerClasses = {
    red: 'bg-red-50 border-red-100 text-red-900',
    amber: 'bg-amber-50 border-amber-100 text-amber-900',
    'hospital-blue': 'bg-hospital-blue-50 border-hospital-blue-100 text-hospital-blue-900',
  };
  const textClasses = {
    red: 'text-red-800',
    amber: 'text-amber-800',
    'hospital-blue': 'text-hospital-blue-800',
  };
  return (
    <div className={`p-5 rounded-2xl border ${containerClasses[color]}`}>
      <h4 className="font-bold mb-3">{title}</h4>
      <ul className="space-y-2">
        {items.map((i, idx) => (
          <li key={idx} className={`text-sm ${textClasses[color]}`}>
            <strong>{i.cpt_code || i.column1_code || i.rule_id}</strong>: {i.description || i.reason}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const apiData = location.state?.reportData || { id, mode: 'auto' };
  return <ReportView apiData={apiData} />;
}
