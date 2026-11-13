// Zaman aralığı seçenekleri. `id` backend'e (AS2) gönderilecek anahtardır.
export const TIME_WINDOWS = [
  { id: 'peak_am', label: 'Peak Hour (07:00–09:00)', shortLabel: 'Peak Hour 07:00–09:00' },
  { id: 'midday', label: 'Midday (11:00–13:00)', shortLabel: 'Midday 11:00–13:00' },
  { id: 'peak_pm', label: 'Evening Peak (17:00–19:00)', shortLabel: 'Evening Peak 17:00–19:00' },
  { id: 'night', label: 'Night (22:00–00:00)', shortLabel: 'Night 22:00–00:00' },
];

export const DEFAULT_TIME_WINDOW_ID = 'peak_am';

export const getTimeWindow = (id) =>
  TIME_WINDOWS.find((w) => w.id === id) ?? TIME_WINDOWS[0];
