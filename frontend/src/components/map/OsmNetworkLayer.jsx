import { useMemo, useState } from 'react';
import L from 'leaflet';
import { Marker, Polyline, Tooltip, useMap, useMapEvents } from 'react-leaflet';

const ROAD_PALETTE = {
  primary: { inner: '#fde9a8', casing: '#c29d48', baseWidth: 11 },
  primary_link: { inner: '#fde9a8', casing: '#c29d48', baseWidth: 8 },
  secondary: { inner: '#fef6d0', casing: '#b8a468', baseWidth: 9.5 },
  tertiary: { inner: '#fef6d0', casing: '#b8a468', baseWidth: 9 },
  residential: { inner: '#ffffff', casing: '#94a3b8', baseWidth: 7.5 },
  unclassified: { inner: '#ffffff', casing: '#94a3b8', baseWidth: 7.5 },
};

const HIGHWAY_TR_LABEL = {
  primary: 'Ana Arter (Primary)',
  primary_link: 'Bağlantı Yolu',
  secondary: 'Ana Cadde (Secondary)',
  tertiary: 'Cadde (Tertiary)',
  residential: 'Ara Sokak (Residential)',
  unclassified: 'Sokak',
};

function createArrowDivIcon(angleDeg) {
  return L.divIcon({
    className: 'osm-oneway-icon',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    html: `<svg width="18" height="18" viewBox="0 0 18 18" style="transform:rotate(${angleDeg.toFixed(1)}deg);display:block">
      <path d="M2 7.4 H10.5 V4.2 L16.2 9 L10.5 13.8 V10.6 H2 Z"
        fill="#334155" stroke="#ffffff" stroke-width="1.6" stroke-linejoin="round" />
    </svg>`,
  });
}

function createStreetLabelDivIcon(name, angleDeg, isAvenue) {
  const cls = isAvenue ? 'osm-street-label osm-street-label--avenue' : 'osm-street-label';
  return L.divIcon({
    className: 'osm-street-label-wrapper',
    iconSize: [0, 0],
    iconAnchor: [0, 0],
    html: `<span class="${cls}" style="transform:translate(-50%,-50%) rotate(${angleDeg.toFixed(1)}deg)">${name}</span>`,
  });
}

const TRAFFIC_SIGNAL_ICON = L.divIcon({
  className: 'osm-signal-icon',
  iconSize: [12, 20],
  iconAnchor: [6, 10],
  html: `<svg width="12" height="20" viewBox="0 0 12 20" style="display:block">
    <rect x="1" y="1" width="10" height="18" rx="4" fill="#1e293b" stroke="#ffffff" stroke-width="1.4"/>
    <circle cx="6" cy="5.2" r="2.1" fill="#ef4444"/>
    <circle cx="6" cy="10" r="2.1" fill="#f59e0b"/>
    <circle cx="6" cy="14.8" r="2.1" fill="#10b981"/>
  </svg>`,
});

/**
 * OsmNetworkLayer – `midtown_east.osm` dosyasından ayrıştırılan yol ağını,
 * yön oklarını, sokak isimlerini ve trafik ışıklarını internetten bağımsız çizer.
 */
export default function OsmNetworkLayer({
  network,
  selectedElement,
  onElementSelect,
}) {
  const map = useMap();
  const [zoom, setZoom] = useState(() => map.getZoom() || 16);

  useMapEvents({
    zoomend: () => setZoom(map.getZoom()),
  });

  // Zoom seviyesine göre yol kalınlığı çarpanı
  const zoomScale = useMemo(() => {
    const z = Math.max(13, Math.min(19, zoom));
    return Math.pow(1.38, z - 16);
  }, [zoom]);

  const arrowIcons = useMemo(() => {
    if (!network?.onewayMarkers) return [];
    return network.onewayMarkers.map((m) => ({
      ...m,
      icon: createArrowDivIcon(m.angleDeg),
    }));
  }, [network]);

  const labelIcons = useMemo(() => {
    if (!network?.streetLabels) return [];
    return network.streetLabels.map((l) => ({
      ...l,
      icon: createStreetLabelDivIcon(l.name, l.angleDeg, l.isAvenue),
    }));
  }, [network]);

  if (!network?.ways?.length) return null;

  const showDetails = zoom >= 15;

  return (
    <>
      {/* 1. Katman: Tüm yolların dış kenar çizgileri (casings) – kavşakların kesintisiz birleşmesi için */}
      {network.ways.map((way) => {
        const style = ROAD_PALETTE[way.highway] || ROAD_PALETTE.residential;
        const laneBoost = Math.max(0, (way.lanes - 2) * 1.1);
        const innerW = (style.baseWidth + laneBoost) * zoomScale;
        const casingW = innerW + 2.8 * Math.min(1.3, zoomScale);
        const isSelected = selectedElement?.id === way.id;

        return (
          <Polyline
            key={`casing-${way.id}`}
            positions={way.coords}
            interactive={false}
            pathOptions={{
              color: isSelected ? '#1d4ed8' : style.casing,
              weight: isSelected ? casingW + 2 : casingW,
              opacity: 1,
              lineCap: 'round',
              lineJoin: 'round',
            }}
          />
        );
      })}

      {/* 2. Katman: Tüm yolların iç dolgusu ve tıklama/üzerine gelme etkileşimi */}
      {network.ways.map((way) => {
        const style = ROAD_PALETTE[way.highway] || ROAD_PALETTE.residential;
        const laneBoost = Math.max(0, (way.lanes - 2) * 1.1);
        const innerW = (style.baseWidth + laneBoost) * zoomScale;
        const isSelected = selectedElement?.id === way.id;

        return (
          <Polyline
            key={`inner-${way.id}`}
            positions={way.coords}
            pathOptions={{
              color: isSelected ? '#60a5fa' : style.inner,
              weight: innerW,
              opacity: 1,
              lineCap: 'round',
              lineJoin: 'round',
            }}
            eventHandlers={{
              click: (e) => {
                L.DomEvent.stopPropagation(e);
                onElementSelect?.(way);
              },
            }}
          >
            <Tooltip sticky direction="top" offset={[0, -6]} className="osm-road-tooltip">
              <strong>{way.name || `Yol #${way.id}`}</strong>
              <div>
                {HIGHWAY_TR_LABEL[way.highway] || way.highway} · {way.lanes} şerit ·{' '}
                {way.isOneway ? 'Tek yön' : 'Çift yön'}
                {way.maxspeed ? ` · ${way.maxspeed}` : ''}
              </div>
            </Tooltip>
          </Polyline>
        );
      })}

      {/* 3. Katman: Tek yön okları */}
      {showDetails &&
        arrowIcons.map((m) => (
          <Marker
            key={m.id}
            position={m.position}
            icon={m.icon}
            interactive={false}
          />
        ))}

      {/* 4. Katman: Sokak ve cadde isimleri */}
      {showDetails &&
        labelIcons.map((l) => (
          <Marker
            key={l.id}
            position={l.position}
            icon={l.icon}
            interactive={false}
          />
        ))}

      {/* 5. Katman: midtown_east.osm içindeki trafik ışıkları (highway=traffic_signals) */}
      {showDetails &&
        network.trafficSignals.map((sig) => (
          <Marker
            key={`sig-${sig.id}`}
            position={[sig.lat, sig.lon]}
            icon={TRAFFIC_SIGNAL_ICON}
            eventHandlers={{
              click: (e) => {
                L.DomEvent.stopPropagation(e);
                onElementSelect?.({
                  id: sig.id,
                  type: 'node',
                  highway: 'traffic_signals',
                  lat: sig.lat,
                  lon: sig.lon,
                  tags: sig.tags,
                });
              },
            }}
          >
            <Tooltip direction="top" offset={[0, -10]} className="osm-road-tooltip">
              <strong>Trafik Sinyali</strong>
              <div>OSM Düğüm #{sig.id}</div>
            </Tooltip>
          </Marker>
        ))}
    </>
  );
}
