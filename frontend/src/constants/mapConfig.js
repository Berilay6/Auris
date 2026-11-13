// Pilot bölge: Manhattan – Lexington Ave, 49th–61st St (Park Ave – 3rd Ave)
// Kaynak: "Auris · Pilot bölge seçimi" raporu (Kasım 2026), Bölüm 1 – köşe koordinatları.
// Not: config/pilot_region.yaml ile senkron tutulmalı; ileride AS2'den (/api) okunacak.
export const PILOT_REGION = {
  id: 'lexington_49_61',
  label: 'Pilot Bölge: Lexington Ave (49th–61st St), NYC',
  // Izgaraya hizalı poligon, köşe kavşaklarını içerecek şekilde 15 m genişletilmiş.
  boundary: [
    [40.764299, -73.969033], // Park Ave / 61st St
    [40.762812, -73.965559], // 3rd Ave / 61st St
    [40.755086, -73.971186], // 3rd Ave / 49th St
    [40.756583, -73.974676], // Park Ave / 49th St
  ],
  // Köşelerin ortalaması – bounds kullanılamazsa yedek merkez.
  center: [40.759695, -73.970114],
  zoom: 16,
};

const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıda bulunanlar';
const OPENFREEMAP_ATTRIBUTION =
  `<a href="https://openfreemap.org" target="_blank">OpenFreeMap</a> ` +
  `&copy; <a href="https://www.openmaptiles.org/" target="_blank">OpenMapTiles</a> ${OSM_ATTRIBUTION}`;

/**
 * Altlık harita seçenekleri. Hepsi OpenStreetMap verisinden üretilir ve API anahtarı gerektirmez.
 *
 * type: 'vector' -> MapLibre GL ile çizilir (VectorBaseLayer); POI katmanları kod tarafında gizlenir.
 * type: 'raster' -> hazır PNG karolar (TileLayer); içerik değiştirilemez.
 *
 * - positron : açık gri, sade; sokak isimleri VAR, restoran/mağaza (POI) YOK  ← varsayılan
 * - liberty  : renkli OSM görünümü; POI katmanları gizlenerek kullanılır
 * - osm      : standart OSM raster; tüm POI ve bina isimleri görünür (yedek)
 */
export const BASEMAPS = {
  positron: {
    type: 'vector',
    styleUrl: 'https://tiles.openfreemap.org/styles/positron',
    attribution: OPENFREEMAP_ATTRIBUTION,
  },
  liberty: {
    type: 'vector',
    styleUrl: 'https://tiles.openfreemap.org/styles/liberty',
    attribution: OPENFREEMAP_ATTRIBUTION,
  },
  osm: {
    type: 'raster',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: OSM_ATTRIBUTION,
    subdomains: 'abc',
    maxZoom: 19,
  },
};

// Aktif altlık – değiştirmek için yalnızca bu satırı düzenleyin.
export const DEFAULT_BASEMAP = BASEMAPS.positron;

export const PILOT_BOUNDARY_STYLE = {
  color: '#0f1f3d',
  weight: 2,
  dashArray: '6 6',
  fillColor: '#0f1f3d',
  fillOpacity: 0.06,
};
