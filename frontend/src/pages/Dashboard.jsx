/**
 * Dashboard — Main application layout.
 * Orchestrates scan flow: map move → scan → display results → chat → export.
 */

import React, { useState, useCallback } from 'react';
import {
  Satellite,
  Map,
  BarChart3,
  MessageSquare,
  Upload,
  Settings,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import Navbar from '../components/Navbar';
import LiveMapExplorer from '../components/LiveMapExplorer';
import GrowthHUD from '../components/GrowthHUD';
import FileUploader from '../components/FileUploader';
import GroundedChatbot from '../components/GroundedChatbot';

export default function Dashboard() {
  const { user, logout } = useAuth();

  // Scan state
  const [scanning, setScanning] = useState(false);
  const [scanId, setScanId] = useState(null);
  const [layers, setLayers] = useState(null);
  const [pastLayers, setPastLayers] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [temporalMetrics, setTemporalMetrics] = useState(null);
  const [pastImageBase64, setPastImageBase64] = useState(null);
  const [currentImageBase64, setCurrentImageBase64] = useState(null);

  // UI state
  const [showUpload, setShowUpload] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [highlightFeatureIds, setHighlightFeatureIds] = useState([]);
  const [visibleLayers, setVisibleLayers] = useState({
    detections: true,
    built_up: true,
    vegetation: true,
    water: true,
    roads: true,
  });

  // Active nav item
  const [activeNav, setActiveNav] = useState('explorer');

  // Handle viewport scan
  const handleScan = useCallback(async (bbox, zoom) => {
    setScanning(true);
    try {
      const response = await api.scanViewport(bbox, zoom);
      const data = response.data;

      if (data.error) {
        console.error('Scan error:', data.error);
        return;
      }

      setScanId(data.scan_id);
      setLayers(data.layers);
      setMetrics(data.metrics);
    } catch (err) {
      console.error('Scan failed:', err);
    } finally {
      setScanning(false);
    }
  }, []);

  // Handle temporal scan
  const handleTemporalScan = useCallback(async (bbox, zoom) => {
    setScanning(true);
    try {
      const response = await api.temporalAnalysis(bbox, zoom);
      const data = response.data;

      if (data.error) {
        console.error('Temporal error:', data.error);
        return;
      }

      setScanId(data.scan_id);
      setLayers(data.current_layers);
      setPastLayers(data.past_layers);
      setTemporalMetrics(data.growth_metrics);
      setPastImageBase64(data.past_image_base64);
      setCurrentImageBase64(data.current_image_base64);

      // Update metrics from temporal data
      const det = data.growth_metrics?.detections || {};
      const veg = data.growth_metrics?.vegetation || {};
      setMetrics({
        detection_count: det.current_count || 0,
        vegetation_count: veg.current_polygon_count || 0,
        water_count: data.growth_metrics?.water_bodies?.current_count || 0,
        road_count: 0,
        built_up_count: data.growth_metrics?.built_up_areas?.current_count || 0,
        vegetation_percentage: veg.current_coverage_pct || 0,
      });
    } catch (err) {
      console.error('Temporal scan failed:', err);
    } finally {
      setScanning(false);
    }
  }, []);

  // Handle file upload
  const handleUpload = useCallback(async (file) => {
    const response = await api.uploadFile(file);
    const data = response.data;

    setScanId(data.scan_id);
    setLayers(data.layers);
    setMetrics(data.metrics);
  }, []);

  // Handle PDF export
  const handleExport = useCallback(async () => {
    if (!scanId) {
      alert('Please scan an area first before exporting a report.');
      return;
    }

    try {
      const response = await api.exportReport(scanId);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `DrishtiAI_Report_${scanId.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to export report. Please try again.');
    }
  }, [scanId]);

  // Handle layer toggle
  const handleToggleLayer = useCallback((layerKey) => {
    setVisibleLayers((prev) => ({
      ...prev,
      [layerKey]: !prev[layerKey],
    }));
  }, []);

  // Handle evidence highlighting from chat
  const handleHighlightFeatures = useCallback((featureIds) => {
    setHighlightFeatureIds(featureIds);
    // Auto-close chat briefly so user can see the map
    setTimeout(() => {
      setHighlightFeatureIds([]);
    }, 5000);
  }, []);

  const navItems = [
    { key: 'explorer', icon: Map, label: 'Map Explorer' },
    { key: 'analytics', icon: BarChart3, label: 'Analytics' },
    { key: 'chat', icon: MessageSquare, label: 'AI Assistant' },
    { key: 'upload', icon: Upload, label: 'Upload Image' },
  ];

  return (
    <div className="app-layout" id="dashboard">
      {/* Sidebar */}
      <aside className="sidebar" id="sidebar">
        <div className="sidebar-header">
          <div className="logo-row">
            <div className="logo-icon">
              <Satellite size={18} />
            </div>
            <div>
              <h2>DrishtiAI</h2>
              <p>Satellite Intelligence</p>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(({ key, icon: Icon, label }) => (
            <button
              key={key}
              className={`sidebar-nav-item ${activeNav === key ? 'active' : ''}`}
              onClick={() => {
                setActiveNav(key);
                if (key === 'chat') setChatOpen(true);
                if (key === 'upload') setShowUpload(true);
              }}
              id={`nav-${key}`}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="avatar">
              {user?.displayName?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="user-info">
              <div className="user-name">{user?.displayName || 'User'}</div>
              <div className="user-email">{user?.email || ''}</div>
            </div>
            <button
              className="btn btn-ghost btn-icon"
              onClick={logout}
              title="Sign out"
              style={{ color: '#94a3b8' }}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="main-content">
        <Navbar
          onUploadClick={() => setShowUpload(true)}
          onExportClick={handleExport}
        />

        {/* Growth HUD */}
        <GrowthHUD metrics={metrics} temporalMetrics={temporalMetrics} />

        {/* Map Explorer */}
        <LiveMapExplorer
          layers={layers}
          pastLayers={pastLayers}
          pastImageBase64={pastImageBase64}
          currentImageBase64={currentImageBase64}
          scanning={scanning}
          onScan={handleScan}
          onTemporalScan={handleTemporalScan}
          highlightFeatureIds={highlightFeatureIds}
          visibleLayers={visibleLayers}
          onToggleLayer={handleToggleLayer}
        />

        {/* Grounded Chatbot */}
        <GroundedChatbot
          isOpen={chatOpen}
          onToggle={() => setChatOpen(!chatOpen)}
          scanId={scanId}
          onHighlightFeatures={handleHighlightFeatures}
        />

        {/* File Uploader Modal */}
        <FileUploader
          isOpen={showUpload}
          onClose={() => setShowUpload(false)}
          onUpload={handleUpload}
        />
      </div>
    </div>
  );
}
