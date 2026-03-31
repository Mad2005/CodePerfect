"""
HTML Report Generator — Full-Featured Report Export
────────────────────────────────────────────────────
Converts FinalCodingReport to complete, printable HTML.
Automatically saves reports with timestamps in the reports/ folder.
Optimized for:
  • Full console report capture (no truncation)
  • Print/PDF export (all content visible)
  • Browser viewing (responsive, styled)
  • Archive (timestamped file naming)
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from core.models import FinalCodingReport, AgentCodeSet, DebateResult, ComplianceResult


def _html_escape(text: str) -> str:
    """Escape HTML special characters."""
    if not isinstance(text, str):
        text = str(text)
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _parse_missed_code(code_text: str) -> tuple[str, str]:
    """Parse missed code description to extract code and description.
    
    Returns: (code, description)
    Examples:
      'E/M service, suggested code: 99213' -> ('99213', 'E/M service...')
      'Discharge day management' -> ('', 'Discharge day management')
    """
    import re
    
    code_text = str(code_text).strip()
    
    # Try to extract code patterns like "suggested code: 99213" or "code: 99213 or 99214"
    match = re.search(r'(?:suggested\s+)?code[s]?:\s*([A-Z0-9]+(?:\s+or\s+[A-Z0-9]+)*)', code_text, re.I)
    if match:
        code = match.group(1).strip()
        # Remove the code reference from description for cleaner display
        description = re.sub(r',?\s*(?:suggested\s+)?code[s]?:\s*[A-Z0-9\s,or]+', '', code_text, flags=re.I).strip()
        return code, description or code_text
    
    return '', code_text


def _risk_color_css(level: str) -> str:
    """Map risk level to CSS color."""
    return {"low": "#22c55e", "medium": "#eab308", "high": "#ef4444"}.get(level.lower(), "#6b7280")


def _confidence_bar_css(score: float) -> str:
    """Generate CSS for confidence/risk bars."""
    percentage = int(score * 100)
    if score >= 0.75:
        color = "#22c55e"  # green
    elif score >= 0.50:
        color = "#eab308"  # yellow
    else:
        color = "#ef4444"  # red
    
    return f"""
    <div class="score-bar">
        <div class="score-fill" style="width: {percentage}%; background-color: {color};"></div>
        <span class="score-text">{percentage:.0f}%</span>
    </div>
    """


def _render_agent_codes_html(agent: Optional[AgentCodeSet], agent_name: str) -> str:
    """Render agent code set as HTML table."""
    if not agent:
        return f'<p class="warning">⚠ No {agent_name} output</p>'
    
    html = f'<h3 class="section-title">{agent_name}</h3>'
    
    # ICD-10 codes
    if agent.icd10_codes:
        html += '<table class="codes-table">'
        html += '<thead><tr><th>Code</th><th>Description</th><th>Type</th><th>Confidence</th><th>Rationale</th></tr></thead><tbody>'
        for c in agent.icd10_codes:
            html += f'''
            <tr>
                <td class="code-cell">{_html_escape(c.code)}</td>
                <td>{_html_escape(c.description)}</td>
                <td class="dim">{_html_escape(c.sequence_type)}</td>
                <td>{_confidence_bar_css(c.confidence)}</td>
                <td class="dim">{_html_escape(c.rationale[:100])}</td>
            </tr>
            '''
        html += '</tbody></table>'
    
    # CPT codes
    if agent.cpt_codes:
        html += '<table class="codes-table">'
        html += '<thead><tr><th>Code</th><th>Description</th><th>Units</th><th>Confidence</th><th>Rationale</th></tr></thead><tbody>'
        for c in agent.cpt_codes:
            html += f'''
            <tr>
                <td class="code-cell">{_html_escape(c.code)}</td>
                <td>{_html_escape(c.description)}</td>
                <td class="center">{c.units}</td>
                <td>{_confidence_bar_css(c.confidence)}</td>
                <td class="dim">{_html_escape(c.rationale[:100])}</td>
            </tr>
            '''
        html += '</tbody></table>'
    
    # HCPCS codes
    if agent.hcpcs_codes:
        html += '<table class="codes-table">'
        html += '<thead><tr><th>Code</th><th>Description</th><th>Category</th><th>Units</th></tr></thead><tbody>'
        for c in agent.hcpcs_codes:
            html += f'''
            <tr>
                <td class="code-cell">{_html_escape(c.code)}</td>
                <td>{_html_escape(c.description)}</td>
                <td class="dim">{_html_escape(c.category)}</td>
                <td class="center">{c.units}</td>
            </tr>
            '''
        html += '</tbody></table>'
    
    # Agent notes
    if agent.agent_notes:
        html += f'<div class="panel"><strong>Notes:</strong> {_html_escape(agent.agent_notes)}</div>'
    
    return html


def _render_debate_html(dr: Optional[DebateResult]) -> str:
    """Render debate result as HTML."""
    if not dr:
        return '<p class="warning">⚠ No debate result</p>'
    
    html = '<h2 class="section-header">⚖️ Debate Resolution</h2>'
    
    # Scoreboard
    html += '''
    <div class="debate-scoreboard">
        <div class="stat-row">
            <span class="stat-label">🤝 Consensus Codes:</span>
            <span class="stat-value">''' + str(dr.consensus_codes) + '</span></div>'
    
    conflicts = dr.debate_points
    neither = [p for p in conflicts if p.winning_agent == "neither"]
    
    html += f'''
        <div class="stat-row">
            <span class="stat-label">⚖️ Conflicts Resolved:</span>
            <span class="stat-value">{len(conflicts)}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">🏥 Clinical Wins:</span>
            <span class="stat-value">{dr.clinical_wins}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">💰 Revenue Wins:</span>
            <span class="stat-value">{dr.revenue_wins}</span>
        </div>
    '''
    
    if neither:
        html += f'''
        <div class="stat-row warning-row">
            <span class="stat-label">❌ Neither Correct:</span>
            <span class="stat-value">{len(neither)}</span>
        </div>
        '''
    
    html += '</div>'
    
    # Detailed conflicts
    if conflicts:
        html += '<table class="conflicts-table"><thead><tr>'
        html += '<th>Code</th><th>Type</th><th>Conflict</th><th>Clinical</th><th>Revenue</th><th>Winner</th><th>Resolution</th>'
        html += '</tr></thead><tbody>'
        
        for p in conflicts:
            winner_label = {
                "clinical": "🏥 Clinical",
                "revenue": "💰 Revenue",
                "both": "🤝 Consensus",
                "neither": "❌ Neither"
            }.get(p.winning_agent, p.winning_agent)
            
            html += f'''
            <tr>
                <td class="code-cell">{_html_escape(p.final_code)}</td>
                <td class="dim">{_html_escape(p.code_type)}</td>
                <td class="dim">{_html_escape(p.conflict_type)}</td>
                <td>{_html_escape(p.clinical_position[:60])}</td>
                <td>{_html_escape(p.revenue_position[:60])}</td>
                <td><strong>{_html_escape(winner_label)}</strong></td>
                <td>{_html_escape(p.resolution[:80])}</td>
            </tr>
            '''
        
        html += '</tbody></table>'
    
    return html


def _render_comparison_html(report: FinalCodingReport) -> str:
    """Render AI vs Human comparison as HTML."""
    comp = report.comparison_result
    if not comp or not comp.has_human_input:
        return ''
    
    hi = report.human_code_input
    s = comp.summary
    coder = hi.coder_name if hi else "Human Coder"
    
    html = f'<h2 class="section-header">🔄 AI vs Human Comparison</h2>'
    html += f'<p class="info">Comparison with human coder: <strong>{_html_escape(coder)}</strong></p>'
    
    # Statistics table
    html += '''
    <table class="stats-table">
    <tr><td>Total AI codes (post-debate)</td><td>''' + str(s.total_ai_codes) + '''</td></tr>
    <tr><td>Total human codes</td><td>''' + str(s.total_human_codes) + '''</td></tr>
    <tr><td>Exact matches</td><td>''' + str(s.exact_matches) + '''</td></tr>
    <tr><td>AI-only codes</td><td>''' + str(s.ai_only_codes) + '''</td></tr>
    <tr><td>Human-only codes</td><td>''' + str(s.human_only_codes) + '''</td></tr>
    <tr><td>Unit/quantity mismatches</td><td>''' + str(s.discrepancies) + '''</td></tr>
    <tr class="separator"><td colspan="2"></td></tr>
    <tr><td>Overall match rate</td><td><strong>''' + f'{s.overall_match_rate*100:.1f}%' + '''</strong></td></tr>
    <tr><td>ICD-10 match rate</td><td><strong>''' + f'{s.icd10_match_rate*100:.1f}%' + '''</strong></td></tr>
    <tr><td>CPT match rate</td><td><strong>''' + f'{s.cpt_match_rate*100:.1f}%' + '''</strong></td></tr>
    <tr><td>HCPCS match rate</td><td><strong>''' + f'{s.hcpcs_match_rate*100:.1f}%' + '''</strong></td></tr>
    <tr class="separator"><td colspan="2"></td></tr>
    <tr><td>AI accuracy vs human</td><td><strong>''' + f'{s.ai_accuracy_vs_human*100:.1f}%' + '''</strong></td></tr>
    <tr><td>Human agreement with AI</td><td><strong>''' + f'{s.human_accuracy_vs_ai*100:.1f}%' + '''</strong></td></tr>
    </table>
    '''
    
    # Matched codes
    if comp.matched_codes:
        html += '<h3 class="section-title">✅ Agreed Codes</h3>'
        html += '<table class="codes-table"><thead><tr><th>Code</th><th>Type</th><th>Description</th><th>AI Confidence</th></tr></thead><tbody>'
        for m in comp.matched_codes:
            html += f'''<tr>
                <td class="code-cell">{_html_escape(m.code)}</td>
                <td class="dim">{_html_escape(m.code_type)}</td>
                <td>{_html_escape(m.description)}</td>
                <td>{_confidence_bar_css(m.ai_confidence)}</td>
            </tr>'''
        html += '</tbody></table>'
    
    # Discrepancies
    if comp.discrepancies:
        html += '<h3 class="section-title warning">⚠️ Discrepancies</h3>'
        html += '<table class="codes-table"><thead><tr><th>Type</th><th>Code</th><th>AI Code</th><th>Human Code</th><th>Severity</th><th>Impact</th></tr></thead><tbody>'
        for d in comp.discrepancies:
            severity_color = {"low": "#22c55e", "medium": "#eab308", "high": "#ef4444"}.get(d.severity.lower(), "#6b7280")
            html += f'''<tr>
                <td><strong>{_html_escape(d.discrepancy_type)}</strong></td>
                <td class="code-cell">{_html_escape(d.code)}</td>
                <td class="dim">{_html_escape(d.ai_code or '—')}</td>
                <td class="dim">{_html_escape(d.human_code or '—')}</td>
                <td><span style="color: {severity_color}; font-weight: bold;">{_html_escape(d.severity.upper())}</span></td>
                <td>{_html_escape(d.clinical_impact)}</td>
            </tr>'''
        html += '</tbody></table>'
    
    return html


def _render_human_codes_section(report: FinalCodingReport) -> str:
    """Render human-provided codes section as HTML."""
    hi = report.human_code_input
    if not hi:
        return ''
    
    has_codes = (
        (hi.icd10_codes and len(hi.icd10_codes) > 0) or
        (hi.cpt_codes and len(hi.cpt_codes) > 0) or
        (hi.hcpcs_codes and len(hi.hcpcs_codes) > 0)
    )
    
    if not has_codes:
        return ''
    
    html = '<h2 class="section-header">👤 Human Coder Input</h2>'
    coder = hi.coder_name or 'Human Coder'
    html += f'<p class="info">Codes provided by: <strong>{_html_escape(coder)}</strong></p>'
    
    # Create a grid layout for the codes
    html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0;">'
    
    # ICD-10
    if hi.icd10_codes and len(hi.icd10_codes) > 0:
        html += f'''
        <div style="background: #f0f9ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 15px;">
            <h3 style="color: #1e40af; font-size: 14px; font-weight: bold; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em;">
                ICD-10 ({len(hi.icd10_codes)})
            </h3>
            <div style="display: flex; flex-direction: column; gap: 8px;">
        '''
        for code in hi.icd10_codes:
            html += f'''
                <div style="background: white; padding: 8px 12px; border-radius: 4px; border-left: 3px solid #1e40af; font-family: 'Courier New', monospace; font-weight: bold; color: #1e40af;">
                    {_html_escape(code.code)}
                </div>
            '''
        html += '</div></div>'
    
    # CPT
    if hi.cpt_codes and len(hi.cpt_codes) > 0:
        html += f'''
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 15px;">
            <h3 style="color: #15803d; font-size: 14px; font-weight: bold; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em;">
                CPT ({len(hi.cpt_codes)})
            </h3>
            <div style="display: flex; flex-direction: column; gap: 8px;">
        '''
        for code in hi.cpt_codes:
            html += f'''
                <div style="background: white; padding: 8px 12px; border-radius: 4px; border-left: 3px solid #15803d; font-family: 'Courier New', monospace; font-weight: bold; color: #15803d;">
                    {_html_escape(code.code)}
                </div>
            '''
        html += '</div></div>'
    
    # HCPCS
    if hi.hcpcs_codes and len(hi.hcpcs_codes) > 0:
        html += f'''
        <div style="background: #fdfce8; border: 1px solid #fef08a; border-radius: 6px; padding: 15px;">
            <h3 style="color: #854d0e; font-size: 14px; font-weight: bold; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em;">
                HCPCS ({len(hi.hcpcs_codes)})
            </h3>
            <div style="display: flex; flex-direction: column; gap: 8px;">
        '''
        for code in hi.hcpcs_codes:
            html += f'''
                <div style="background: white; padding: 8px 12px; border-radius: 4px; border-left: 3px solid #854d0e; font-family: 'Courier New', monospace; font-weight: bold; color: #854d0e;">
                    {_html_escape(code.code)}
                </div>
            '''
        html += '</div></div>'
    
    html += '</div>'
    return html


def _render_compliance_html(comp: Optional[ComplianceResult]) -> str:
    """Render compliance findings as HTML."""
    if not comp:
        return ''
    
    html = '<h2 class="section-header">📋 Compliance & Risk Assessment</h2>'
    
    status_color = "#22c55e" if comp.is_compliant else "#ef4444"
    status_text = "✅ COMPLIANT" if comp.is_compliant else "❌ NON-COMPLIANT"
    
    html += f'<div class="compliance-status" style="border-left: 4px solid {status_color};">'
    html += f'<strong style="color: {status_color};">{status_text}</strong>'
    html += f'<p>{_html_escape(comp.summary)}</p></div>'
    
    # Violations detail (non-compliant claims)
    if not comp.is_compliant:
        html += '<h3 class="section-title warning">⚠️ Compliance Violations</h3>'
        html += '<table class="findings-table"><thead><tr><th>Type</th><th>Code(s)</th><th>Issue</th><th>Severity</th><th>Recommendation</th></tr></thead><tbody>'
        
        # NCCI violations
        for v in comp.ncci_violations:
            html += f'''<tr class="violation-row">
                <td><strong>NCCI Edit</strong></td>
                <td class="code-cell">{_html_escape(v.column1_code)} + {_html_escape(v.column2_code)}</td>
                <td>{_html_escape(v.description)}</td>
                <td><span style="color: #ef4444; font-weight: bold;">HIGH</span></td>
                <td>Remove or apply modifier. Allowed: {'Yes' if v.modifier_allowed else 'No'}</td>
            </tr>'''
        
        # MUE violations
        for v in comp.mue_violations:
            html += f'''<tr class="violation-row">
                <td><strong>MUE Limit</strong></td>
                <td class="code-cell">{_html_escape(v.cpt_code)}</td>
                <td>Billed {v.billed_units} units, CMS limit: {v.max_units}/day</td>
                <td><span style="color: #ef4444; font-weight: bold;">HIGH</span></td>
                <td>Reduce to {v.max_units} units or split across dates</td>
            </tr>'''
        
        # LCD issues
        for v in comp.lcd_issues:
            html += f'''<tr class="violation-row">
                <td><strong>LCD Issue</strong></td>
                <td>''' + ', '.join(v.applicable_codes) + f'''</td>
                <td>{_html_escape(v.description)}</td>
                <td><span style="color: #eab308; font-weight: bold;">MEDIUM</span></td>
                <td>Ensure documentation meets local coverage criteria</td>
            </tr>'''
        
        # NCD issues
        for v in comp.ncd_issues:
            html += f'''<tr class="violation-row">
                <td><strong>NCD Issue</strong></td>
                <td>''' + ', '.join(v.applicable_codes) + f'''</td>
                <td>{_html_escape(v.description)}</td>
                <td><span style="color: #eab308; font-weight: bold;">MEDIUM</span></td>
                <td>Verify patient meets national coverage criteria</td>
            </tr>'''
        
        # Missed codes
        for code in comp.missed_codes:
            extracted_code, description = _parse_missed_code(code)
            code_display = f'<span style="background: #fef08a; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{_html_escape(extracted_code)}</span>' if extracted_code else '(see description)'
            html += f'''<tr>
                <td><strong>Missed Code</strong></td>
                <td>{code_display}</td>
                <td>{_html_escape(description)}</td>
                <td><span style="color: #22c55e; font-weight: bold;">LOW</span></td>
                <td>Review documentation and add if supported</td>
            </tr>'''
        
        html += '</tbody></table>'
    
    # Advisory issues section (shows even for compliant claims if advisory issues exist)
    advisory_issues = comp.lcd_issues + comp.ncd_issues + [{"description": code} for code in comp.missed_codes]
    if comp.is_compliant and advisory_issues:
        html += '<h3 class="section-title" style="color: #d97706; border-bottom: 2px solid #f59e0b;">⚠️ Advisory Issues — Review Before Submission</h3>'
        html += '<table class="findings-table"><thead><tr><th>Type</th><th>Code(s)</th><th>Issue</th><th>Severity</th><th>Recommendation</th></tr></thead><tbody>'
        
        # LCD issues
        for v in comp.lcd_issues:
            html += f'''<tr>
                <td><strong>LCD Issue</strong></td>
                <td>''' + ', '.join(v.applicable_codes) + f'''</td>
                <td>{_html_escape(v.description)}</td>
                <td><span style="color: #eab308; font-weight: bold;">ADVISORY</span></td>
                <td>Ensure documentation meets local coverage criteria</td>
            </tr>'''
        
        # NCD issues
        for v in comp.ncd_issues:
            html += f'''<tr>
                <td><strong>NCD Issue</strong></td>
                <td>''' + ', '.join(v.applicable_codes) + f'''</td>
                <td>{_html_escape(v.description)}</td>
                <td><span style="color: #eab308; font-weight: bold;">ADVISORY</span></td>
                <td>Verify patient meets national coverage criteria</td>
            </tr>'''
        
        # Missed codes
        for code in comp.missed_codes:
            extracted_code, description = _parse_missed_code(code)
            code_display = f'<span style="background: #fef08a; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{_html_escape(extracted_code)}</span>' if extracted_code else '(see description)'
            html += f'''<tr>
                <td><strong>Missed Code</strong></td>
                <td>{code_display}</td>
                <td>{_html_escape(description)}</td>
                <td><span style="color: #22c55e; font-weight: bold;">LOW</span></td>
                <td>Review documentation and add if supported</td>
            </tr>'''
        
        html += '</tbody></table>'
    
    return html


def _render_scores_html(report: FinalCodingReport) -> str:
    """Render confidence and risk scores as HTML."""
    if not report.confidence_scores:
        return ''
    
    sc = report.confidence_scores
    
    html = '<h2 class="section-header">📊 Confidence & Risk Scores</h2>'
    html += '<div class="scores-grid">'
    
    # Confidence scores
    html += '<div class="score-section">'
    html += '<h3>Coding Confidence (higher is better)</h3>'
    html += f'<div class="score-item"><span>Overall Coding Confidence</span>{_confidence_bar_css(sc.overall_coding_confidence)}</div>'
    html += f'<div class="score-item"><span>ICD-10 Confidence</span>{_confidence_bar_css(sc.icd10_confidence)}</div>'
    html += f'<div class="score-item"><span>CPT Confidence</span>{_confidence_bar_css(sc.cpt_confidence)}</div>'
    html += f'<div class="score-item"><span>HCPCS Confidence</span>{_confidence_bar_css(sc.hcpcs_confidence)}</div>'
    html += '</div>'
    
    # Risk score (inverted — high is bad)
    html += '<div class="score-section">'
    html += '<h3>Compliance Risk (lower is better)</h3>'
    
    risk_percentage = int(sc.compliance_risk_score * 100)
    if sc.compliance_risk_score >= 0.70:
        risk_color = "#ef4444"  # red
    elif sc.compliance_risk_score >= 0.40:
        risk_color = "#eab308"  # yellow
    else:
        risk_color = "#22c55e"  # green
    
    html += f'''
    <div class="score-item">
        <span>Risk Score</span>
        <div class="score-bar">
            <div class="score-fill" style="width: {risk_percentage}%; background-color: {risk_color};"></div>
            <span class="score-text">{risk_percentage:.0f}%</span>
        </div>
    </div>
    <div class="score-item">
        <span>Risk Level</span>
        <span style="color: {_risk_color_css(sc.risk_level)}; font-weight: bold;">{_html_escape(sc.risk_level.upper())}</span>
    </div>
    '''
    
    # Comparison scores
    if sc.comparison_available:
        html += f'''
        <div class="score-item"><span>AI vs Human Match Rate</span>{_confidence_bar_css(sc.comparison_confidence)}</div>
        <div class="score-item"><span>AI Accuracy vs Human</span>{_confidence_bar_css(sc.human_agreement_rate)}</div>
        '''
    
    # Debate agreement
    if sc.clinical_vs_revenue_agreement > 0:
        html += f'<div class="score-item"><span>Clinical vs Revenue Agreement</span>{_confidence_bar_css(sc.clinical_vs_revenue_agreement)}</div>'
    
    html += '</div>'  # scores-grid
    html += '</div>'
    
    return html


def generate_html_report(report: FinalCodingReport) -> str:
    """Generate complete HTML report from FinalCodingReport."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Medical Coding AI — Final Compliance Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Helvetica Neue', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            line-height: 1.7;
            color: #2d3748;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 30px 20px;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 15px 10px;
            }}
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 50px 45px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
        }}
        
        @media print {{
            * {{
                -webkit-print-color-adjust: exact !important;
                color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            body {{
                background: white;
                padding: 0;
                margin: 0;
                width: 100%;
            }}
            .container {{
                max-width: 100%;
                box-shadow: none;
                margin: 0;
                padding: 20px;
                background: white;
            }}
            .page-break {{
                page-break-before: always;
            }}
            table {{
                page-break-inside: avoid;
                margin: 10px 0 !important;
            }}
            .section-header {{
                page-break-after: avoid;
                page-break-inside: avoid;
            }}
            .section-title {{
                page-break-after: avoid;
            }}
            tr {{
                page-break-inside: avoid;
            }}
            .meta-info, .clinical-note, .panel, .debate-scoreboard, 
            .compliance-status, .recommendations, .audit-summary, .justifications {{
                page-break-inside: avoid;
            }}
            .score-bar .score-fill {{
                border: 1px solid #333;
            }}
            .violation-row {{
                background: #f5f5f5 !important;
            }}
            thead {{
                display: table-header-group;
            }}
            tfoot {{
                display: table-footer-group;
            }}
        }}
        
        .header {{
            background: linear-gradient(135deg, #1f8a7a 0%, #2ba89d 100%);
            color: white;
            padding: 35px;
            margin: -50px -45px 40px -45px;
            border-radius: 12px 12px 0 0;
        }}
        
        .header h1 {{
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 10px;
            letter-spacing: -0.5px;
        }}
        
        .header p {{
            color: rgba(255, 255, 255, 0.9);
            font-size: 15px;
            font-weight: 400;
        }}
        
        .meta-info {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 35px;
            padding: 15px 20px;
            background: #f8fafc;
            border-radius: 8px;
            border-left: 4px solid #1f8a7a;
        }}
        
        .meta-item {{
            font-size: 13px;
            color: #2d3748;
            font-weight: 500;
        }}
        
        .meta-item strong {{
            display: inline;
            color: #1f8a7a;
            font-weight: 600;
        }}
        
        .meta-item span {{
            color: #718096;
        }}
        
        .section-header {{
            color: #1a202c;
            font-size: 24px;
            font-weight: 700;
            margin: 45px 0 25px 0;
            padding-bottom: 12px;
            border-bottom: 3px solid #1f8a7a;
            letter-spacing: -0.3px;
        }}
        
        .section-title {{
            color: #2d3748;
            font-size: 17px;
            font-weight: 600;
            margin: 25px 0 18px 0;
            letter-spacing: -0.2px;
        }}
        
        .section-title.warning {{
            color: #e53e3e;
        }}
        
        .clinical-note {{
            background: linear-gradient(135deg, #f0fdf9 0%, #e6f8f5 100%);
            border-left: 5px solid #1f8a7a;
            padding: 18px;
            margin: 20px 0;
            border-radius: 8px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
            color: #1a202c;
        }}
        
        .warning {{
            color: #c05621;
            padding: 12px 15px;
            background: #fef5e7;
            border-left: 4px solid #f39c12;
            margin: 12px 0;
            border-radius: 6px;
            font-size: 13px;
        }}
        
        .info {{
            color: #0e5a8a;
            padding: 12px 15px;
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            margin: 12px 0;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
        }}
        
        .panel {{
            background: #f8fafc;
            border: 1px solid #cbd5e0;
            padding: 18px;
            border-radius: 8px;
            margin: 18px 0;
        }}
        
        .panel strong {{
            color: #1a202c;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 13px;
        }}
        
        table.codes-table {{
            font-size: 12px;
        }}
        
        th {{
            background: linear-gradient(135deg, #1f8a7a 0%, #2ba89d 100%);
            color: white;
            padding: 14px 12px;
            text-align: left;
            font-weight: 600;
            border: none;
        }}
        
        td {{
            padding: 12px 12px;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        tr:nth-child(even) {{
            background: #f8fafc;
        }}
        
        tr:hover {{
            background: #edf2f7;
        }}
        
        .code-cell {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-weight: 700;
            color: #e53e3e;
            width: 100px;
        }}
        
        .center {{
            text-align: center;
        }}
        
        .dim {{
            color: #718096;
        }}
        
        .violation-row {{
            background: #fff5f5;
        }}
        
        tr.separator {{
            height: 8px;
            background: none;
        }}
        
        tr.separator td {{
            border: none;
            padding: 0;
            background: none;
        }}
        
        .score-bar {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 10px 0;
        }}
        
        .score-fill {{
            height: 26px;
            border-radius: 6px;
            flex: 1;
            max-width: 200px;
            position: relative;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .score-text {{
            font-weight: 700;
            min-width: 50px;
            text-align: right;
            color: #1a202c;
            font-size: 12px;
        }}
        
        .scores-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
            gap: 28px;
            margin: 25px 0;
        }}
        
        .score-section {{
            background: linear-gradient(135deg, #f0fdf9 0%, #e6f8f5 100%);
            padding: 24px;
            border-radius: 10px;
            border: 1px solid #d1e8e4;
        }}
        
        .score-section h3 {{
            color: #1a202c;
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 18px;
            letter-spacing: -0.2px;
        }}
        
        .score-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding: 0;
        }}
        
        .score-item span {{
            font-size: 13px;
            color: #2d3748;
            min-width: 220px;
            font-weight: 500;
        }}
        
        .debate-scoreboard {{
            background: linear-gradient(135deg, #f0fdf9 0%, #e6f8f5 100%);
            padding: 24px;
            border-radius: 10px;
            margin: 25px 0;
            border: 1px solid #d1e8e4;
        }}
        
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 14px 0;
            border-bottom: 1px solid #cbd5e0;
            font-size: 14px;
        }}
        
        .stat-row:last-child {{
            border-bottom: none;
        }}
        
        .stat-label {{
            color: #2d3748;
            font-weight: 600;
        }}
        
        .stat-value {{
            color: #1f8a7a;
            font-weight: 700;
            font-size: 17px;
        }}
        
        .stat-row.warning-row .stat-value {{
            color: #e53e3e;
        }}
        
        .compliance-status {{
            padding: 18px;
            margin: 20px 0;
            border-radius: 8px;
            background: #f8fafc;
            border-left: 5px solid #1f8a7a;
        }}
        
        h3 {{
            color: #1a202c;
            font-size: 16px;
            font-weight: 700;
            margin: 18px 0 12px 0;
            letter-spacing: -0.2px;
        }}
        
        .recommendations {{
            background: linear-gradient(135deg, #f0fdf4 0%, #e6fffa 100%);
            border-left: 5px solid #22863a;
            padding: 22px;
            margin: 25px 0;
            border-radius: 8px;
        }}
        
        .recommendations li {{
            color: #22863a;
            margin-bottom: 10px;
            list-style: none;
            font-weight: 500;
        }}
        
        .recommendations li:before {{
            content: "✓ ";
            font-weight: 700;
            margin-right: 10px;
        }}
        
        .audit-summary {{
            background: linear-gradient(135deg, #f0fdf9 0%, #e6f8f5 100%);
            border-left: 5px solid #1f8a7a;
            padding: 22px;
            margin: 25px 0;
            border-radius: 8px;
            color: #0c4a6e;
            line-height: 1.7;
            font-weight: 500;
        }}
        
        .footer {{
            margin-top: 60px;
            padding-top: 25px;
            border-top: 2px solid #e2e8f0;
            color: #718096;
            font-size: 12px;
            text-align: center;
        }}
        
        .footer p {{
            margin-bottom: 8px;
        }}
        
        .justifications {{
            background: linear-gradient(135deg, #fef9e7 0%, #fff9e6 100%);
            border-left: 5px solid #d4af37;
            padding: 22px;
            margin: 25px 0;
            border-radius: 8px;
        }}
        
        .justifications p {{
            color: #664d03;
            margin-bottom: 10px;
            font-weight: 500;
        }}
        
        .findings-table {{
            font-size: 13px;
        }}
        
        .stats-table {{
            font-size: 13px;
        }}
        
        .stats-table tr:nth-child(odd) {{
            background: #f8fafc;
        }}
        
        .stats-table tr:hover {{
            background: #edf2f7;
        }}
        
        .stats-table td:first-child {{
            font-weight: 600;\n            color: #2d3748;
        }}
        
        .stats-table td:last-child {{
            font-weight: 700;
            color: #667eea;
        }}
        
        @media print {{
            .no-print {{
                display: none;
            }}
            .section-header {{
                page-break-before: always;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Medical Coding AI — Final Compliance Report</h1>
            <p>Automated coding analysis with compliance assessment, debate resolution, and human comparison</p>
        </div>
        
        <div class="meta-info">
            <div class="meta-item">
                <span>Generated: {timestamp}</span>
            </div>
        </div>
        
        <!-- Clinical Note -->
        <h2 class="section-header">📝 Clinical Note Summary</h2>
        <div class="clinical-note">{_html_escape(report.patient_note_excerpt)}</div>
        
        <!-- Per-Agent Codes -->
        <h2 class="section-header">🏥 Per-Agent Analysis</h2>
        {_render_agent_codes_html(report.clinical_agent_codes, "🏥 Clinical Accuracy Agent")}
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
        {_render_agent_codes_html(report.revenue_agent_codes, "💰 Revenue Optimization Agent")}
        
        <!-- Debate -->
        {_render_debate_html(report.debate_result)}
        
        <!-- Final Codes -->
        <h2 class="section-header">📋 Final Resolved Codes (Post-Debate)</h2>
        
        {('<h3 class="section-title">ICD-10-CM Codes</h3><table class="codes-table"><thead><tr><th>Code</th><th>Description</th><th>Type</th><th>Confidence</th></tr></thead><tbody>' +
          ''.join(f'<tr><td class="code-cell">{_html_escape(c.get("code",""))}</td><td>{_html_escape(c.get("description",""))}</td><td>{_html_escape(c.get("type",""))}</td><td>{_confidence_bar_css(float(c.get("confidence",0)))}</td></tr>' for c in report.icd10_codes) +
          '</tbody></table>') if report.icd10_codes else '<p class="dim">No ICD-10 codes</p>'}
        
        {('<h3 class="section-title">CPT Codes</h3><table class="codes-table"><thead><tr><th>Code</th><th>Description</th><th>Units</th><th>Confidence</th></tr></thead><tbody>' +
          ''.join(f'<tr><td class="code-cell">{_html_escape(c.get("code",""))}</td><td>{_html_escape(c.get("description",""))}</td><td class="center">{c.get("units",1)}</td><td>{_confidence_bar_css(float(c.get("confidence",0)))}</td></tr>' for c in report.cpt_codes) +
          '</tbody></table>') if report.cpt_codes else '<p class="dim">No CPT codes</p>'}
        
        {('<h3 class="section-title">HCPCS Codes</h3><table class="codes-table"><thead><tr><th>Code</th><th>Description</th><th>Category</th><th>Units</th></tr></thead><tbody>' +
          ''.join(f'<tr><td class="code-cell">{_html_escape(c.get("code",""))}</td><td>{_html_escape(c.get("description",""))}</td><td>{_html_escape(c.get("category",""))}</td><td class="center">{c.get("units",1)}</td></tr>' for c in report.hcpcs_codes) +
          '</tbody></table>') if report.hcpcs_codes else '<p class="dim">No HCPCS codes</p>'}
        
        <!-- Human Codes Input -->
        {_render_human_codes_section(report)}
        
        <!-- Comparison -->
        {_render_comparison_html(report)}
        
        <!-- Compliance -->
        {_render_compliance_html(report.compliance_result)}
        
        <!-- Audit Findings -->
        {('<h2 class="section-header">🔍 Audit Findings</h2><table class="findings-table"><thead><tr><th>Type</th><th>Code</th><th>Finding</th><th>Severity</th><th>Recommendation</th></tr></thead><tbody>' +
          ''.join(f'<tr><td><strong>{_html_escape(f.finding_type)}</strong></td><td class="code-cell">{_html_escape(f.code)}</td><td>{_html_escape(f.description)}</td><td><span style="color: {_risk_color_css(f.severity)}; font-weight: bold;">{_html_escape(f.severity.upper())}</span></td><td>{_html_escape(f.recommendation)}</td></tr>' for f in report.audit_findings) +
          '</tbody></table>') if report.audit_findings else ''}
        
        <!-- Justifications -->
        {('<h2 class="section-header">💡 Code Justifications</h2><div class="justifications">' +
          ''.join(f'<p><strong>{_html_escape(j.code)}:</strong> {_html_escape(j.explanation)}</p>' for j in report.justifications) +
          '</div>') if report.justifications else ''}
        
        <!-- Scores -->
        {_render_scores_html(report)}
        
        <!-- Recommendations -->
        {('<h2 class="section-header">🎯 Recommendations</h2><div class="recommendations"><ul>' +
          ''.join(f'<li>{_html_escape(r)}</li>' for r in report.recommendations) +
          '</ul></div>') if report.recommendations else ''}
        
        <!-- Audit Summary -->
        {f'<h2 class="section-header">📊 Audit Summary</h2><div class="audit-summary">{_html_escape(report.audit_summary)}</div>' if report.audit_summary else ''}
        
        <div class="footer">
            <p>Report generated: {timestamp}</p>
            <p style="margin-top:18px;font-size:12px;color:#718096;">This report contains comprehensive compliance analysis. Review all high-severity findings before claim submission.</p>
        </div>
    </div>
</body>
</html>'''
    
    return html_content


def save_report(report: FinalCodingReport, report_dir: str = "reports", filename: Optional[str] = None) -> Path:
    """
    Save FinalCodingReport as complete HTML file.
    
    Args:
        report: FinalCodingReport object
        report_dir: Directory to save report (default: "reports")
        filename: Optional custom filename (default: auto-generated with timestamp)
    
    Returns:
        Path object pointing to saved HTML file
    """
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_generate_{timestamp}.html"
    
    # Ensure .html extension
    if not filename.endswith('.html'):
        filename += '.html'
    
    file_path = report_path / filename
    
    # Generate HTML content
    html_content = generate_html_report(report)
    
    # Write to file
    try:
        file_path.write_text(html_content, encoding='utf-8')
        return file_path
    except IOError as e:
        raise IOError(f"Failed to save report to {file_path}: {e}")


if __name__ == "__main__":
    # Quick test
    print("HTML Report module loaded. Use save_report(report) to generate HTML.")
