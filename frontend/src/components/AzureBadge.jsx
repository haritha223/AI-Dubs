import React from 'react';
import { Cloud, CloudOff, Loader2 } from 'lucide-react';

/**
 * AzureBadge — shows Azure TTS status fetched from /config.
 * Props: { isAzureConfigured: bool, loading: bool, error: any }
 */
export default function AzureBadge({ isAzureConfigured, loading, error }) {
  if (loading) {
    return (
      <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-slate-800/60 text-slate-400 font-semibold border border-slate-700/40 animate-pulse">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        Checking TTS…
      </span>
    );
  }

  if (error) {
    return (
      <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-slate-800/60 text-slate-500 font-semibold border border-slate-700/40">
        <CloudOff className="w-3.5 h-3.5" />
        Backend offline
      </span>
    );
  }

  if (isAzureConfigured) {
    return (
      <span className="relative flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/25 shadow-inner">
        {/* Animated pulse ring */}
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
        </span>
        <Cloud className="w-3.5 h-3.5" />
        Azure TTS active
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-indigo-500/10 text-indigo-400 font-semibold border border-indigo-500/20 shadow-inner">
      <span className="w-2 h-2 rounded-full bg-indigo-400/80" />
      NLLB-200 offline
    </span>
  );
}
