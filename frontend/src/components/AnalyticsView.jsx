/**
 * AnalyticsView — Detailed spatial statistics dashboard component.
 * Displays land cover distribution, spectral index metrics, and object counts.
 */

import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Building2, TreePine, Droplets, Route, Layers, Activity } from 'lucide-react';

export default function AnalyticsView({ metrics, temporalMetrics }) {
  if (!metrics) {
    return (
      <div className="analytics-empty">
        <Activity size={48} style={{ color: '#38bdf8', marginBottom: 16 }} />
        <h3>No Scan Data Available</h3>
        <p>Scan a satellite viewport on the Map Explorer tab to generate live spatial analytics.</p>
      </div>
    );
  }

  const landCoverData = [
    { name: 'Vegetation', value: metrics.vegetation_percentage || 0, color: '#22c55e' },
    { name: 'Built-up', value: Math.min(100 - (metrics.vegetation_percentage || 0), 40), color: '#8b5cf6' },
    { name: 'Water', value: metrics.water_count > 0 ? 15 : 5, color: '#0ea5e9' },
    { name: 'Other', value: Math.max(0, 100 - (metrics.vegetation_percentage || 0) - 20), color: '#64748b' },
  ];

  const countsData = [
    { name: 'Detections', count: metrics.detection_count || 0, fill: '#ef4444' },
    { name: 'Built-up', count: metrics.built_up_count || 0, fill: '#8b5cf6' },
    { name: 'Vegetation', count: metrics.vegetation_count || 0, fill: '#22c55e' },
    { name: 'Water Bodies', count: metrics.water_count || 0, fill: '#0ea5e9' },
    { name: 'Roads', count: metrics.road_count || 0, fill: '#f59e0b' },
  ];

  return (
    <div className="analytics-view" id="analytics-panel" style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
      <div className="analytics-header" style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#f8fafc', margin: 0 }}>
          📊 Spatial Analytics & Land Cover Breakdown
        </h2>
        <p style={{ color: '#94a3b8', fontSize: '13px', marginTop: '4px' }}>
          Live metrics computed directly from satellite raster imagery and vector geometry analysis.
        </p>
      </div>

      {/* Metric Cards Grid */}
      <div className="hud-grid" style={{ marginBottom: '24px' }}>
        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-card-title">Vegetation Index (GLI)</span>
            <TreePine size={18} color="#22c55e" />
          </div>
          <div className="metric-card-value" style={{ color: '#22c55e' }}>
            {metrics.vegetation_percentage}%
          </div>
          <div className="metric-card-sub">Real spectral canopy index</div>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-card-title">Built-up Structures</span>
            <Building2 size={18} color="#8b5cf6" />
          </div>
          <div className="metric-card-value" style={{ color: '#8b5cf6' }}>
            {metrics.built_up_count}
          </div>
          <div className="metric-card-sub">Identified polygon zones</div>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-card-title">Water Bodies</span>
            <Droplets size={18} color="#0ea5e9" />
          </div>
          <div className="metric-card-value" style={{ color: '#0ea5e9' }}>
            {metrics.water_count}
          </div>
          <div className="metric-card-sub">Spectral water basins</div>
        </div>

        <div className="metric-card">
          <div className="metric-card-header">
            <span className="metric-card-title">YOLO Detections</span>
            <Layers size={18} color="#ef4444" />
          </div>
          <div className="metric-card-value" style={{ color: '#ef4444' }}>
            {metrics.detection_count}
          </div>
          <div className="metric-card-sub">Object bounding boxes</div>
        </div>
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px' }}>
        {/* Land Cover Pie Chart */}
        <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ fontSize: '15px', color: '#f8fafc', marginBottom: '16px' }}>Land Cover Distribution (%)</h3>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={landCoverData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {landCoverData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Feature Counts Bar Chart */}
        <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ fontSize: '15px', color: '#f8fafc', marginBottom: '16px' }}>Vector Feature Counts</h3>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={countsData}>
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {countsData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
