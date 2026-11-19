import { useEffect } from 'react';
import { MapContainer, Polygon, ZoomControl, useMap, useMapEvents } from 'react-leaflet';
import { OFFLINE_ATTRIBUTION, PILOT_BOUNDARY_STYLE, PILOT_REGION } from '../../constants/mapConfig.js';
import OsmNetworkLayer from './OsmNetworkLayer.jsx';
import PilotBoundaryLayer from './PilotBoundaryLayer.jsx';

function OfflineAttributionAndClickClear({ onElementSelect }) {
  const map = useMap();

  useEffect(() => {
    map.attributionControl?.setPrefix('Leaflet');
    map.attributionControl?.addAttribution(OFFLINE_ATTRIBUTION);
    return () => {
      map.attributionControl?.removeAttribution(OFFLINE_ATTRIBUTION);
    };
  }, [map]);

  useMapEvents({
    click: () => onElementSelect?.(null),
  });

  return null;
}

/**
 * NetworkMap – `midtown_east.osm` dosyasından internet bağlantısı gerektirmeden
 * çizilen interaktif harita (S1 sol alan).
 *
 * Sunum bileşenidir; hesaplama yapmaz. Gelecek katmanlar `children` olarak
 * MapContainer içine enjekte edilir:
 *   - Isı haritası        -> <CongestionLayer results />
 *   - S5 darboğaz pinleri -> <AlertMarker alerts />
 *
 * @param {object}   props
 * @param {Array<[number, number]>} [props.boundary] Pilot bölge poligonu
 * @param {[number, number]} [props.center]   Yedek harita merkezi
 * @param {number}   [props.zoom]             Yedek zoom seviyesi
 * @param {boolean}  [props.showBoundary]     Pilot bölge sınırını çiz
 * @param {string}   [props.overlayLabel]     Sol üst bilgi etiketi
 * @param {object|null} [props.network]       Ayrıştırılmış `midtown_east.osm` ağ verisi
 * @param {object|null} [props.selectedElement] Seçili edge/node ({ id, type, ... })
 * @param {(el: object|null) => void} [props.onElementSelect] Eleman seçimi callback'i
 * @param {(map: L.Map) => void} [props.onMapReady] Leaflet map örneğine erişim
 * @param {React.ReactNode} [props.children]  Ek harita katmanları
 */
export default function NetworkMap({
  boundary = PILOT_REGION.boundary,
  center = PILOT_REGION.center,
  zoom = PILOT_REGION.zoom,
  showBoundary = true,
  overlayLabel = PILOT_REGION.label,
  network = null,
  selectedElement = null,
  onElementSelect,
  onMapReady,
  children,
}) {
  const viewProps = boundary?.length
    ? { bounds: boundary, boundsOptions: { padding: [36, 36] } }
    : { center, zoom };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <MapContainer
        {...viewProps}
        minZoom={14}
        maxZoom={19}
        zoomControl={false}
        scrollWheelZoom
        dragging
        style={{ width: '100%', height: '100%' }}
        ref={onMapReady}
      >
        <OfflineAttributionAndClickClear onElementSelect={onElementSelect} />
        <ZoomControl position="bottomleft" />

        {/* 1. Pilot bölge ada dolgusu (yolların altında) */}
        {showBoundary && <PilotBoundaryLayer boundary={boundary} />}

        {/* 2. midtown_east.osm yol ağı, tek yön okları, sokak isimleri ve trafik ışıkları */}
        <OsmNetworkLayer
          network={network}
          selectedElement={selectedElement}
          onElementSelect={onElementSelect}
        />

        {/* 3. Pilot bölge kesikli dış çerçevesi (yolların üstünde net görünmesi için) */}
        {showBoundary && boundary?.length > 0 && (
          <Polygon positions={boundary} pathOptions={PILOT_BOUNDARY_STYLE} interactive={false} />
        )}

        {/* Gelecek katmanlar: ısı haritası, uyarı pinleri */}
        {children}
      </MapContainer>

      {overlayLabel && <div className="map-overlay-label">{overlayLabel}</div>}
    </div>
  );
}
