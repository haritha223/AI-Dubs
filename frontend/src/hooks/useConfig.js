import { useState, useEffect } from 'react';
import api from '../api';

/**
 * Fetches the backend /config endpoint once on mount.
 * Returns: { isAzureConfigured, whisperModel, nllbModel, loading, error }
 */
export function useConfig() {
  const [config, setConfig] = useState({
    isAzureConfigured: false,
    whisperModel: null,
    nllbModel: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get('/config')
      .then((res) => {
        if (!cancelled) {
          setConfig({
            isAzureConfigured: res.data.is_azure_configured ?? false,
            whisperModel: res.data.whisper_model ?? null,
            nllbModel: res.data.nllb_model ?? null,
          });
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  return { ...config, loading, error };
}
