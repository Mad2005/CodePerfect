/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Home from './pages/Home';
import AutoCoding from './pages/AutoCoding';
import AssistedCoding from './pages/AssistedCoding';
import Report from './pages/Report';
import History from './pages/History';

export default function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col font-sans">
        <Navbar />
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/home" element={<Home />} />
            <Route path="/auto-coding" element={<AutoCoding />} />
            <Route path="/assisted-coding" element={<AssistedCoding />} />
            <Route path="/report/:id" element={<Report />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
