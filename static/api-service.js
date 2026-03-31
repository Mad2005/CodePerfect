/**
 * Medical Coding UI - API Service
 * 
 * Optional utility module for making API calls to the medical coding backend.
 * This can be imported separately if building custom integrations.
 * 
 * Usage:
 *   import { APIService } from './api-service.js';
 *   const api = new APIService('http://localhost:5000');
 *   const result = await api.extract(clinicalNote);
 */

export class APIService {
  constructor(baseUrl = window.location.origin) {
    this.baseUrl = baseUrl;
  }

  /**
   * Auto Code Generation
   * @param {string} clinicalNote - The clinical documentation text
   * @returns {Promise<Object>} Report data
   */
  async extract(clinicalNote) {
    if (!clinicalNote || typeof clinicalNote !== 'string') {
      throw new Error('Clinical note must be a non-empty string');
    }

    const response = await fetch(`${this.baseUrl}/api/extract`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        clinical_note: clinicalNote.trim(),
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Assisted Code Validation & Enhancement
   * @param {string} clinicalNote - The clinical documentation text
   * @param {string[]} humanCodes - Array of human-entered codes
   * @returns {Promise<Object>} Report data with comparison
   */
  async validate(clinicalNote, humanCodes) {
    if (!clinicalNote || typeof clinicalNote !== 'string') {
      throw new Error('Clinical note must be a non-empty string');
    }

    if (!Array.isArray(humanCodes) || humanCodes.length === 0) {
      throw new Error('Human codes must be a non-empty array');
    }

    const response = await fetch(`${this.baseUrl}/api/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        clinical_note: clinicalNote.trim(),
        human_codes: humanCodes.map(code => code.trim().toUpperCase()),
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Get all available reports
   * @returns {Promise<Array>} Array of report objects
   */
  async getReports() {
    const response = await fetch(`${this.baseUrl}/api/reports`);

    if (!response.ok) {
      throw new Error(`Failed to fetch reports: HTTP ${response.status}`);
    }

    const data = await response.json();
    return data.reports || [];
  }

  /**
   * Get sample clinical note
   * @param {number} sampleNumber - Sample number (1-4)
   * @returns {Promise<string>} Sample clinical note text
   */
  async getSample(sampleNumber) {
    if (![1, 2, 3, 4].includes(sampleNumber)) {
      throw new Error('Sample number must be 1, 2, 3, or 4');
    }

    const response = await fetch(`${this.baseUrl}/api/sample/${sampleNumber}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch sample: HTTP ${response.status}`);
    }

    const data = await response.json();
    return data.note || '';
  }

  /**
   * Get database/vector store status
   * @returns {Promise<Object>} Status information
   */
  async getStatus() {
    const response = await fetch(`${this.baseUrl}/api/db-status`);

    if (!response.ok) {
      return {};
    }

    return await response.json();
  }

  /**
   * Parse codes from file
   * @param {File} file - CSV/TXT file containing codes
   * @returns {Promise<Object>} Parsed codes by type
   */
  async parseCodesFromFile(file) {
    if (!(file instanceof File)) {
      throw new Error('Invalid file object');
    }

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/parse-codes`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `Failed to parse codes: HTTP ${response.status}`);
    }

    return await response.json();
  }
}

/**
 * Event Emitter for cross-component communication
 */
export class EventEmitter {
  constructor() {
    this.events = {};
  }

  on(event, callback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
  }

  off(event, callback) {
    if (this.events[event]) {
      this.events[event] = this.events[event].filter(cb => cb !== callback);
    }
  }

  emit(event, data) {
    if (this.events[event]) {
      this.events[event].forEach(callback => callback(data));
    }
  }
}

/**
 * Local storage utilities with auto-parsing
 */
export class StorageService {
  static setJSON(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  static getJSON(key) {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : null;
  }

  static setString(key, value) {
    localStorage.setItem(key, value);
  }

  static getString(key) {
    return localStorage.getItem(key);
  }

  static remove(key) {
    localStorage.removeItem(key);
  }

  static clear() {
    localStorage.clear();
  }
}

/**
 * Format utilities for display
 */
export const Formatters = {
  /**
   * Format confidence as percentage
   */
  confidence: (value) => {
    if (typeof value !== 'number') return '—';
    return `${Math.round(Math.max(0, Math.min(100, value)))}%`;
  },

  /**
   * Format date/time
   */
  datetime: (date) => {
    const d = new Date(date);
    return d.toLocaleString();
  },

  /**
   * Format code with type badge
   */
  codeWithType: (code, type) => {
    const typeMap = {
      'ICD-10': 'bg-blue-100 text-blue-800',
      'CPT': 'bg-green-100 text-green-800',
      'HCPCS': 'bg-purple-100 text-purple-800',
    };
    return `<code class="font-mono">${code}</code> <span class="badge ${typeMap[type] || ''}">${type}</span>`;
  },

  /**
   * Truncate text with ellipsis
   */
  truncate: (text, length = 100) => {
    if (typeof text !== 'string') return '';
    return text.length > length ? text.substring(0, length) + '...' : text;
  },

  /**
   * Format file size
   */
  fileSize: (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  },
};

/**
 * Validation utilities
 */
export const Validators = {
  /**
   * Check if string is valid ICD-10 code
   */
  isICD10: (code) => {
    const pattern = /^[A-Z][0-9]{2}(?:\.[A-Z0-9]{1,4})?$/;
    return pattern.test(code.trim().toUpperCase());
  },

  /**
   * Check if string is valid CPT code
   */
  isCPT: (code) => {
    const pattern = /^[0-9]{5}$|^[0-9]{4}[A-Z]$/;
    return pattern.test(code.trim().toUpperCase());
  },

  /**
   * Check if string is valid HCPCS code
   */
  isHCPCS: (code) => {
    const pattern = /^[A-Z][0-9]{4}$/;
    return pattern.test(code.trim().toUpperCase());
  },

  /**
   * Detect code type
   */
  detectCodeType: (code) => {
    const c = code.trim().toUpperCase();
    if (Validators.isCPT(c)) return 'CPT';
    if (Validators.isHCPCS(c)) return 'HCPCS';
    if (Validators.isICD10(c)) return 'ICD-10';
    return 'UNKNOWN';
  },

  /**
   * Validate clinical note length
   */
  isValidNote: (note) => {
    const text = (note || '').trim();
    return text.length >= 10 && text.length <= 50000;
  },
};

/**
 * HTML generation utilities
 */
export const HTML = {
  /**
   * Create a code badge
   */
  codeBadge: (code, confidence) => {
    const bgColor = confidence >= 90 ? 'bg-green-100 text-green-800'
                  : confidence >= 80 ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-orange-100 text-orange-800';
    return `
      <tr class="hover:bg-slate-50">
        <td class="px-4 py-3 font-mono font-semibold text-slate-900">${code}</td>
        <td class="px-4 py-3"><span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${bgColor}">${confidence}%</span></td>
      </tr>
    `;
  },

  /**
   * Create a diagnosis card
   */
  diagnosisCard: (diagnosis) => {
    return `
      <div class="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
        <svg class="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
        </svg>
        <span class="text-slate-700">${diagnosis}</span>
      </div>
    `;
  },

  /**
   * Create a spinner
   */
  spinner: () => {
    return `
      <div class="w-12 h-12">
        <div class="w-full h-full border-4 border-blue-100 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
    `;
  },
};
