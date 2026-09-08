/**
 * UploadedImageViewer — Displays user-uploaded satellite image with SVG canvas overlay for detections & analytics.
 */

import React, { useState } from 'react';
import { Eye, Layers, Image as ImageIcon, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import LayerControls from './LayerControls';

const LAYER_COLORS = {
  detections: '#ef4444',
  built_up: '#8b5cf6',
  vegetation: '#22c55e',
  water: '#0ea5e9',
  roads: '#f59e0b',
};

export default function UploadedImageViewer({
  uploadedImage,
  visibleLayers,
  onToggleLayer,
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [selectedFeature, setSelectedFeature] = useState(null);

  if (!uploadedImage || !uploadedImage.imageBase64) {
    return (
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 16, color: '#94a3b8', background: '#090d16'
      }}>
        <ImageIcon size={48} opacity={0.4} />
        <p style={{ fontSize: 16, fontWeight: 500 }}>No image uploaded yet. Click "Upload Image" in the sidebar to analyze your satellite image.</p>
      </div>
    );
  }

  const { filename, imageBase64, imageSize, layers, metrics } = uploadedImage;
  const imgWidth = imageSize?.width || 800;
  const imgHeight = imageSize?.height || 600;

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Convert feature coordinates (pixel coords) to SVG path strings
  const renderFeaturePath = (feature, key) => {
    const coords = feature.geometry?.coordinates;
    if (!coords || !coords.length) return null;

    const layerName = feature.properties?.layer || key;
    const isHighlighted = selectedFeature?.id === feature.id;
    const strokeColor = isHighlighted ? '#22d3ee' : LAYER_COLORS[layerName] || '#ef4444';

    // Handle polygon vs linestring
    let pathD = '';
    if (feature.geometry.type === 'Polygon' || feature.geometry.type === 'MultiPolygon') {
      const rings = feature.geometry.type === 'Polygon' ? [coords[0]] : coords.map(c => c[0]);
      pathD = rings.map(ring => {
        return ring.map(([x, y], idx) => `${idx === 0 ? 'M' : 'L'} ${x} ${y}`).join(' ') + ' Z';
      }).join(' ');
    } else if (feature.geometry.type === 'LineString') {
      pathD = coords.map(([x, y], idx) => `${idx === 0 ? 'M' : 'L'} ${x} ${y}`).join(' ');
    }

    return (
      <path
        key={feature.id}
        d={pathD}
        fill={strokeColor}
        fillOpacity={layerName === 'roads' ? 0 : isHighlighted ? 0.6 : 0.25}
        stroke={strokeColor}
        strokeWidth={isHighlighted ? 4 / zoom : 2 / zoom}
        strokeDasharray={layerName === 'roads' ? '4,4' : undefined}
        style={{ cursor: 'pointer', transition: 'all 0.15s ease' }}
        onClick={(e) => {
          e.stopPropagation();
          setSelectedFeature(feature);
        }}
      />
    );
  };

  return (
    <div
      style={{
        position: 'relative', flex: 1, width: '100%', height: '100%',
        background: '#040711', overflow: 'hidden', userSelect: 'none',
        display: 'flex', flexDirection: 'column'
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Top Banner with File Info */}
      <div style={{
        position: 'absolute', top: 16, left: 16, zIndex: 10,
        background: 'rgba(15, 23, 42, 0.85)', backdropFilter: 'blur(12px)',
        border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: 12,
        padding: '10px 16px', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 12,
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
      }}>
        <ImageIcon size={20} color="#38bdf8" />
        <div>
          <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700 }}>{filename}</h4>
          <p style={{ margin: 0, fontSize: 11, color: '#94a3b8' }}>
            {imgWidth} × {imgHeight} px | Detections: {metrics?.detection_count || 0}
          </p>
        </div>
      </div>

      {/* Zoom / Pan Controls */}
      <div style={{
        position: 'absolute', top: 16, right: 60, zIndex: 10,
        display: 'flex', gap: 6, background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(12px)', padding: 6, borderRadius: 10,
        border: '1px solid rgba(148, 163, 184, 0.2)'
      }}>
        <button
          onClick={() => setZoom(z => Math.min(z * 1.25, 5))}
          style={{ background: 'none', border: 'none', color: '#f8fafc', padding: 6, cursor: 'pointer', borderRadius: 6 }}
          title="Zoom In"
        >
          <ZoomIn size={18} />
        </button>
        <button
          onClick={() => setZoom(z => Math.max(z / 1.25, 0.5))}
          style={{ background: 'none', border: 'none', color: '#f8fafc', padding: 6, cursor: 'pointer', borderRadius: 6 }}
          title="Zoom Out"
        >
          <ZoomOut size={18} />
        </button>
        <button
          onClick={resetView}
          style={{ background: 'none', border: 'none', color: '#f8fafc', padding: 6, cursor: 'pointer', borderRadius: 6 }}
          title="Reset View"
        >
          <RotateCcw size={18} />
        </button>
      </div>

      {/* Image & Analytics Overlay Container */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: isDragging ? 'grabbing' : 'grab'
      }}>
        <div style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transition: isDragging ? 'none' : 'transform 0.1s ease-out',
          position: 'relative',
          display: 'inline-block',
          boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
          borderRadius: 8,
          overflow: 'hidden'
        }}>
          {/* Base Uploaded Image */}
          <img
            src={`data:image/jpeg;base64,${imageBase64}`}
            alt="Uploaded Satellite Input"
            style={{ display: 'block', maxWidth: '80vw', maxHeight: '75vh', width: 'auto', height: 'auto' }}
          />

          {/* SVG Overlay layer matching image dimensions */}
          <svg
            viewBox={`0 0 ${imgWidth} ${imgHeight}`}
            style={{
              position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
              pointerEvents: 'auto'
            }}
          >
            {layers && Object.entries(layers).map(([layerKey, geojson]) => {
              if (!geojson?.features?.length) return null;
              if (visibleLayers[layerKey] === false) return null;

              return geojson.features.map(feature => renderFeaturePath(feature, layerKey));
            })}
          </svg>
        </div>
      </div>

      {/* Selected Feature Info Popup */}
      {selectedFeature && (
        <div style={{
          position: 'absolute', bottom: 24, left: 24, zIndex: 10,
          background: 'rgba(15, 23, 42, 0.95)', backdropFilter: 'blur(12px)',
          border: '1px solid #38bdf8', borderRadius: 12, padding: 14,
          maxWidth: 320, color: '#f8fafc', boxShadow: '0 6px 24px rgba(0,0,0,0.6)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#38bdf8', textTransform: 'capitalize' }}>
              Feature: {selectedFeature.properties?.class || selectedFeature.properties?.layer || 'Object'}
            </span>
            <button
              onClick={() => setSelectedFeature(null)}
              style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 14 }}
            >✕</button>
          </div>
          <div style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 4, color: '#cbd5e1' }}>
            {selectedFeature.properties?.confidence && (
              <div>Confidence: <b>{(selectedFeature.properties.confidence * 100).toFixed(1)}%</b></div>
            )}
            {selectedFeature.properties?.area_pixels && (
              <div>Area: <b>{Math.round(selectedFeature.properties.area_pixels)} px²</b></div>
            )}
          </div>
        </div>
      )}

      {/* Layer Controls overlay */}
      <LayerControls visibleLayers={visibleLayers} onToggleLayer={onToggleLayer} />
    </div>
  );
}
