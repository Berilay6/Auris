import { TIME_WINDOWS } from '../../constants/timeWindows.js';

/**
 * TimeRangePicker – "Zaman Aralığı Seç" açılır kutusu (kontrollü bileşen).
 * @param {{ value: string, onChange: (id: string) => void, options?: Array, disabled?: boolean }} props
 */
export default function TimeRangePicker({ value, onChange, options = TIME_WINDOWS, disabled = false }) {
  return (
    <div className="time-picker">
      <label htmlFor="time-window-select">Zaman Aralığı Seç</label>
      <select
        id="time-window-select"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.value)}
      >
        {options.map((opt) => (
          <option key={opt.id} value={opt.id}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
