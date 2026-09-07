/**
 * LayerControls — Vector layer visibility toggles with colored indicators.
 */

import React from 'react';

const LAYER_CONFIG = [
  { key: 'detections', label: 'Object Detections', color: '#ef4444' },
  { key: 'built_up', label: 'Built-up Areas', color: '#8b5cf6' },
  { key: 'vegetation', label: 'Vegetation', color: '#22c55e' },
  { key: 'water', label: 'Water Bodies', color: '#0ea5e9' },
  { key: 'roads', label: 'Roads', color: '#f59e0b' },
];

export default function LayerControls({ visibleLayers, onToggleLayer }) {
  return (
    <div className="layer-panel map-overlay map-overlay-topright" id="layer-controls">
      <h4>Layers</h4>
      {LAYER_CONFIG.map(({ key, label, color }) => (
        <div className="layer-item" key={key}>
          <label htmlFor={`layer-toggle-${key}`}>
            <span className="layer-dot" style={{ backgroundColor: color }} />
            {label}
          </label>
          <label className="toggle-switch">
            <input
              type="checkbox"
              id={`layer-toggle-${key}`}
              checked={visibleLayers[key] !== false}
              onChange={() => onToggleLayer(key)}
            />
            <span className="toggle-slider" />
          </label>
        </div>
      ))}
    </div>
  );
}

export { LAYER_CONFIG };
