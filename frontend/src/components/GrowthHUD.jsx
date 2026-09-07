/**
 * GrowthHUD — Live counts & percentage growth metrics.
 * Displays animated metric cards for detection results.
 */

import React from 'react';
import {
  Building2,
  TreePine,
  Droplets,
  Route,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';

function MetricCard({ label, value, change, changeLabel, icon: Icon, color }) {
  const changeClass = change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral';
  const ChangeIcon = change > 0 ? TrendingUp : change < 0 ? TrendingDown : Minus;

  return (
    <div className="metric-card" id={`metric-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {Icon && <Icon size={14} color={color} />}
        <span className="metric-label">{label}</span>
      </div>
      <div className="metric-value">{value}</div>
      {changeLabel && (
        <div className={`metric-change ${changeClass}`}>
          <ChangeIcon size={12} />
          <span>{changeLabel}</span>
        </div>
      )}
    </div>
  );
}

export default function GrowthHUD({ metrics, temporalMetrics }) {
  if (!metrics) return null;

  const {
    detection_count = 0,
    vegetation_count = 0,
    water_count = 0,
    road_count = 0,
    built_up_count = 0,
    vegetation_percentage = 0,
  } = metrics;

  // Temporal data if available
  const det = temporalMetrics?.detections;
  const veg = temporalMetrics?.vegetation;
  const built = temporalMetrics?.built_up_areas;

  return (
    <div className="metrics-row" id="growth-hud">
      <MetricCard
        label="Buildings"
        value={built_up_count}
        icon={Building2}
        color="#8b5cf6"
        change={built?.concrete_expansion_sqm}
        changeLabel={built ? `${built.concrete_expansion_sqm >= 0 ? '+' : ''}${built.concrete_expansion_sqm.toFixed(0)} m²` : null}
      />
      <MetricCard
        label="Vegetation"
        value={`${vegetation_percentage.toFixed(1)}%`}
        icon={TreePine}
        color="#16a34a"
        change={veg?.vegetation_change_pct}
        changeLabel={veg ? `${veg.vegetation_change_pct >= 0 ? '+' : ''}${veg.vegetation_change_pct.toFixed(1)}%` : null}
      />
      <MetricCard
        label="Water Bodies"
        value={water_count}
        icon={Droplets}
        color="#0ea5e9"
      />
      <MetricCard
        label="Roads"
        value={road_count}
        icon={Route}
        color="#f59e0b"
      />
      <MetricCard
        label="Objects"
        value={detection_count}
        icon={Building2}
        color="#ef4444"
        change={det?.net_change}
        changeLabel={det ? `${det.net_change >= 0 ? '+' : ''}${det.net_change} since 2021` : null}
      />
    </div>
  );
}
