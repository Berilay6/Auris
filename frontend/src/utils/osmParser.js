// Manhattan (~40.76°N) enleminde boylam ölçek katsayısı
const COS_LAT = Math.cos((40.76 * Math.PI) / 180);
const METERS_PER_DEG_LAT = 111320;

function distanceMeters(a, b) {
  const dy = (b[0] - a[0]) * METERS_PER_DEG_LAT;
  const dx = (b[1] - a[1]) * METERS_PER_DEG_LAT * COS_LAT;
  return Math.hypot(dx, dy);
}

/**
 * Ekran koordinatlarında (+X sağ / doğu, +Y aşağı / güney) derece cinsinden açı.
 */
function screenAngleDeg(a, b) {
  const dy = -(b[0] - a[0]);
  const dx = (b[1] - a[1]) * COS_LAT;
  return (Math.atan2(dy, dx) * 180) / Math.PI;
}

/**
 * Yazıların baş aşağı durmaması için açıyı [-90°, +90°] aralığına katlar.
 */
function readableTextAngleDeg(angle) {
  let a = angle;
  if (a > 90) a -= 180;
  if (a < -90) a += 180;
  return a;
}

/**
 * Poliline orta noktasını ve o noktadaki teğet ekran açısını hesaplar.
 */
function polylineMidpointAndAngle(coords) {
  if (coords.length === 2) {
    return {
      point: [(coords[0][0] + coords[1][0]) / 2, (coords[0][1] + coords[1][1]) / 2],
      angleDeg: screenAngleDeg(coords[0], coords[1]),
    };
  }

  const segLengths = [];
  let total = 0;
  for (let i = 0; i < coords.length - 1; i++) {
    const len = distanceMeters(coords[i], coords[i + 1]);
    segLengths.push(len);
    total += len;
  }

  const half = total / 2;
  let acc = 0;
  for (let i = 0; i < segLengths.length; i++) {
    if (acc + segLengths[i] >= half && segLengths[i] > 0) {
      const t = (half - acc) / segLengths[i];
      const p0 = coords[i];
      const p1 = coords[i + 1];
      return {
        point: [p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t],
        angleDeg: screenAngleDeg(p0, p1),
      };
    }
    acc += segLengths[i];
  }

  const last = coords.length - 1;
  return {
    point: coords[Math.floor(last / 2)],
    angleDeg: screenAngleDeg(coords[0], coords[last]),
  };
}

const HIGHWAY_ORDER = {
  residential: 1,
  unclassified: 1,
  secondary: 2,
  tertiary: 2,
  primary_link: 3,
  primary: 3,
  trunk: 4,
};

/**
 * `midtown_east.osm` XML içeriğini internet bağlantısı gerektirmeden
 * haritada çizilebilecek yol ağı (ways), düğüm (nodes), trafik ışıkları ve
 * sokak etiketlerine dönüştürür.
 */
export function parseOsmXml(xmlString) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlString, 'application/xml');

  const boundsEl = doc.querySelector('bounds');
  const bounds = boundsEl
    ? [
        [parseFloat(boundsEl.getAttribute('minlat')), parseFloat(boundsEl.getAttribute('minlon'))],
        [parseFloat(boundsEl.getAttribute('maxlat')), parseFloat(boundsEl.getAttribute('maxlon'))],
      ]
    : null;

  const nodeMap = new Map();
  const trafficSignals = [];

  for (const nodeEl of doc.querySelectorAll('node')) {
    const id = nodeEl.getAttribute('id');
    const lat = parseFloat(nodeEl.getAttribute('lat'));
    const lon = parseFloat(nodeEl.getAttribute('lon'));
    const tags = {};
    for (const tagEl of nodeEl.querySelectorAll('tag')) {
      tags[tagEl.getAttribute('k')] = tagEl.getAttribute('v');
    }
    const node = { id, lat, lon, tags };
    nodeMap.set(id, node);
    if (tags.highway === 'traffic_signals') {
      trafficSignals.push(node);
    }
  }

  const ways = [];
  const onewayMarkers = [];
  let totalLengthM = 0;

  for (const wayEl of doc.querySelectorAll('way')) {
    const id = wayEl.getAttribute('id');
    const tags = {};
    for (const tagEl of wayEl.querySelectorAll('tag')) {
      tags[tagEl.getAttribute('k')] = tagEl.getAttribute('v');
    }
    if (!tags.highway) continue;

    const nodeIds = [];
    const coords = [];
    for (const ndEl of wayEl.querySelectorAll('nd')) {
      const ref = ndEl.getAttribute('ref');
      const node = nodeMap.get(ref);
      if (node) {
        nodeIds.push(ref);
        coords.push([node.lat, node.lon]);
      }
    }
    if (coords.length < 2) continue;

    let lengthM = 0;
    for (let i = 0; i < coords.length - 1; i++) {
      lengthM += distanceMeters(coords[i], coords[i + 1]);
    }
    totalLengthM += lengthM;

    const { point: midpoint, angleDeg } = polylineMidpointAndAngle(coords);
    const lanes = parseInt(tags.lanes, 10) || (tags.highway === 'primary' ? 3 : 2);
    const isOneway = tags.oneway === 'yes' || tags.oneway === '1' || tags.oneway === '-1';
    const arrowAngleDeg = tags.oneway === '-1' ? angleDeg + 180 : angleDeg;

    const way = {
      id,
      type: 'edge',
      nodeIds,
      coords,
      lengthM,
      midpoint,
      angleDeg,
      textAngleDeg: readableTextAngleDeg(angleDeg),
      lanes,
      isOneway,
      highway: tags.highway,
      name: tags.name || '',
      maxspeed: tags.maxspeed || '',
      order: HIGHWAY_ORDER[tags.highway] ?? 1,
      tags,
    };
    ways.push(way);

    // Yeterince uzun tek yönlü segmentlerin ortasına yön oku ekle
    if (isOneway && lengthM >= 32) {
      onewayMarkers.push({
        id: `arrow-${id}`,
        wayId: id,
        position: midpoint,
        angleDeg: arrowAngleDeg,
      });
    }
  }

  // Çizim sırası: önce ara sokaklar, üstte ana caddeler ve bulvarlar
  ways.sort((a, b) => a.order - b.order);

  // Her cadde/sokak için birbirine çok yakın olmayan etiket konumları seç
  const streetLabels = selectStreetLabels(ways);

  return {
    bounds,
    nodes: Array.from(nodeMap.values()),
    nodeMap,
    ways,
    trafficSignals,
    onewayMarkers,
    streetLabels,
    summary: {
      nodeCount: nodeMap.size,
      wayCount: ways.length,
      signalCount: trafficSignals.length,
      totalLengthKm: +(totalLengthM / 1000).toFixed(2),
    },
  };
}

function selectStreetLabels(ways) {
  const byName = new Map();
  for (const w of ways) {
    if (!w.name || w.lengthM < 45) continue;
    if (!byName.has(w.name)) byName.set(w.name, []);
    byName.get(w.name).push(w);
  }

  const labels = [];
  for (const [name, candidates] of byName.entries()) {
    // Uzun segmentleri önceliklendir
    const sorted = [...candidates].sort((a, b) => b.lengthM - a.lengthM);
    const isAvenue = /Avenue/i.test(name);
    const minSpacingM = isAvenue ? 260 : 220;
    const maxPerStreet = isAvenue ? 3 : 2;
    const picked = [];

    for (const seg of sorted) {
      if (picked.length >= maxPerStreet) break;
      const tooClose = picked.some(
        (other) => distanceMeters(seg.midpoint, other.midpoint) < minSpacingM
      );
      if (!tooClose) {
        picked.push(seg);
        labels.push({
          id: `label-${seg.id}`,
          name,
          isAvenue,
          position: seg.midpoint,
          angleDeg: seg.textAngleDeg,
        });
      }
    }
  }

  return labels;
}
