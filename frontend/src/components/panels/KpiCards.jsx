/**
 * KpiCards – alt alta çerçeveli özet gösterge kartları.
 * @param {{ items: Array<{ key: string, label: string, value: string }> }} props
 */
export default function KpiCards({ items = [] }) {
  return (
    <div className="kpi-list">
      {items.map((kpi) => (
        <div key={kpi.key} className="kpi-card">
          <p className="kpi-card__label">{kpi.label}</p>
          <p className="kpi-card__value">{kpi.value}</p>
        </div>
      ))}
    </div>
  );
}
