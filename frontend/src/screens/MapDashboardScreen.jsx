import { useCallback, useMemo, useRef, useState } from 'react';
import midtownEastOsmRaw from '../../../auris-data/base_network/midtown_east.osm?raw';
import NetworkMap from '../components/map/NetworkMap.jsx';
import KpiCards from '../components/panels/KpiCards.jsx';
import TimeRangePicker from '../components/panels/TimeRangePicker.jsx';
import { PILOT_REGION } from '../constants/mapConfig.js';
import { DEFAULT_TIME_WINDOW_ID, getTimeWindow } from '../constants/timeWindows.js';
import { parseOsmXml } from '../utils/osmParser.js';

// S1 başlangıç KPI kartları – simülasyon/AS2 yanıtıyla güncellenecek.
const PLACEHOLDER_KPIS = [
  { key: 'totalVehicles', label: 'Toplam Araç', value: '1,284' },
  { key: 'avgSpeed', label: 'Ort. Hız', value: '23 km/s' },
  { key: 'networkLength', label: 'Ağ Uzunluğu', value: '6.4 km' },
];

/**
 * S1 – Harita Paneli (Map Dashboard)
 * Sol %80: NetworkMap (auris-data/base_network/midtown_east.osm çevrimdışı yol ağı)
 * Sağ %20: Karar Destek Paneli
 */
export default function MapDashboardScreen() {
  const mapRef = useRef(null);

  // `midtown_east.osm` dosyasını internetten bağımsız olarak ayrıştır
  const initialNetwork = useMemo(() => parseOsmXml(midtownEastOsmRaw), []);

  // --- Temel S1 state'leri ---
  const [selectedTimeWindow, setSelectedTimeWindow] = useState(DEFAULT_TIME_WINDOW_ID);
  const [activeScenario] = useState({ id: 'base', name: 'Base Scenario' });
  const [kpis, setKpis] = useState(PLACEHOLDER_KPIS); // eslint-disable-line no-unused-vars

  // --- Yol ağı & seçim (Edge/Node katmanı + S2 Drawer) ---
  const [network, setNetwork] = useState(initialNetwork);
  const [isRegionLoading, setIsRegionLoading] = useState(false);
  const [selectedElement, setSelectedElement] = useState(null);

  // --- Simülasyon (sonraki görev: S3/S3b modalları, Heatmap, S5 pinleri) ---
  // simulationStatus: 'idle' | 'running' | 'succeeded' | 'failed'
  const [simulationStatus] = useState('idle'); // eslint-disable-line no-unused-vars
  const [results] = useState(null); // eslint-disable-line no-unused-vars

  const timeWindow = useMemo(() => getTimeWindow(selectedTimeWindow), [selectedTimeWindow]);

  const handleElementSelect = useCallback((element) => {
    setSelectedElement(element);
    // S2: element seçildiğinde InterventionDrawer açılacak (isDrawerOpen = !!selectedElement)
  }, []);

  const handleLoadRegion = useCallback(async () => {
    setIsRegionLoading(true);
    try {
      setNetwork((prev) => prev || parseOsmXml(midtownEastOsmRaw));
      if (mapRef.current && PILOT_REGION.boundary?.length) {
        mapRef.current.fitBounds(PILOT_REGION.boundary, { padding: [36, 36] });
      }
      // TODO: AS2 hazır olduğunda networkApi.fetchNetwork({ timeWindow: selectedTimeWindow })
    } finally {
      setIsRegionLoading(false);
    }
  }, []);

  return (
    <div className="dashboard">
      {/* Sol %80 – Harita */}
      <main className="dashboard__map">
        <NetworkMap
          network={network}
          selectedElement={selectedElement}
          onElementSelect={handleElementSelect}
          onMapReady={(mapInstance) => {
            mapRef.current = mapInstance;
          }}
        >
          {/* <CongestionLayer />, <AlertMarker /> buraya eklenecek */}
        </NetworkMap>
      </main>

      {/* Sağ %20 – Karar Destek Paneli */}
      <aside className="dashboard__sidebar">
        <header className="sidebar__header">
          <h1>TOBB ETÜ</h1>
          <h2>Karar Destek Paneli</h2>
        </header>

        <hr className="sidebar__divider" />

        <section className="scenario-info">
          <p className="sidebar__section-label">Aktif Senaryo:</p>
          <p className="scenario-info__name">{activeScenario.name}</p>
          <p className="scenario-info__window">{timeWindow.shortLabel}</p>
        </section>

        <KpiCards items={kpis} />

        <section className="sidebar__controls">
          <TimeRangePicker
            value={selectedTimeWindow}
            onChange={setSelectedTimeWindow}
            disabled={isRegionLoading}
          />
          <button
            type="button"
            className="btn-primary"
            onClick={handleLoadRegion}
            disabled={isRegionLoading}
          >
            {isRegionLoading ? 'Yükleniyor…' : 'Bölgeyi Yükle'}
          </button>
        </section>
      </aside>

      {/* S2 InterventionDrawer, S3 SimulationProgressModal, S3b ValidationErrorModal buraya eklenecek */}
    </div>
  );
}
