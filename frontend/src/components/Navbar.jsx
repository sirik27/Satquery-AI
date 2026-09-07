/**
 * Navbar — Deep navy top bar with logo, user info, and actions.
 */

import React from 'react';
import { Satellite, Upload, FileText, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ onUploadClick, onExportClick }) {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  return (
    <nav className="navbar" id="main-navbar">
      <div className="navbar-brand">
        <div className="logo-icon">
          <Satellite size={18} />
        </div>
        <h1>DrishtiAI</h1>
      </div>

      <div className="navbar-actions">
        <button
          className="btn btn-secondary btn-sm"
          onClick={onUploadClick}
          id="btn-upload"
        >
          <Upload size={14} />
          Upload
        </button>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onExportClick}
          id="btn-export"
        >
          <FileText size={14} />
          Export PDF
        </button>
        <button
          className="btn btn-ghost btn-sm"
          onClick={handleLogout}
          id="btn-logout"
          title="Sign out"
        >
          <LogOut size={14} />
        </button>
      </div>
    </nav>
  );
}
