/**
 * LiveMapExplorer — Leaflet map with bbox scanner, GeoJSON overlays,
 * dynamic multi-year time-travel (2014 - 2026), and side-by-side interactive split slider.
 *
 * Split comparison uses a custom Leaflet pane with CSS clip-path so the
 * historical tile layer lives inside the SAME map and auto-syncs pan/zoom.
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import { Scan, Clock, ArrowLeftRight, Calendar } from 'lucide-react';
import LayerControls from './LayerControls';

const ESRI_TILES = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const ESRI_LABELS = 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}';

const WAYBACK_URLS = {
  2014: 'https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/1258/{z}/{y}/{x}',
  2016: 'https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/1805/{z}/{y}/{x}',
  2018: 'https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/2500/{z}/{y}/{x}',
  2020: 'https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/3200/{z}/{y}/{x}',
  2021: 'https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/45009/{z}/{y}/{x}',
  2023: 'https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/49000/{z}/{y}/{x}',
  2024: 'https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/52000/{z}/{y}/{x}',
  2026: ESRI_TILES,
};

const AVAILABLE_YEARS = [2014, 2016, 2018, 2020, 2021, 2023, 2024, 2026];

const LAYER_COLORS = {
  detections: '#ef4444',
  built_up: '#8b5cf6',
  vegetation: '#22c55e',
  water: '#0ea5e9',
  roads: '#f59e0b',
};

const HIGHLIGHT_COLOR = '#22d3ee';

// ---------- helper components ----------

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

function FlyToFeature({ targetFeature }) {
  const map = useMap();

  useEffect(() => {
    if (!targetFeature) return;
    const coords = targetFeature.geometry?.coordinates;
    if (!coords) return;

    try {
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

/**
 * ClippedPane — creates / updates a custom Leaflet pane whose tiles are
 * clipped via CSS clip-path.  Because the TileLayer lives inside the SAME
 * map instance, pan and zoom stay in sync automatically.
 */
function ClippedPane({ splitPos }) {
  const map = useMap();

  useEffect(() => {
    if (!map.getPane('historicalPane')) {
      map.createPane('historicalPane');
    }
    const pane = map.getPane('historicalPane');
    pane.style.zIndex = 350;
    pane.style.clipPath = `polygon(0 0, ${splitPos}% 0, ${splitPos}% 100%, 0 100%)`;
    pane.style.WebkitClipPath = pane.style.clipPath;
  }, [map, splitPos]);

  return null;
}

// ---------- main component ----------

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
  const [selectedYear, setSelectedYear] = useState(2021);
  const [splitPos, setSplitPos] = useState(50);
  const [targetFeature, setTargetFeature] = useState(null);
  const [isDraggingSlider, setIsDraggingSlider] = useState(false);
  const [clickedCoords, setClickedCoords] = useState(null);

  const mapRef = useRef(null);
  const containerRef = useRef(null);

  const handleBoundsChange = useCallback((bounds) => {
    setViewport(bounds);
  }, []);

  const handleScan = () => {
    if (viewport) {
      onScan(
        [viewport.min_lat, viewport.min_lon, viewport.max_lat, viewport.max_lon],
        viewport.zoom
      );
    }
  };

  const handleTemporalScan = () => {
    if (viewport) {
      onTemporalScan(
        [viewport.min_lat, viewport.min_lon, viewport.max_lat, viewport.max_lon],
        viewport.zoom,
        selectedYear
      );
      setShowSplit(true);
    }
  };

  // --- slider drag ---
  const handleMouseMove = useCallback(
    (e) => {
      if (!isDraggingSlider || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      setSplitPos(Math.max(0, Math.min(100, (x / rect.width) * 100)));
    },
    [isDraggingSlider]
  );

  const handleMouseUp = useCallback(() => setIsDraggingSlider(false), []);

  useEffect(() => {
    if (isDraggingSlider) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingSlider, handleMouseMove, handleMouseUp]);

  // --- GeoJSON styling ---
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

  // --- fly-to highlighted evidence ---
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
        if (found) { setTargetFeature(found); return; }
      }
    }
  }, [highlightFeatureIds, layers]);

  // --- render GeoJSON layers ---
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

  const pastWaybackUrl = WAYBACK_URLS[selectedYear] || WAYBACK_URLS[2021];

  return (
    <div className="map-container" id="map-explorer" ref={containerRef}>
      <MapContainer
        center={[17.42, 78.345]}
        zoom={15}
        style={{ height: '100%', width: '100%' }}
        ref={mapRef}
        zoomControl={true}
      >
        {/* Base: current 2026 imagery */}
        <TileLayer
          url={ESRI_TILES}
          attribution='&copy; <a href="https://www.esri.com">Esri</a> World Imagery'
          maxZoom={19}
        />

        {/* Historical layer in a clipped pane — auto-syncs pan/zoom */}
        {showSplit && <ClippedPane splitPos={splitPos} />}
        {showSplit && (
          <TileLayer
            key={`wayback-${selectedYear}`}
            url={pastWaybackUrl}
            maxZoom={19}
            pane="historicalPane"
          />
        )}

        {/* Labels */}
        <TileLayer url={ESRI_LABELS} maxZoom={19} opacity={0.7} />

        <MapEventHandler onBoundsChange={handleBoundsChange} onClickCoords={setClickedCoords} />
        <FlyToFeature targetFeature={targetFeature} />

        {/* Live coordinate badge */}
        {clickedCoords && (
          <div
            style={{
              position: 'absolute', top: 16, left: 60, zIndex: 1000,
              background: 'rgba(15,23,42,0.9)', backdropFilter: 'blur(8px)',
              border: '1px solid rgba(56,189,248,0.4)', color: '#38bdf8',
              padding: '6px 14px', borderRadius: 20, fontSize: 12,
              fontWeight: 600, fontFamily: 'monospace',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              display: 'flex', alignItems: 'center', gap: 8,
            }}
          >
            <span>📍 {clickedCoords.lat.toFixed(6)}°N, {clickedCoords.lng.toFixed(6)}°E</span>
            <button onClick={() => setClickedCoords(null)}
              style={{ background:'none', border:'none', color:'#94a3b8', cursor:'pointer', fontSize:14, padding:0, lineHeight:1 }}>✕</button>
          </div>
        )}

        {renderLayers(layers, 'current-')}
        {showSplit && renderLayers(pastLayers, 'past-')}
      </MapContainer>

      {/* -------- Split-view overlays (only when active) -------- */}

      {/* Year labels */}
      {showSplit && (
        <>
          <div style={{
            position:'absolute', bottom:80, left:16, zIndex:900,
            background:'rgba(168,85,247,0.9)', color:'#fff',
            padding:'4px 12px', borderRadius:8, fontSize:13, fontWeight:700,
            boxShadow:'0 2px 8px rgba(0,0,0,0.4)',
          }}>⏳ {selectedYear}</div>
          <div style={{
            position:'absolute', bottom:80, right:16, zIndex:900,
            background:'rgba(34,197,94,0.9)', color:'#fff',
            padding:'4px 12px', borderRadius:8, fontSize:13, fontWeight:700,
            boxShadow:'0 2px 8px rgba(0,0,0,0.4)',
          }}>🛰️ 2026</div>
        </>
      )}

      {/* Draggable split divider */}
      {showSplit && (
        <div
          style={{
            position:'absolute', top:0, bottom:0,
            left:`${splitPos}%`, width:4, marginLeft:-2,
            background:'linear-gradient(180deg,#38bdf8,#a855f7,#22c55e)',
            zIndex:900, cursor:'ew-resize',
            boxShadow:'0 0 12px rgba(168,85,247,0.8)',
          }}
          onMouseDown={() => setIsDraggingSlider(true)}
        >
          <div style={{
            position:'absolute', top:'50%', left:'50%',
            transform:'translate(-50%,-50%)', width:38, height:38,
            borderRadius:'50%', background:'#0f172a',
            border:'2px solid #a855f7', color:'#38bdf8',
            display:'flex', alignItems:'center', justifyContent:'center',
            fontSize:16, fontWeight:'bold',
            boxShadow:'0 4px 14px rgba(0,0,0,0.6)', userSelect:'none',
          }}>↔</div>
        </div>
      )}

      {/* Layer Controls */}
      <LayerControls visibleLayers={visibleLayers} onToggleLayer={onToggleLayer} />

      {/* -------- Timeline selector: ONLY shown when split mode is active -------- */}
      {showSplit && (
        <div
          style={{
            position: 'absolute', top: 16, right: 60, zIndex: 1000,
            background: 'rgba(15,23,42,0.92)', backdropFilter: 'blur(12px)',
            border: '1px solid rgba(168,85,247,0.4)', borderRadius: 16,
            padding: '10px 16px', display: 'flex', flexDirection: 'column', gap: 8,
            boxShadow: '0 6px 24px rgba(0,0,0,0.6)', maxWidth: 420,
          }}
        >
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap:12 }}>
            <div style={{ display:'flex', alignItems:'center', gap:6, fontSize:13, fontWeight:700, color:'#a855f7' }}>
              <Calendar size={14} /><span>Select Timeline Year:</span>
            </div>
            <span style={{ fontSize:12, fontWeight:600, color:'#38bdf8' }}>{selectedYear} vs 2026</span>
          </div>

          {/* Year pills */}
          <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
            {AVAILABLE_YEARS.map((yr) => (
              <button
                key={yr}
                onClick={() => {
                  setSelectedYear(yr);
                  if (viewport) {
                    onTemporalScan(
                      [viewport.min_lat, viewport.min_lon, viewport.max_lat, viewport.max_lon],
                      viewport.zoom, yr
                    );
                  }
                }}
                style={{
                  padding:'4px 10px', borderRadius:12, fontSize:11, fontWeight:700,
                  border:'1px solid',
                  borderColor: selectedYear === yr ? '#a855f7' : 'rgba(148,163,184,0.2)',
                  background: selectedYear === yr
                    ? 'linear-gradient(135deg,#7c3aed,#a855f7)'
                    : 'rgba(30,41,59,0.6)',
                  color: selectedYear === yr ? '#fff' : '#94a3b8',
                  cursor:'pointer', transition:'all 0.2s ease',
                }}
              >{yr}</button>
            ))}
          </div>

          {/* Split slider */}
          <div style={{ display:'flex', alignItems:'center', gap:10, marginTop:4 }}>
            <span style={{ fontSize:11, color:'#a855f7', fontWeight:600 }}>⏳ {selectedYear}</span>
            <input type="range" min="0" max="100" value={splitPos}
              onChange={(e) => setSplitPos(Number(e.target.value))}
              style={{ flex:1, accentColor:'#a855f7', cursor:'pointer' }} />
            <span style={{ fontSize:11, color:'#22c55e', fontWeight:600 }}>🛰️ 2026</span>
          </div>
        </div>
      )}

      {/* -------- Scan controls -------- */}
      <div className="scan-btn-container">
        <div style={{ display:'flex', gap:8 }}>
          <button className="scan-btn" onClick={handleScan}
            disabled={scanning || !viewport} id="btn-scan-viewport">
            {scanning
              ? <><div className="spinner" /> Scanning...</>
              : <><Scan size={16} /> Scan Viewport</>}
          </button>

          <button className="scan-btn" onClick={handleTemporalScan}
            disabled={scanning || !viewport} id="btn-temporal-scan"
            style={{ background:'linear-gradient(135deg,#065f46,#16a34a)',
                     boxShadow:'0 4px 20px rgba(22,163,74,0.4)' }}>
            <Clock size={16} /> Time Travel ({selectedYear})
          </button>

          <button className="scan-btn"
            onClick={() => setShowSplit(!showSplit)} id="btn-toggle-split"
            style={{
              background: showSplit
                ? 'linear-gradient(135deg,#7c3aed,#a855f7)'
                : 'linear-gradient(135deg,#475569,#64748b)',
              boxShadow: showSplit
                ? '0 4px 20px rgba(124,58,237,0.4)'
                : '0 4px 20px rgba(71,85,105,0.3)',
            }}>
            <ArrowLeftRight size={16} />
            {showSplit ? 'Hide Split Overlay' : `Compare ${selectedYear} vs 2026`}
          </button>
        </div>
      </div>
    </div>
  );
}
