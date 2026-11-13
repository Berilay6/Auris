import { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import { maplibreGL } from '@maplibre/maplibre-gl-leaflet';
import 'maplibre-gl/dist/maplibre-gl.css';
import { PILOT_TRAFFIC_SIGNALS_GEOJSON } from '../../constants/pilotTrafficSignals.js';

// Ticari mekanlar (poi), kapı numaraları (housenumber) ve havalimanı etiketleri gizlenir;
// ulaşım durakları (otobüs/metro) ise aşağıda ayrı filtreli katman olarak eklenir.
export const DEFAULT_HIDDEN_SOURCE_LAYERS = ['poi', 'housenumber', 'aerodrome_label'];

const ICON_ONEWAY_ARROW = 'auris-oneway-arrow';
const ICON_TRAFFIC_SIGNAL = 'auris-traffic-signal';

/**
 * Tek yön oku ikonu (+X yönüne bakan, beyaz haleli koyu arduvaz ok).
 * MapLibre `symbol-placement: "line"` ile yol doğrultusunda otomatik döndürülür.
 */
function createOnewayArrowImageData() {
  const width = 36;
  const height = 18;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  const drawArrow = () => {
    ctx.beginPath();
    ctx.moveTo(4, 7);
    ctx.lineTo(22, 7);
    ctx.lineTo(22, 3);
    ctx.lineTo(33, 9);
    ctx.lineTo(22, 15);
    ctx.lineTo(22, 11);
    ctx.lineTo(4, 11);
    ctx.closePath();
  };

  ctx.lineJoin = 'round';
  ctx.lineWidth = 3;
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.92)';
  drawArrow();
  ctx.stroke();

  ctx.fillStyle = '#334155';
  drawArrow();
  ctx.fill();

  return ctx.getImageData(0, 0, width, height);
}

/**
 * OSM tarzı dikey 3 lambalı (kırmızı-sarı-yeşil) trafik ışığı ikonu.
 */
function createTrafficSignalImageData() {
  const width = 22;
  const height = 38;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  // Beyaz dış konturlu koyu gövde
  ctx.beginPath();
  ctx.roundRect(3, 2, 16, 34, 7);
  ctx.fillStyle = '#1e293b';
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = '#ffffff';
  ctx.stroke();

  // Kırmızı, sarı, yeşil sinyal lambaları
  const lights = [
    { y: 9.5, color: '#ef4444' },
    { y: 19, color: '#f59e0b' },
    { y: 28.5, color: '#10b981' },
  ];
  for (const { y, color } of lights) {
    ctx.beginPath();
    ctx.arc(11, y, 3.6, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }

  return ctx.getImageData(0, 0, width, height);
}

function registerCustomIcons(glMap) {
  if (!glMap) return;
  const ensureIcons = () => {
    if (!glMap.hasImage(ICON_ONEWAY_ARROW)) {
      glMap.addImage(ICON_ONEWAY_ARROW, createOnewayArrowImageData(), { pixelRatio: 2 });
    }
    if (!glMap.hasImage(ICON_TRAFFIC_SIGNAL)) {
      glMap.addImage(ICON_TRAFFIC_SIGNAL, createTrafficSignalImageData(), { pixelRatio: 2 });
    }
  };

  ensureIcons();
  glMap.on('styleimagemissing', (e) => {
    if (e.id === ICON_ONEWAY_ARROW || e.id === ICON_TRAFFIC_SIGNAL) {
      ensureIcons();
    }
  });
}

/**
 * Positron stilini zenginleştirir:
 *  - Bina, zemin ve yol hiyerarşisi (ana arter, cadde, ara sokak) ton farkı
 *  - Tek yön okları (oneway = 1 / -1)
 *  - OSM trafik ışıkları (highway=traffic_signals)
 *  - Yalnızca ulaşım durakları (otobüs / metro); restoran ve dükkanlar gizli kalır
 */
function buildRoadRichStyle(style, hiddenSourceLayers) {
  const filtered = style.layers.filter(
    (layer) => !hiddenSourceLayers.includes(layer['source-layer'])
  );

  const layers = [];

  for (const raw of filtered) {
    const layer = {
      ...raw,
      paint: raw.paint ? { ...raw.paint } : {},
    };

    switch (layer.id) {
      case 'background':
        layer.paint['background-color'] = '#ebeef2';
        break;

      case 'landuse_residential':
        layer.paint['fill-color'] = '#e6eaef';
        break;

      case 'park':
        layer.paint['fill-color'] = '#d7ead9';
        break;

      case 'water':
        layer.paint['fill-color'] = '#b8cedc';
        break;

      case 'building':
        layer.paint['fill-color'] = '#d4dbe4';
        layer.paint['fill-outline-color'] = '#b3bdcb';
        break;

      case 'highway_path':
        layer.paint['line-color'] = '#cbd5e1';
        layer.paint['line-dasharray'] = [2, 2];
        break;

      case 'highway_minor': {
        // Ara sokaklar (E 50th, E 51st vb.): belirgin kenar çizgisi + beyaz iç dolgu
        layers.push({
          ...layer,
          id: 'highway_minor_casing',
          paint: {
            ...layer.paint,
            'line-color': '#b0bac8',
            'line-opacity': 1,
            'line-width': ['interpolate', ['exponential', 1.55], ['zoom'], 13, 3.2, 20, 24],
          },
        });
        layer.paint['line-color'] = '#ffffff';
        layer.paint['line-opacity'] = 1;
        break;
      }

      case 'highway_major_casing':
        // Ana arter ve caddelerin kenar çizgisi (OSM tarzı sıcak gri-kehribar tonu)
        layer.paint['line-color'] = [
          'match',
          ['get', 'class'],
          ['primary', 'trunk'],
          '#c29d48',
          '#baa870',
        ];
        break;

      case 'highway_major_inner':
        // Ana arterler (Park, 3rd Ave) sıcak kehribar-krem; caddeler (Lexington, E 57th) açık krem
        layer.paint['line-color'] = [
          'match',
          ['get', 'class'],
          ['primary', 'trunk'],
          '#fde9a8',
          '#fef6d0',
        ];
        break;

      case 'highway_motorway_casing':
      case 'highway_motorway_bridge_casing':
        layer.paint['line-color'] = '#b88746';
        break;

      case 'highway_motorway_inner':
      case 'highway_motorway_bridge_inner':
        layer.paint['line-color'] = '#fcd68a';
        break;

      case 'railway':
      case 'railway_transit':
      case 'railway_service':
        // Yeraltı demiryolu hatlarının (Park Ave altı) cadde görünümünü bozmaması için yumuşat
        layer.paint['line-opacity'] = 0.35;
        break;

      case 'railway_dashline':
      case 'railway_transit_dashline':
      case 'railway_service_dashline':
        layer.paint['line-opacity'] = 0.35;
        break;

      case 'highway-name-minor':
      case 'highway-name-major':
        layer.paint['text-color'] = '#1e293b';
        layer.paint['text-halo-color'] = '#ffffff';
        layer.paint['text-halo-width'] = 1.6;
        break;

      default:
        break;
    }

    layers.push(layer);
  }

  // Kavşaklarda kenar çizgisinin ara sokak ağzını kesmemesi için
  // highway_major_casing katmanını highway_minor öncesine taşı.
  const minorIdx = layers.findIndex((l) => l.id === 'highway_minor');
  const majorCasingIdx = layers.findIndex((l) => l.id === 'highway_major_casing');
  if (minorIdx !== -1 && majorCasingIdx > minorIdx) {
    const [majorCasing] = layers.splice(majorCasingIdx, 1);
    layers.splice(minorIdx, 0, majorCasing);
  }

  // 1) Tek yön okları (oneway = 1 ve oneway = -1)
  const roadClasses = ['primary', 'secondary', 'tertiary', 'trunk', 'minor', 'service'];
  const nameLayerIdx = layers.findIndex((l) => l.id === 'highway-name-minor');
  const insertArrowIdx = nameLayerIdx !== -1 ? nameLayerIdx : layers.length;

  layers.splice(
    insertArrowIdx,
    0,
    {
      id: 'road_one_way_arrow',
      type: 'symbol',
      source: 'openmaptiles',
      'source-layer': 'transportation',
      minzoom: 14.5,
      filter: [
        'all',
        ['==', ['get', 'oneway'], 1],
        ['match', ['get', 'class'], roadClasses, true, false],
        ['!=', ['get', 'brunnel'], 'tunnel'],
      ],
      layout: {
        'symbol-placement': 'line',
        'symbol-spacing': 135,
        'icon-image': ICON_ONEWAY_ARROW,
        'icon-size': ['interpolate', ['linear'], ['zoom'], 14.5, 0.7, 17, 1.0],
        'icon-rotation-alignment': 'map',
        'icon-padding': 2,
      },
      paint: {
        'icon-opacity': 0.88,
      },
    },
    {
      id: 'road_one_way_arrow_opposite',
      type: 'symbol',
      source: 'openmaptiles',
      'source-layer': 'transportation',
      minzoom: 14.5,
      filter: [
        'all',
        ['==', ['get', 'oneway'], -1],
        ['match', ['get', 'class'], roadClasses, true, false],
        ['!=', ['get', 'brunnel'], 'tunnel'],
      ],
      layout: {
        'symbol-placement': 'line',
        'symbol-spacing': 135,
        'icon-image': ICON_ONEWAY_ARROW,
        'icon-rotate': 180,
        'icon-size': ['interpolate', ['linear'], ['zoom'], 14.5, 0.7, 17, 1.0],
        'icon-rotation-alignment': 'map',
        'icon-padding': 2,
      },
      paint: {
        'icon-opacity': 0.88,
      },
    }
  );

  // 2) Yalnızca ulaşım durakları (otobüs durağı ve metro istasyonu) – restoran/dükkanlar hariç
  layers.push({
    id: 'poi_transit_only',
    type: 'symbol',
    source: 'openmaptiles',
    'source-layer': 'poi',
    minzoom: 15.5,
    filter: ['match', ['get', 'class'], ['bus', 'railway'], true, false],
    layout: {
      'icon-image': [
        'match',
        ['get', 'subclass'],
        ['subway', 'metro'],
        'railway_metro',
        ['get', 'class'],
      ],
      'icon-size': 0.75,
      'text-field': [
        'case',
        ['==', ['get', 'class'], 'railway'],
        ['coalesce', ['get', 'name_en'], ['get', 'name']],
        '',
      ],
      'text-font': ['Open Sans Regular'],
      'text-size': 10,
      'text-anchor': 'top',
      'text-offset': [0, 0.7],
      'text-optional': true,
    },
    paint: {
      'text-color': '#1d4ed8',
      'text-halo-color': '#ffffff',
      'text-halo-width': 1.2,
    },
  });

  // 3) OSM Trafik Işıkları (highway=traffic_signals)
  layers.push({
    id: 'osm_traffic_signals',
    type: 'symbol',
    source: 'osm_traffic_signals',
    minzoom: 15,
    layout: {
      'icon-image': ICON_TRAFFIC_SIGNAL,
      'icon-size': ['interpolate', ['linear'], ['zoom'], 15, 0.7, 17, 1.0, 19, 1.15],
      'icon-allow-overlap': true,
      'icon-ignore-placement': true,
    },
  });

  return {
    ...style,
    sources: {
      ...style.sources,
      osm_traffic_signals: {
        type: 'geojson',
        data: PILOT_TRAFFIC_SIGNALS_GEOJSON,
      },
    },
    layers,
  };
}

/**
 * VectorBaseLayer – OSM vektör karolarını (MapLibre GL) Leaflet haritasına altlık olarak ekler.
 */
export default function VectorBaseLayer({
  styleUrl,
  attribution,
  hiddenSourceLayers = DEFAULT_HIDDEN_SOURCE_LAYERS,
}) {
  const map = useMap();

  useEffect(() => {
    let layer = null;
    let cancelled = false;

    fetch(styleUrl)
      .then((res) => {
        if (!res.ok) throw new Error(`Stil yüklenemedi (${res.status})`);
        return res.json();
      })
      .then((style) => {
        if (cancelled) return;
        const enhancedStyle = buildRoadRichStyle(style, hiddenSourceLayers);
        layer = maplibreGL({ style: enhancedStyle, attribution, interactive: false }).addTo(map);
        registerCustomIcons(layer.getMaplibreMap());
      })
      .catch((err) => console.error('[VectorBaseLayer]', err));

    return () => {
      cancelled = true;
      if (layer) map.removeLayer(layer);
    };
  }, [map, styleUrl, attribution, hiddenSourceLayers]);

  return null;
}
