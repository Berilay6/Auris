import { useEffect, useState } from 'react';
import { get } from '../../api/client.js';

const LABELS = {
  checking: 'API: checking…',
  ok: 'API: ok',
  down: 'API: down',
};

/**
 * Small badge that shows whether the backend API is reachable.
 * It calls GET /api/health once, when the component is first shown.
 */
export default function ApiStatusBadge() {
  // One of: 'checking', 'ok', 'down'.
  const [status, setStatus] = useState('checking');

  useEffect(() => {
    let ignore = false;

    async function checkHealth() {
      try {
        await get('/health');
        if (!ignore) {
          setStatus('ok');
        }
      } catch (error) {
        if (!ignore) {
          console.error(error);
          setStatus('down');
        }
      }
    }

    checkHealth();

    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className={`api-status api-status--${status}`} role="status">
      {LABELS[status]}
    </div>
  );
}
