import 'leaflet/dist/leaflet.css';
import MapDashboardScreen from './screens/MapDashboardScreen.jsx';

/**
 * Uygulama kökü. İleride ScenarioCartProvider (S2 senaryo sepeti) gibi
 * global context sağlayıcıları burada MapDashboardScreen'i sarmalayacak.
 */
export default function App() {
  return <MapDashboardScreen />;
}
