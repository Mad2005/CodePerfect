#!/usr/bin/env python3
"""
Quick test script to verify report saving functionality.
Run this after making API calls to see if reports are being saved correctly.
"""

from pathlib import Path
from datetime import datetime
import json

def check_saved_reports():
    """List all saved reports with timestamps and sizes."""
    reports_dir = Path("reports")
    
    if not reports_dir.exists():
        print(f"❌ Reports directory not found: {reports_dir.resolve()}")
        return
    
    html_files = sorted(reports_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not html_files:
        print("⚠️  No reports found in reports/ directory")
        return
    
    print(f"\n✅ Found {len(html_files)} saved reports:\n")
    print(f"{'Filename':<40} {'Size (KB)':<12} {'Modified':<20}")
    print("─" * 75)
    
    for f in html_files[:10]:  # Show last 10
        size_kb = f.stat().st_size / 1024
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{f.name:<40} {size_kb:>10.1f}  {mtime}")
    
    # Check content of most recent report
    if html_files:
        latest = html_files[0]
        content = latest.read_text()
        
        print(f"\n📋 Latest Report: {latest.name}")
        print(f"   Size: {latest.stat().st_size / 1024:.1f} KB")
        
        # Check for key sections
        sections = {
            "Clinical Note": "Clinical Note Summary",
            "Agent Analysis": "Per-Agent Analysis",
            "Debate": "Debate Scoreboard",
            "Final Codes": "Final Resolved Codes",
            "Compliance": "Compliance &amp; Risk Assessment" ,
            "Audit Findings": "Audit Findings",
            "Recommendations": "Recommendations",
            "Scores": "Confidence &amp; Risk Scores",
        }
        
        print("\n   Sections included:")
        for name, search_text in sections.items():
            if search_text in content:
                print(f"   ✅ {name}")
            else:
                print(f"   ❌ {name} (missing)")
        
        # Check for print-optimized CSS
        if "@media print" in content and "print-color-adjust" in content:
            print("\n   ✅ Print/PDF optimized (enhanced print CSS found)")
        else:
            print("\n   ⚠️  Basic print support only")

if __name__ == "__main__":
    check_saved_reports()
