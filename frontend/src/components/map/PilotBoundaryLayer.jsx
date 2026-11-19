import { Polygon } from 'react-leaflet';
import { PILOT_BLOCK_FILL_STYLE, PILOT_BOUNDARY_STYLE } from '../../constants/mapConfig.js';

/**
 * PilotBoundaryLayer – pilot bölge adasını (#d3dae4) ve kesikli sınır çerçevesini çizer.
 * interactive=false: yol ağı (edge/node) tıklamalarını engellemez.
 */
export default function PilotBoundaryLayer({
  boundary,
  fillOptions = PILOT_BLOCK_FILL_STYLE,
  borderOptions = PILOT_BOUNDARY_STYLE,
}) {
  if (!boundary?.length) return null;
  return (
    <>
      <Polygon positions={boundary} pathOptions={fillOptions} interactive={false} />
      <Polygon positions={boundary} pathOptions={borderOptions} interactive={false} />
    </>
  );
}
