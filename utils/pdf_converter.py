"""
Report Download Helper — HTML Report Serving
─────────────────────────────────────────────
Provides utilities for serving HTML reports for download.
Users can print/save as PDF using browser's native print-to-PDF feature.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_html_report(html_path: Path) -> str:
    """
    Read HTML report file.
    
    Args:
        html_path: Path to the HTML file
        
    Returns:
        str: HTML content or error message
    """
    if not html_path.exists():
        logger.error(f"HTML file not found: {html_path}")
        return ""
    
    try:
        html_content = html_path.read_text(encoding='utf-8')
        logger.info(f"Successfully read {html_path.name}")
        return html_content
    except Exception as e:
        logger.error(f"Failed to read HTML report: {str(e)}")
        return ""
