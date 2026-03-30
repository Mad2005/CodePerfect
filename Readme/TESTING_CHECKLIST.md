# Testing Checklist for Modern Medical Coding UI

Use this checklist to verify all features work correctly after deployment.

## Pre-Flight Checks

- [ ] Flask server starts without errors
- [ ] No Python import errors
- [ ] Vector database loads successfully
- [ ] Uploads and reports directories exist
- [ ] Port 5000 (or configured port) is available

## UI Rendering

- [ ] Home page loads with logo and app title
- [ ] Navigation bar displays correctly
- [ ] All nav items are clickable
- [ ] Page doesn't have console errors
- [ ] Responsive on mobile (test with F12 DevTools)
- [ ] All images/icons load properly
- [ ] Colors match design spec

## Navigation

- [ ] Home link navigates to home page
- [ ] Auto Coding link navigates to auto coding mode
- [ ] Assisted Coding link navigates to assisted coding mode
- [ ] Reports link navigates to reports page
- [ ] Nav items show active state
- [ ] Navigation is instant (no full page reload)

## Home Page

- [ ] Logo and title display
- [ ] App description shows
- [ ] Two mode cards appear
- [ ] Mode cards are clickable
- [ ] "How It Works" section shows 4 steps
- [ ] Gradient background displays
- [ ] Layout is centered and clean

## Auto Coding Mode

### UI Elements
- [ ] Page title: "Auto Coding Mode"
- [ ] Page description displays
- [ ] "Clinical Notes" label shows
- [ ] Drag-and-drop zone displays with icon
- [ ] File upload text shows supported formats
- [ ] "Or paste" section displays
- [ ] Textarea is visible and editable
- [ ] "Generate Codes" button appears
- [ ] "Clear" button appears

### File Upload
- [ ] Click upload zone opens file picker
- [ ] Accepts .txt files
- [ ] Accepts .pdf files
- [ ] Accepts .doc/.docx files
- [ ] File name displays after selection
- [ ] Error shown for unsupported format
- [ ] Error shown if file too large

### Text Input
- [ ] Textarea accepts pasted text
- [ ] Text can be entered/edited freely
- [ ] Clear button removes text
- [ ] Form validates required fields

### Form Submission
- [ ] Without input, shows error notification
- [ ] Processing overlay appears on submit
- [ ] Overlay centers on screen
- [ ] Spinner animates
- [ ] Processing steps display
- [ ] Steps progress in order
- [ ] Each step shows checkmark when done
- [ ] Current step shows active indicator

### Error Handling
- [ ] Invalid file format shows error
- [ ] Empty submission shows error message
- [ ] Network error displays notification
- [ ] Error notification auto-dismisses

## Assisted Coding Mode

### UI Elements
- [ ] Page title: "Assisted Coding Mode"
- [ ] Page description displays
- [ ] Two-column layout (Clinical + Codes)
- [ ] Left column: Clinical Notes
- [ ] Right column: Human-Entered Codes
- [ ] Both textareas visible
- [ ] "Validate & Enhance Codes" button appears
- [ ] "Clear" button appears

### Input Handling
- [ ] Clinical notes textarea works
- [ ] Codes textarea works
- [ ] Multiple codes can be entered (one per line)
- [ ] Codes are trimmed of whitespace
- [ ] Clear button clears both fields

### Validation
- [ ] Both fields required for submission
- [ ] Error if clinical notes is empty
- [ ] Error if codes field is empty
- [ ] Error if codes format is invalid
- [ ] Valid formats accepted:
  - [ ] ICD-10 (E11.9)
  - [ ] CPT (99214)
  - [ ] HCPCS (J1100)

## Processing State

### Overlay Display
- [ ] Processing overlay appears on screen
- [ ] Overlay is centered (50% top/left)
- [ ] Dark background overlay blocks interaction
- [ ] Overlay has rounded corners
- [ ] Overlay has shadow

### Progress Indicators
- [ ] Spinner animates smoothly
- [ ] Spinner uses primary blue color
- [ ] Processing title "Processing..." shows
- [ ] All steps listed with icons

### Step States
- [ ] Completed steps show ✓ (green)
- [ ] Active step shows ● (blue, pulsing)
- [ ] Pending steps show ○ (gray)
- [ ] Steps update properly over time
- [ ] "May take a few moments" message shows

### Processing Duration
- [ ] Processing takes reasonable time
- [ ] Each step takes ~1 second
- [ ] All steps complete successfully
- [ ] Processing completes without hanging

## Report Page

### Header Section
- [ ] Title: "Clinical Coding Report"
- [ ] Date/time generated displays
- [ ] "Generate New Report" button shows
- [ ] Button navigates back to auto coding

### Clinical Summary (Card 1)
- [ ] Section title displays with icon
- [ ] Summary text shows clinical overview
- [ ] Card has white background
- [ ] Card has shadow effect
- [ ] Card has border

### Extracted Diagnoses (Card 2)
- [ ] Section title displays with icon
- [ ] Diagnoses appear as individual cards
- [ ] Each diagnosis has checkmark icon
- [ ] Diagnoses are green-colored
- [ ] Grid layout for multiple diagnosis

### Generated Codes (Card 3)
- [ ] Section title displays with icon
- [ ] Table structure appears
- [ ] Column headers: Code, Description, Confidence
- [ ] Table data rows populate
- [ ] Confidence shown as percentage (%)
- [ ] Confidence color coding:
  - [ ] >=90% green badge
  - [ ] >=80% yellow badge
  - [ ] <80% orange badge
- [ ] Code column uses monospace font

### Validation Results (Card 4)
- [ ] Section title displays with icon
- [ ] Success message appears in green
- [ ] Compliance status shows
- [ ] All results in status cards
- [ ] Cards have appropriate icons

### Footer Actions
- [ ] "View All Reports" button shows
- [ ] "Print Report" button shows
- [ ] Both buttons are styled correctly
- [ ] Print button opens print dialog

## Reports History Page

### Page Layout
- [ ] Title: "Report History"
- [ ] Description text shows
- [ ] Table structure displays

### Table Content
- [ ] Column headers: Title, Type, Generated, Actions
- [ ] Sample reports appear in table
- [ ] Report titles show
- [ ] Type badges appear (Auto/Assisted)
- [ ] Date/time shows for each report
- [ ] Action buttons visible

### Report Types
- [ ] Auto Coding reports show "Auto Coding" badge
- [ ] Assisted Coding reports show "Assisted Coding" badge
- [ ] Type badges have different colors

### Action Buttons
- [ ] "View" button opens report in page
- [ ] "New Tab" button opens in new tab
- [ ] Buttons are clickable
- [ ] Buttons have hover effect

### List Display
- [ ] All reports display in order
- [ ] Most recent first
- [ ] Report count shows at bottom

## API Integration

### Auto Coding API
- [ ] POST `/api/extract` called on submit
- [ ] Request includes clinical_note
- [ ] Response includes status: "ok"
- [ ] Response includes report data
- [ ] Response includes codes array
- [ ] Error response handled properly

### Assisted Coding API
- [ ] POST `/api/validate` called on submit
- [ ] Request includes clinical_note
- [ ] Request includes human_codes array
- [ ] Response includes status: "ok"
- [ ] Response includes comparison data
- [ ] Error response handled properly

### Other APIs
- [ ] GET `/api/reports` returns list
- [ ] GET `/api/sample/1` returns sample note
- [ ] GET `/api/db-status` returns status

## Notifications

### Success Notifications
- [ ] Report generated successfully message shows
- [ ] Message auto-dismisses after 4 seconds
- [ ] Green background color
- [ ] Appears in bottom-right corner

### Error Notifications
- [ ] Error messages display on failure
- [ ] Auto-dismisses after 4 seconds
- [ ] Red background color
- [ ] Contains error description

### Info Notifications
- [ ] Info messages display for user actions
- [ ] Blue background color
- [ ] Example: "Form cleared"

## Accessibility

- [ ] Page works without mouse (keyboard only)
- [ ] Focus indicators visible
- [ ] Tab navigation works
- [ ] Color contrast sufficient (text readable)
- [ ] Font sizes readable (14px+)
- [ ] No ARIA errors in console

## Performance

- [ ] Page loads in <3 seconds
- [ ] Navigation is instant
- [ ] Processing doesn't freeze UI
- [ ] Report displays quickly (<1 second)
- [ ] No memory leaks detected
- [ ] Console has no warnings or errors

## Cross-Browser Testing

- [ ] Works in Chrome
- [ ] Works in Firefox
- [ ] Works in Safari
- [ ] Works in Edge
- [ ] Works on mobile Safari (iOS)
- [ ] Works on Chrome Mobile (Android)

## Mobile Responsiveness

- [ ] Page is readable on mobile (360px width)
- [ ] Buttons are touch-friendly (44px+ height)
- [ ] Text is readable without zooming
- [ ] Forms are mobile-optimized
- [ ] Navigation works on mobile
- [ ] Layout adapts to screen size
- [ ] Two-column layouts stack on mobile

## Error Scenarios

### Network Errors
- [ ] Connection timeout shows error
- [ ] HTTP 400 error handled
- [ ] HTTP 500 error handled
- [ ] Error message is user-friendly

### Input Errors
- [ ] Empty clinical note shows error
- [ ] Invalid code format shows error
- [ ] Missing field shows error
- [ ] Error messages are clear

### Backend Errors
- [ ] Report generation failure handled
- [ ] Database errors shown correctly
- [ ] API failures don't crash page
- [ ] User can retry on error

## Sample Data

- [ ] Load sample 1 works
- [ ] Load sample 2 works
- [ ] Load sample 3 works
- [ ] Load sample 4 works
- [ ] Sample text loads into textarea
- [ ] Can auto-code loaded sample
- [ ] Can validate sample with codes

## Print Functionality

- [ ] Print button visible on report
- [ ] Print button opens print dialog
- [ ] Report prints cleanly
- [ ] Report saves to PDF
- [ ] Formatting preserved in print
- [ ] All sections appear in print

## Dark Mode (Future)

- [ ] Color scheme can be toggled (when implemented)
- [ ] All colors adapt to dark theme
- [ ] Text remains readable
- [ ] No eye strain in dark mode

## Advanced Features (Future)

- [ ] CSV export button works (when implemented)
- [ ] JSON export button works (when implemented)
- [ ] Report comparison works (when implemented)
- [ ] Search functionality works (when implemented)

## Final Verification

- [ ] No console errors (F12)
- [ ] No console warnings
- [ ] All tests pass ✓
- [ ] Ready for production deployment
- [ ] User documentation complete
- [ ] API documentation complete
- [ ] Team trained on new interface

## Notes

Record any issues found here:

```
[Issue #1]
Description:
Steps to Reproduce:
Expected Result:
Actual Result:
Browser/OS:
Screenshots:

[Issue #2]
...
```

## Sign-off

- [ ] QA Lead: _________________________ Date: _______
- [ ] Product Owner: _________________ Date: _______
- [ ] DevOps: ________________________ Date: _______

---

**Total Tests:** 100+  
**Estimated Time:** 30-45 minutes  
**Pass Criteria:** All tests pass or issues documented
