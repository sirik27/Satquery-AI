/**
 * LiveMapExplorer — Leaflet map with bbox scanner, GeoJSON overlays,
 * split-screen time-travel, and evidence highlighting.
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  useMap,
  useMapEvents,
  Rectangle,
} from 'react-leaflet';
import { Scan, Clock, ArrowLeftRight } from 'lucide-react';
import LayerControls from './LayerControls';

const ESRI_TILES = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const ESRI_LABELS = 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}';

const LAYER_COLORS = {
  detections: '#ef4444',
  built_up: '#8b5cf6',
  vegetation: '#22c55e',
  water: '#0ea5e9',
  roads: '#f59e0b',
};

const HIGHLIGHT_COLOR = '#22d3ee';

// Map event handler component
function MapEventHandler({ onBoundsChange, onClickCoords }) {
  useMapEvents({
    moveend: (e) => {
      const map = e.target;
      const bounds = map.getBounds();
      const zoom = map.getZoom();
      onBoundsChange({
        min_lat: bounds.getSouth(),
        min_lon: bounds.getWest(),
        max_lat: bounds.getNorth(),
        max_lon: bounds.getEast(),
        zoom,
      });
    },
    click: (e) => {
      if (onClickCoords) {
        onClickCoords({ lat: e.latlng.lat, lng: e.latlng.lng });
      }
    },
  });
  return null;
}

// Fly to evidence feature
function FlyToFeature({ targetFeature }) {
  const map = useMap();

  useEffect(() => {
    if (!targetFeature) return;
    const coords = targetFeature.geometry?.coordinates;
    if (!coords) return;

    try {
      // Get center of polygon
      let lats = [], lons = [];
      const ring = coords[0] || coords;
      ring.forEach(([lon, lat]) => {
        if (typeof lat === 'number' && typeof lon === 'number') {
          lats.push(lat);
          lons.push(lon);
        }
      });

      if (lats.length > 0) {
        const centerLat = lats.reduce((a, b) => a + b) / lats.length;
        const centerLon = lons.reduce((a, b) => a + b) / lons.length;
        map.flyTo([centerLat, centerLon], 17, { duration: 1 });
      }
    } catch (err) {
      console.error('FlyTo error:', err);
    }
  }, [targetFeature, map]);

  return null;
}

export default function LiveMapExplorer({
  layers,
  pastLayers,
  pastImageBase64,
  currentImageBase64,
  scanning,
  onScan,
  onTemporalScan,
  highlightFeatureIds,
  visibleLayers,
  onToggleLayer,
}) {
  const [viewport, setViewport] = useState(null);
  const [showSplit, setShowSplit] = useState(false);
  const [targetFeature, setTargetFeature] = useState(null);
  const mapRef = useRef(null);

  const [clickedCoords, setClickedCoords] = useState(null);

  const handleBoundsChange = useCallback((bounds) => {
    setViewport(bounds);
  }, []);

  const handleScan = () => {
    if (viewport) {
      onScan([viewport.min_lat, viewport.min_lon, viewport.max_lat, viewport.max_lon], viewport.zoom);
    }
  };

  const handleTemporalScan = () => {
    if (viewport) {
      onTemporalScan([viewport.min_lat, viewport.min_lon, viewport.max_lat, viewport.max_lon], viewport.zoom);
    }
  };

  // Style function for GeoJSON features
  const getFeatureStyle = (feature) => {
    const layer = feature.properties?.layer || 'detections';
    const isHighlighted = highlightFeatureIds?.includes(feature.id);

    return {
      color: isHighlighted ? HIGHLIGHT_COLOR : LAYER_COLORS[layer] || '#ef4444',
      weight: isHighlighted ? 4 : 2,
      fillOpacity: isHighlighted ? 0.5 : 0.2,
      opacity: 0.9,
      dashArray: layer === 'roads' ? '5, 5' : null,
    };
  };

  const onEachFeature = (feature, featureLayer) => {
    const props = feature.properties || {};
    const parts = [];
    if (props.class) parts.push(`<b>Type:</b> ${props.class}`);
    if (props.confidence) parts.push(`<b>Confidence:</b> ${(props.confidence * 100).toFixed(1)}%`);
    if (props.layer) parts.push(`<b>Layer:</b> ${props.layer}`);
    if (props.area_pixels) parts.push(`<b>Area:</b> ${props.area_pixels.toFixed(0)} px`);
    if (props.center_lat) parts.push(`<b>Location:</b> ${props.center_lat.toFixed(5)}°N, ${props.center_lon.toFixed(5)}°E`);

    if (parts.length > 0) {
      featureLayer.bindPopup(parts.join('<br/>'), { className: 'custom-popup' });
    }
  };

  // Find highlighted feature for fly-to
  useEffect(() => {
    if (!highlightFeatureIds || highlightFeatureIds.length === 0 || !layers) {
      setTargetFeature(null);
      return;
    }

    const targetId = highlightFeatureIds[0];
    for (const layerKey of Object.keys(layers)) {
      const fc = layers[layerKey];
      if (fc?.features) {
        const found = fc.features.find((f) => f.id === targetId);
        if (found) {
          setTargetFeature(found);
          return;
        }
      }
    }
  }, [highlightFeatureIds, layers]);

  // Render GeoJSON layers
  const renderLayers = (layerData, prefix = '') => {
    if (!layerData) return null;
    return Object.entries(layerData).map(([key, geojson]) => {
      if (!geojson?.features?.length) return null;
      if (visibleLayers[key] === false) return null;

      return (
        <GeoJSON
          key={`${prefix}${key}-${geojson.features.length}`}
          data={geojson}
          style={getFeatureStyle}
          onEachFeature={onEachFeature}
        />
      );
    });
  };

  return (
    <div className="map-container" id="map-explorer">
      <MapContainer
        center={[17.42, 78.345]}
        zoom={15}
        style={{ height: '100%', width: '100%' }}
        ref={mapRef}
        zoomControl={true}
      >
        <TileLayer
          url={ESRI_TILES}
          attribution='&copy; <a href="https://www.esri.com">Esri</a> World Imagery'
          maxZoom={19}
        />
        <TileLayer
          url={ESRI_LABELS}
          maxZoom={19}
          opacity={0.7}
        />

        <MapEventHandler onBoundsChange={handleBoundsChange} onClickCoords={setClickedCoords} />
        <FlyToFeature targetFeature={targetFeature} />

        {/* Live Click Coordinate Badge */}
        {clickedCoords && (
          <div
            style={{
              position: 'absolute',
              top: 16,
              left: 60,
              zIndex: 1000,
              background: 'rgba(15, 23, 42, 0.9)',
              backdropFilter: 'blur(8px)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              color: '#38bdf8',
              padding: '6px 14px',
              borderRadius: '20px',
              fontSize: '12px',
              fontWeight: 600,
              fontFamily: 'monospace',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <span>📍 {clickedCoords.lat.toFixed(6)}°N, {clickedCoords.lng.toFixed(6)}°E</span>
            <button
              onClick={() => setClickedCoords(null)}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                fontSize: 14,
                padding: 0,
                lineHeight: 1,
              }}
            >
              ✕
            </button>
          </div>
        )}

        {/* Render current layers */}
        {renderLayers(layers, 'current-')}

        {/* Render past layers if split view */}
        {showSplit && renderLayers(pastLayers, 'past-')}
      </MapContainer>

      {/* Layer Controls */}
      <LayerControls
        visibleLayers={visibleLayers}
        onToggleLayer={onToggleLayer}
      />

      {/* Split-screen time labels & Slider controls */}
      {showSplit && pastImageBase64 && (
        <div style={{
          position: 'absolute',
          top: 16,
          right: 60,
          zIndex: 1000,
          background: 'rgba(15, 23, 42, 0.9)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(168, 85, 247, 0.4)',
          borderRadius: '12px',
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#a855f7' }}>⏳ 2021 Wayback</span>
          <span style={{ fontSize: 12, color: '#64748b' }}>vs</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#22c55e' }}>🛰️ 2026 Current</span>
        </div>
      )}

      {/* Scan Controls */}
      <div className="scan-btn-container">
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="scan-btn"
            onClick={handleScan}
            disabled={scanning || !viewport}
            id="btn-scan-viewport"
          >
            {scanning ? (
              <>
                <div className="spinner" />
                Scanning...
              </>
            ) : (
              <>
                <Scan size={16} />
                Scan Viewport
              </>
            )}
          </button>
          <button
            className="scan-btn"
            onClick={handleTemporalScan}
            disabled={scanning || !viewport}
            id="btn-temporal-scan"
            style={{
              background: 'linear-gradient(135deg, #065f46, #16a34a)',
              boxShadow: '0 4px 20px rgba(22, 163, 74, 0.4)',
            }}
          >
            <Clock size={16} />
            Time Travel
          </button>
          {pastLayers && (
            <button
              className="scan-btn"
              onClick={() => setShowSplit(!showSplit)}
              id="btn-toggle-split"
              style={{
                background: showSplit
                  ? 'linear-gradient(135deg, #7c3aed, #a855f7)'
                  : 'linear-gradient(135deg, #475569, #64748b)',
                boxShadow: showSplit
                  ? '0 4px 20px rgba(124, 58, 237, 0.4)'
                  : '0 4px 20px rgba(71, 85, 105, 0.3)',
              }}
            >
              <ArrowLeftRight size={16} />
              {showSplit ? 'Hide 2021 Overlay' : 'Compare 2021 vs 2026'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
