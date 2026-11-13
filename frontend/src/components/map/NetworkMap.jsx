import { MapContainer, TileLayer, ZoomControl } from 'react-leaflet';
import { PILOT_REGION, DEFAULT_BASEMAP } from '../../constants/mapConfig.js';
import PilotBoundaryLayer from './PilotBoundaryLayer.jsx';
import VectorBaseLayer from './VectorBaseLayer.jsx';

/**
 * NetworkMap – OSM altlıklı interaktif harita (S1 sol alan).
 *
 * Sunum bileşenidir; hesaplama yapmaz. Gelecek katmanlar `children` olarak
 * MapContainer içine enjekte edilir (react-leaflet context'ine erişebilirler):
 *   - Yol ağı (Edge/Node) katmanı  -> <ElementSelector network selectedElement onElementSelect />
 *   - Isı haritası                  -> <CongestionLayer results />
 *   - S5 darboğaz pinleri           -> <AlertMarker alerts />
 *
 * @param {object}   props
 * @param {Array<[number, number]>} [props.boundary] Pilot bölge poligonu; verilirse harita bu sınıra sığdırılır
 * @param {[number, number]} [props.center]   Yedek harita merkezi (boundary yoksa)
 * @param {number}   [props.zoom]             Yedek zoom seviyesi (boundary yoksa)
 * @param {boolean}  [props.showBoundary]     Pilot bölge sınırını çiz
 * @param {object}   [props.tileLayer]
 *        Altlık (mapConfig BASEMAPS girdisi). Varsayılan: DEFAULT_BASEMAP – POI'siz OpenFreeMap Positron
 * @param {string}   [props.overlayLabel]     Sol üst bilgi etiketi
 * @param {object|null} [props.network]       AS2'den gelen yol ağı (GeoJSON vb.) – ileride kullanılacak
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
  tileLayer: basemap = DEFAULT_BASEMAP,
  overlayLabel = PILOT_REGION.label,
  network = null, // eslint-disable-line no-unused-vars
  selectedElement = null, // eslint-disable-line no-unused-vars
  onElementSelect, // eslint-disable-line no-unused-vars
  onMapReady,
  children,
}) {
  // Poligon varsa haritayı ona sığdır (ekran boyutundan bağımsız), yoksa center/zoom kullan.
  const viewProps = boundary?.length
    ? { bounds: boundary, boundsOptions: { padding: [40, 40] } }
    : { center, zoom };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <MapContainer
        {...viewProps}
        zoomControl={false}
        scrollWheelZoom
        dragging
        style={{ width: '100%', height: '100%' }}
        ref={onMapReady}
      >
        {basemap.type === 'vector' ? (
          <VectorBaseLayer styleUrl={basemap.styleUrl} attribution={basemap.attribution} />
        ) : (
          <TileLayer
            url={basemap.url}
            attribution={basemap.attribution}
            subdomains={basemap.subdomains}
            maxZoom={basemap.maxZoom}
          />
        )}
        <ZoomControl position="bottomleft" />

        {showBoundary && <PilotBoundaryLayer boundary={boundary} />}

        {/* Gelecek katmanlar: yol ağı, ısı haritası, uyarı pinleri */}
        {children}
      </MapContainer>

      {overlayLabel && <div className="map-overlay-label">{overlayLabel}</div>}
    </div>
  );
}
