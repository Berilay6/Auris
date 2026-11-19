// Pilot bölge: Manhattan – Lexington Ave, 49th–61st St (Park Ave – 3rd Ave)
// Kaynak: config/pilot_region.yaml ve auris-data/base_network/midtown_east.osm
export const PILOT_REGION = {
  id: 'midtown_east',
  label: 'Pilot Bölge: Lexington Ave (49th–61st St), NYC',
  // Izgaraya hizalı poligon [enlem, boylam]
  boundary: [
    [40.764299, -73.969033], // Park Ave & E 61st St
    [40.762812, -73.965559], // 3rd Ave & E 61st St
    [40.755086, -73.971186], // 3rd Ave & E 49th St
    [40.756583, -73.974676], // Park Ave & E 49th St
  ],
  center: [40.759695, -73.970114],
  zoom: 16,
};

export const OFFLINE_ATTRIBUTION =
  'Veri: <code>midtown_east.osm</code> (çevrimdışı) · &copy; OpenStreetMap katkıda bulunanlar (ODbL)';

// Bina adası zemin dolgusu (yolların altında kalır, yollar aradaki blokları ayırır)
export const PILOT_BLOCK_FILL_STYLE = {
  stroke: false,
  fill: true,
  fillColor: '#d3dae4',
  fillOpacity: 0.95,
};

// Pilot bölge kesikli dış sınır çizgisi
export const PILOT_BOUNDARY_STYLE = {
  color: '#0f1f3d',
  weight: 2.2,
  dashArray: '6 6',
  fill: false,
};
