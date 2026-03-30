import React from 'react';
import { saveAs } from 'file-saver';
import { pdf, Document, Page, Text, View, StyleSheet, Font } from '@react-pdf/renderer';

const styles = StyleSheet.create({
  page: { padding: 40, fontFamily: 'Helvetica', fontSize: 10, color: '#1e293b' },
  title: { fontSize: 20, fontWeight: 'bold', textAlign: 'center', marginBottom: 6 },
  subtitle: { fontSize: 10, textAlign: 'center', color: '#64748b', marginBottom: 20 },
  sectionHeading: { fontSize: 13, fontWeight: 'bold', marginTop: 18, marginBottom: 6, color: '#1d4ed8', borderBottomWidth: 1, borderBottomColor: '#e2e8f0', paddingBottom: 4 },
  subHeading: { fontSize: 11, fontWeight: 'bold', marginTop: 12, marginBottom: 4, color: '#334155' },
  row: { flexDirection: 'row', marginBottom: 4 },
  label: { fontWeight: 'bold', width: 160, color: '#475569' },
  value: { flex: 1, color: '#0f172a' },
  tableHeader: { flexDirection: 'row', backgroundColor: '#f1f5f9', padding: 6, borderRadius: 4, marginBottom: 2 },
  tableRow: { flexDirection: 'row', padding: 6, borderBottomWidth: 1, borderBottomColor: '#f1f5f9' },
  colCode: { width: 100, fontWeight: 'bold', color: '#1d4ed8', fontFamily: 'Courier' },
  colDesc: { flex: 1, color: '#334155' },
  colUnits: { width: 50, textAlign: 'center' },
  colConf: { width: 60, textAlign: 'right', color: '#64748b' },
  badge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, fontSize: 9, fontWeight: 'bold' },
  badgeGreen: { backgroundColor: '#dcfce7', color: '#166534' },
  badgeRed: { backgroundColor: '#fee2e2', color: '#991b1b' },
  badgeBlue: { backgroundColor: '#dbeafe', color: '#1e40af' },
  noteBox: { backgroundColor: '#f8fafc', borderWidth: 1, borderColor: '#e2e8f0', padding: 10, borderRadius: 6, marginBottom: 10, fontFamily: 'Courier', fontSize: 9, color: '#475569' },
  complianceGreen: { backgroundColor: '#f0fdf4', borderWidth: 1, borderColor: '#bbf7d0', padding: 10, borderRadius: 6, marginBottom: 8 },
  complianceRed: { backgroundColor: '#fef2f2', borderWidth: 1, borderColor: '#fecaca', padding: 10, borderRadius: 6, marginBottom: 8 },
  debateCard: { borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 6, marginBottom: 10, overflow: 'hidden' },
  debateHeader: { backgroundColor: '#f8fafc', padding: 8, flexDirection: 'row', justifyContent: 'space-between' },
  debateBody: { padding: 8 },
  debateResolution: { backgroundColor: '#eff6ff', padding: 8, borderTopWidth: 1, borderTopColor: '#bfdbfe' },
  justCard: { borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 6, padding: 10, marginBottom: 8 },
  separator: { height: 1, backgroundColor: '#f1f5f9', marginVertical: 8 },
});

function LabelValue({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}:</Text>
      <Text style={styles.value}>{value}</Text>
    </View>
  );
}

function CodeTablePdf({ title, codes, showUnits = false }: { title: string; codes: any[]; showUnits?: boolean }) {
  return (
    <View>
      <Text style={styles.subHeading}>{title}</Text>
      <View style={styles.tableHeader}>
        <Text style={styles.colCode}>Code</Text>
        <Text style={styles.colDesc}>Description</Text>
        {showUnits && <Text style={styles.colUnits}>Units</Text>}
        <Text style={styles.colConf}>Conf.</Text>
      </View>
      {codes.map((c, i) => (
        <View key={i} style={styles.tableRow}>
          <Text style={styles.colCode}>{c.code}</Text>
          <Text style={styles.colDesc}>{c.description || ''}</Text>
          {showUnits && <Text style={styles.colUnits}>{c.units || 1}</Text>}
          <Text style={styles.colConf}>{Math.round((c.confidence || 0) * 100)}%</Text>
        </View>
      ))}
    </View>
  );
}

function ReportDocument({ apiData }: { apiData: any }) {
  const report = apiData?.report || {};
  const title = apiData?.mode === 'auto' ? 'Autonomous Coding Final Report' : 'Assisted Coding Analysis Report';
  const confidence = report.confidence_scores?.overall_coding_confidence || 0;
  const riskLevel = (report.confidence_scores?.risk_level || 'Low').toUpperCase();
  const finalIcd10 = report.icd10_codes || [];
  const finalCpt = report.cpt_codes || [];
  const finalHcpcs = report.hcpcs_codes || [];
  const humanInput = report.human_code_input || null;
  const comp = report.comparison_result;
  const s = comp?.summary || {};

  return (
    <Document title={title}>
      <Page size="A4" style={styles.page}>

        {/* Title */}
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle}>AI-Verified Medical Codes & Compliance Analysis</Text>

        {/* Summary */}
        <Text style={styles.sectionHeading}>Summary</Text>
        <LabelValue label="Overall Confidence" value={`${Math.round(confidence * 100)}%`} />
        <LabelValue label="Compliance Risk" value={riskLevel} />
        {report.confidence_scores?.human_agreement_rate !== undefined && (
          <LabelValue label="Human Match Rate" value={`${Math.round(report.confidence_scores.human_agreement_rate * 100)}%`} />
        )}

        {/* Clinical Note */}
        {report.patient_note_excerpt && (
          <>
            <Text style={styles.sectionHeading}>Clinical Note Excerpt</Text>
            <Text style={styles.noteBox}>{report.patient_note_excerpt}</Text>
          </>
        )}

        {/* Human Coder Input */}
        {humanInput && (
          <>
            <Text style={styles.sectionHeading}>Human Coder Input</Text>
            {humanInput.icd10_codes?.length > 0 && <CodeTablePdf title="ICD-10" codes={humanInput.icd10_codes} />}
            {humanInput.cpt_codes?.length > 0 && <CodeTablePdf title="CPT" codes={humanInput.cpt_codes} showUnits />}
            {humanInput.hcpcs_codes?.length > 0 && <CodeTablePdf title="HCPCS" codes={humanInput.hcpcs_codes} showUnits />}
          </>
        )}

        {/* Final Codes */}
        <Text style={styles.sectionHeading}>Verified Codes for Billing</Text>
        {finalIcd10.length > 0 && <CodeTablePdf title={`ICD-10-CM Diagnoses (${finalIcd10.length})`} codes={finalIcd10} />}
        {finalCpt.length > 0 && <CodeTablePdf title={`CPT Procedures (${finalCpt.length})`} codes={finalCpt} showUnits />}
        {finalHcpcs.length > 0 && <CodeTablePdf title={`HCPCS Supplies / Drugs (${finalHcpcs.length})`} codes={finalHcpcs} showUnits />}

        {/* Human vs AI Comparison */}
        {comp?.has_human_input && (
          <>
            <Text style={styles.sectionHeading}>Human vs AI Comparison</Text>
            <LabelValue label="Exact Matches" value={String(s.exact_matches ?? 0)} />
            <LabelValue label="Discrepancies" value={String(s.discrepancies ?? 0)} />
            <LabelValue label="AI Only" value={String(s.ai_only_codes ?? 0)} />
            <LabelValue label="Human Only" value={String(s.human_only_codes ?? 0)} />
            <LabelValue label="AI Accuracy vs Human" value={`${Math.round((s.ai_accuracy_vs_human || 0) * 100)}%`} />
            <LabelValue label="Human Accuracy vs AI" value={`${Math.round((s.human_accuracy_vs_ai || 0) * 100)}%`} />
            <LabelValue label="Overall Match Rate" value={`${Math.round((s.overall_match_rate || 0) * 100)}%`} />
            {comp.discrepancies?.length > 0 && (
              <>
                <Text style={styles.subHeading}>Discrepancies</Text>
                {comp.discrepancies.map((d: any, i: number) => (
                  <View key={i} style={{ marginBottom: 6 }}>
                    <Text style={{ fontWeight: 'bold' }}>{d.discrepancy_type?.replace('_', ' ').toUpperCase()} — {d.code}</Text>
                    <Text>AI: {d.ai_code || 'Not coded'} | Human: {d.human_code || 'Not coded'}</Text>
                    <Text style={{ color: '#64748b', fontStyle: 'italic' }}>Impact: {d.clinical_impact}</Text>
                  </View>
                ))}
              </>
            )}
          </>
        )}

      </Page>

      {/* Page 2: Debate */}
      {report.debate_result && (
        <Page size="A4" style={styles.page}>
          <Text style={styles.sectionHeading}>Agent Debate</Text>
          <Text style={{ fontWeight: 'bold', marginBottom: 8 }}>{report.debate_result.debate_summary}</Text>
          <LabelValue label="Clinical Wins" value={String(report.debate_result.clinical_wins)} />
          <LabelValue label="Revenue Wins" value={String(report.debate_result.revenue_wins)} />
          {report.debate_result.debate_points?.map((pt: any, i: number) => (
            <View key={i} style={styles.debateCard}>
              <View style={styles.debateHeader}>
                <Text style={{ fontWeight: 'bold', color: '#1d4ed8' }}>{pt.final_code} ({pt.code_type})</Text>
                <Text style={{ fontSize: 9, color: '#64748b' }}>Winner: {pt.winning_agent}</Text>
              </View>
              <View style={styles.debateBody}>
                <Text style={{ fontWeight: 'bold', marginBottom: 2 }}>Clinical Agent:</Text>
                <Text style={{ marginBottom: 6, color: '#475569' }}>{pt.clinical_position}</Text>
                <Text style={{ fontWeight: 'bold', marginBottom: 2 }}>Revenue Agent:</Text>
                <Text style={{ color: '#475569' }}>{pt.revenue_position}</Text>
              </View>
              <View style={styles.debateResolution}>
                <Text style={{ fontWeight: 'bold' }}>Resolution: <Text style={{ fontWeight: 'normal' }}>{pt.resolution}</Text></Text>
                <Text style={{ color: '#1e40af', marginTop: 2 }}>{pt.reasoning}</Text>
              </View>
            </View>
          ))}
        </Page>
      )}

      {/* Page 3: Compliance */}
      <Page size="A4" style={styles.page}>
        <Text style={styles.sectionHeading}>Compliance & Audit</Text>
        {report.compliance_result && (
          <>
            <View style={report.compliance_result.is_compliant ? styles.complianceGreen : styles.complianceRed}>
              <Text style={{ fontWeight: 'bold' }}>
                {report.compliance_result.is_compliant ? '✔ Fully Compliant' : '✖ Violations Detected'}
              </Text>
              <Text style={{ marginTop: 2 }}>
                {report.compliance_result.is_compliant
                  ? 'No critical NCCI/MUE/LCD violations detected.'
                  : 'Review the edits below before submission.'}
              </Text>
            </View>
            {['ncci_violations', 'mue_violations', 'lcd_issues'].map((key) =>
              report.compliance_result[key]?.length > 0 ? (
                <View key={key}>
                  <Text style={styles.subHeading}>{key.replace('_', ' ').toUpperCase()}</Text>
                  {report.compliance_result[key].map((item: any, i: number) => (
                    <Text key={i} style={{ marginBottom: 4 }}>
                      <Text style={{ fontWeight: 'bold' }}>{item.cpt_code || item.column1_code || item.rule_id}</Text>: {item.description || item.reason}
                    </Text>
                  ))}
                </View>
              ) : null
            )}
          </>
        )}
        {report.audit_findings?.map((f: any, i: number) => (
          <View key={i} style={{ marginBottom: 8 }}>
            <Text style={{ fontWeight: 'bold' }}>[{f.severity?.toUpperCase()}] {f.code}</Text>
            <Text style={{ color: '#334155' }}>{f.description}</Text>
            <Text style={{ color: '#1d4ed8' }}>Rec: {f.recommendation}</Text>
          </View>
        ))}
      </Page>

      {/* Page 4: Justifications */}
      {report.justifications?.length > 0 && (
        <Page size="A4" style={styles.page}>
          <Text style={styles.sectionHeading}>Code Justifications</Text>
          {report.justifications.map((j: any, i: number) => (
            <View key={i} style={styles.justCard}>
              <View style={[styles.row, { marginBottom: 6 }]}>
                <Text style={{ fontWeight: 'bold', color: '#1d4ed8', fontSize: 12 }}>{j.code}</Text>
                <Text style={{ marginLeft: 8, color: '#64748b', fontSize: 9 }}>{j.code_type}</Text>
                {j.comparison_verdict !== 'no_comparison' && (
                  <Text style={{ marginLeft: 'auto', color: '#7c3aed', fontSize: 9 }}>{j.comparison_verdict?.replace('_', ' ')}</Text>
                )}
              </View>
              <LabelValue label="Clinical Evidence" value={j.clinical_evidence} />
              <LabelValue label="Guideline" value={j.guideline_reference} />
              <LabelValue label="Explanation" value={j.explanation} />
            </View>
          ))}
        </Page>
      )}
    </Document>
  );
}

export async function exportReportAsPdf(apiData: any) {
  const title = apiData?.mode === 'auto' ? 'Autonomous_Coding_Final_Report' : 'Assisted_Coding_Analysis_Report';
  const filename = `${title}_${new Date().toISOString().slice(0, 10)}.pdf`;
  const blob = await pdf(<ReportDocument apiData={apiData} />).toBlob();
  saveAs(blob, filename);
}
