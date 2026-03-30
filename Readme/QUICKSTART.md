# Medical Coding UI - Quick Start Guide

## Installation

### Prerequisites
- Python 3.8+
- Flask 3.0+
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Setup

1. **Clone/Navigate to Project**
   ```bash
   cd medical_coding_ai
   ```

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Initialize Vector Database** (if needed)
   ```bash
   python migrate.py
   ```

## Running the Application

### Start the Server
```bash
python app.py --port 5000
```

The application will automatically open at `http://localhost:5000`

### With Custom Port
```bash
python app.py --port 8080
```

### Disable Auto-Browser Open
```bash
python app.py --no-browser
```

## User Guide

### Home Page
- Landing page with system overview
- Choose between **Auto Coding** or **Assisted Coding** modes
- View "How It Works" guide

### Auto Coding Mode

**How to use:**
1. Click "Auto Coding Mode" from home page
2. Either:
   - Upload a document (TXT, PDF, DOC, DOCX)
   - Paste clinical notes directly
3. Click "Generate Codes"
4. Wait for processing (watch the progress steps)
5. Review the generated report

**Input:**
- Clinical documentation (discharge summary, operative note, consultation note, etc.)
- Any medical narrative text

**Output:**
- Clinical summary
- Extracted diagnoses
- Generated medical codes with confidence scores
- Validation results

### Assisted Coding Mode

**How to use:**
1. Click "Assisted Coding Mode" from home page
2. Paste clinical notes in left panel
3. Enter human-coded entries in right panel (one per line)
4. Click "Validate & Enhance Codes"
5. Review the enhanced report with comparison

**Input:**
- Clinical documentation (left panel)
- Human-entered codes (right panel, one per line)
- Example codes: E11.9, I10, 99214, A0123

**Output:**
- Clinical summary
- AI-generated codes
- Comparison with human codes
- Recommendations for improvement

### Processing Steps

During processing, you'll see real-time progress:
- ✓ Completed steps (green checkmark)
- ● Active step (blue dot)
- ○ Pending steps (gray circle)

### Viewing Reports

**From Report Page:**
- Click "View All Reports" to see history
- Click "Print Report" to print/save as PDF

**From Reports Page:**
- View table of all generated reports
- Click "View" to open in page
- Click "New Tab" to open in separate tab
- Sort by date or type

## Features & Tips

### Document Upload
- Supported formats: TXT, PDF, DOC, DOCX, RTF
- Maximum file size: 10 MB
- Automatically extracts text

### Code Input Formats
Supported medical code formats:
- **ICD-10**: E11.9, I10, N18.3 (diagnosis codes)
- **CPT**: 99213, 99214, 99215 (procedure codes)
- **HCPCS**: J1100, A0123, E1234 (supply codes)

### Processing Status
- Processing typically takes 10-30 seconds
- Longer notes may take more time
- Server will notify if there are errors

### Saving Reports
- Reports are automatically saved on server
- View history anytime in Reports page
- Print to PDF from report view

## Troubleshooting

### Issue: Page Won't Load
**Solution:**
- Check if Flask server is running
- Clear browser cache (Ctrl+Shift+Del)
- Try different browser
- Check port isn't blocked (default 5000)

### Issue: Upload Fails
**Solution:**
- Check file size < 10 MB
- Use supported format (PDF, DOCX, TXT)
- Try pasting text instead
- Check Flask logs for errors

### Issue: Long Processing Time
**Solution:**
- Normal for large documents
- Try shorter input first
- Check server CPU usage
- Review Flask logs

### Issue: Codes Not Generating
**Solution:**
- Ensure clinical note has enough detail
- Check code formatting if in Assisted mode
- Try sample note first
- Check browser console for errors

## Browser Console

If issues occur, check the browser console:

1. **Open DevTools**: F12 or Ctrl+Shift+I
2. **Go to Console tab**: See any JavaScript errors
3. **Go to Network tab**: Check API requests status
4. **Go to Application tab**: Check localStorage

## Report Examples

### Auto Coding Report
Example input:
```
Patient: 65-year-old male
Chief Complaint: Chest pain
History: Type II diabetes, hypertension
Exam: BP 160/95, HR 88, RR 16
Labs: Troponin 0.5 ng/mL (elevated)
Impression: Acute coronary syndrome, rule out MI
```

Example output:
- I20.0 (Unstable angina)
- E11.9 (Type 2 diabetes)
- I10 (Hypertension)
- 99213 (Office visit)

### Assisted Coding Report
Example input:
```
Clinical Note: Same as above
Human Codes: I20.0, E11.9, I10
```

Example output:
- AI suggests adding: 99214 (higher complexity)
- Validates human codes (all correct)
- Confidence: 95%+

## Advanced Usage

### Loading Sample Notes
1. From Auto Coding page, select from dropdown
2. Samples include: Diabetes, Appendicitis, Cardiac, Pneumonia
3. Perfect for testing the system

### Real-Time Validation
Processing steps show real-time feedback:
1. "Analyzing clinical notes..." - Reading input
2. "Extracting clinical entities..." - Finding conditions
3. "Generating medical codes..." - Creating codes
4. "Validating compliance..." - Checking against standards
5. "Finalizing report..." - Preparing output

## API Reference

For developers integrating with the API:

### Extract Codes
```bash
curl -X POST http://localhost:5000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"clinical_note": "Patient has diabetes and high blood pressure"}'
```

### Validate Codes
```bash
curl -X POST http://localhost:5000/api/validate \
  -H "Content-Type: application/json" \
  -d '{
    "clinical_note": "Patient has diabetes",
    "human_codes": ["E11.9", "I10"]
  }'
```

### Get Reports
```bash
curl http://localhost:5000/api/reports
```

## Performance Tips

1. **For Better Speed:**
   - Use concise clinical notes (500-2000 chars)
   - Ensure stable internet connection
   - Use modern browser (Chrome/Firefox)

2. **For Better Accuracy:**
   - Use complete clinical information
   - Include patient history
   - Mention all relevant diagnoses and procedures

3. **For Large Batches:**
   - Process one note at a time
   - Check history page between runs
   - Monitor server resources

## Configuration

UI configuration can be customized in `config/ui_config.json`:
- Theme colors
- Animation settings
- Processing timeout
- Report sections
- Feature flags

## Support & Debugging

1. **Check Logs:**
   ```bash
   # Flask logs output in terminal
   ```

2. **Browser Console:** F12 → Console tab

3. **Network Requests:** F12 → Network tab

4. **Local Storage:** F12 → Application → Local Storage

## Next Steps

- Explore both coding modes
- Try with different types of clinical notes
- Review report history
- Test with edge cases
- Provide feedback for improvements

---

**Version:** 2.0.0  
**Last Updated:** March 2026  
**Support:** Check Flask application logs for detailed error information
