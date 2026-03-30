# Modern Medical Coding UI

A clean, professional, hospital-style web application for AI-powered medical coding. This modern UI replaces the previous templates with a single-page application built with vanilla JavaScript and Tailwind CSS.

## Features

### 🏠 Home Page
- Professional landing page with system overview
- Two prominent action buttons for each coding mode
- "How It Works" visual guide
- Hospital-style design with blue/white/gray color scheme

### ⚡ Auto Coding Mode
- Upload clinical documents (TXT, PDF, DOC, DOCX)
- Paste clinical notes directly
- One-click code generation
- No manual code input required

### 🔍 Assisted Coding Mode
- Upload/paste clinical notes
- Input human-coded entries
- Validate and enhance with AI suggestions
- Side-by-side comparison

### 📊 Processing Flow
- Real-time step-by-step progress tracking
- Animated processing overlay
- Visual indicators for completed/active/pending steps
- Examples:
  - "Analyzing clinical notes..."
  - "Extracting clinical entities..."
  - "Generating medical codes..."
  - "Validating compliance..."
  - "Finalizing report..."

### 📋 Report Generation
- Patient Clinical Summary
- Extracted Diagnoses
- Generated Codes (with confidence scores)
- Validation Results
- Comprehensive tables and cards
- Print functionality
- Clean, professional formatting

### 📁 Reports History
- View all previously generated reports
- Sort by date and type
- Open reports in-page or new tab
- Quick navigation

## Design Principles

### Removed from UI
- ✗ PubMedBERT, LLM Agents, SNOMED CT, RxNorm, ICD-10, CPT, HCPCS terminology
- ✗ Dataset counts (SNOMED: 194.5k, etc.)
- ✗ Backend/model/framework details
- ✗ Technical internal information

### Visual Design
- Clean hospital dashboard style
- Soft blue/white/gray color palette
- Responsive mobile-friendly layout
- Smooth animations and transitions
- Readable typography (Inter font)
- Accessible UI components

## Technical Stack

- **Frontend**: HTML5 + Vanilla JavaScript (no frameworks needed)
- **Styling**: Tailwind CSS (CDN)
- **Icons**: Feather Icons (CDN)
- **Backend API**: Python Flask (existing)
- **State Management**: Client-side JavaScript object
- **Responsive**: Mobile, tablet, desktop support

## File Structure

```
templates/
├── index.html          # Single-page application (replaces home.html, generate.html, etc.)
├── _base.html          # (kept for backwards compatibility)
├── home.html           # (deprecated - redirects to index.html)
├── generate.html       # (deprecated - redirects to index.html)
├── compare.html        # (deprecated - redirects to index.html)
└── reports.html        # (deprecated - redirects to index.html)
```

## API Endpoints

### New Endpoints
- `POST /api/extract` - Auto coding (clinical notes only)
- `POST /api/validate` - Assisted coding (clinical notes + human codes)

### Existing Endpoints (Still Supported)
- `GET /api/reports` - List all reports
- `GET /api/db-status` - Database status
- `GET /api/sample/<n>` - Get sample clinical notes
- `POST /api/parse-codes` - Parse uploaded code files
- `POST /api/run` - Legacy endpoint (still works)

## Request/Response Examples

### Auto Coding Request
```json
{
  "clinical_note": "Patient presents with type 2 diabetes and hypertension..."
}
```

### Assisted Coding Request
```json
{
  "clinical_note": "Patient presents with type 2 diabetes...",
  "human_codes": ["E11.9", "I10", "99214"]
}
```

### Response Format
```json
{
  "status": "ok",
  "url": "/report/generate_1234567890.html",
  "mode": "auto",
  "summary": "Report generated successfully",
  "diagnoses": ["Type 2 Diabetes", "Hypertension"],
  "codes": [
    {
      "code": "E11.9",
      "description": "Type 2 diabetes mellitus without complications",
      "confidence": 95
    }
  ]
}
```

## Usage

### Starting the Application

```bash
python app.py --port 5000
```

The application will automatically open in your default browser at `http://localhost:5000`.

### User Flow

1. **Home Page**: User chooses between Auto or Assisted coding
2. **Input**: Upload/paste clinical notes (and human codes if assisted)
3. **Processing**: See real-time progress with step indicators
4. **Report**: View structured output with tables, cards, and metrics
5. **History**: Access previous reports from history page

## Customization

### Changing Colors
Edit the CSS variables in the `<style>` section of `index.html`:
- Primary: `--accent: #2563eb` (blue)
- Success: `--green: #16a34a`
- Purple: `--purple: #7c3aed`

### Adding More Processing Steps
Update the `startProcessing()` function call in the form handlers:
```javascript
const steps = [
  'Step 1...',
  'Step 2...',
  'Step 3...'
];
startProcessing(steps);
```

### Modifying Report Sections
Edit the `ReportPage()` function to add/remove sections or change layout.

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance

- Single HTML file (easy to cache)
- Tailwind CSS via CDN (optimized delivery)
- Minimal JavaScript (vanilla, no framework overhead)
- Responsive images and icons
- Fast page transitions

## Accessibility

- Semantic HTML5 structure
- ARIA labels where needed
- Keyboard navigation support
- High contrast color scheme
- Readable font sizes

## Future Enhancements

- [ ] Dark mode toggle
- [ ] Code export to CSV/Excel
- [ ] Report comparison tool
- [ ] Batch processing
- [ ] User authentication
- [ ] Audit logs
- [ ] Customizable report templates
- [ ] Email report delivery

## Support

For issues or questions:
1. Check the browser console for errors
2. Verify Flask backend is running
3. Check network requests in browser DevTools
4. Review Flask application logs
