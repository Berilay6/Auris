import { Polygon } from 'react-leaflet';
import { PILOT_BOUNDARY_STYLE } from '../../constants/mapConfig.js';

/**
 * PilotBoundaryLayer – pilot bölge sınırını kesikli poligon olarak çizer.
 * interactive=false: ileride eklenecek yol ağı (edge/node) tıklamalarını engellemez.
 */
export default function PilotBoundaryLayer({ boundary, pathOptions = PILOT_BOUNDARY_STYLE }) {
  if (!boundary?.length) return null;
  return <Polygon positions={boundary} pathOptions={pathOptions} interactive={false} />;
}
