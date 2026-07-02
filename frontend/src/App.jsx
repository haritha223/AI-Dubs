import React, { useState } from 'react';
import Home from './components/Home';
import Processing from './components/Processing';
import Results from './components/Results';
import AzureBadge from './components/AzureBadge';
import { useConfig } from './hooks/useConfig';

function App() {
  const [view, setView] = useState('home'); // 'home' | 'processing' | 'results'
  const [taskId, setTaskId] = useState(null);
  const [taskData, setTaskData] = useState(null);
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [targetLanguage, setTargetLanguage] = useState('Tamil');

  // Fetch backend config once (Azure status, model names, etc.)
  const { isAzureConfigured, whisperModel, nllbModel, loading: configLoading, error: configError } = useConfig();

  const startJob = (url, lang, id) => {
    setYoutubeUrl(url);
    setTargetLanguage(lang);
    setTaskId(id);
    setView('processing');
  };

  const showResults = (data) => {
    setTaskData(data);
    setView('results');
  };

  const reset = () => {
    setTaskId(null);
    setTaskData(null);
    setYoutubeUrl('');
    setView('home');
  };

  return (
    <div className="min-h-screen bg-gradient-mesh text-slate-100 flex flex-col font-sans">

      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="border-b border-white/[0.04] bg-slate-950/50 backdrop-blur-xl px-6 py-4 flex justify-between items-center sticky top-0 z-50 animate-fade-in">
        {/* Logo */}
        <div
          className="flex items-center space-x-3 cursor-pointer group"
          onClick={reset}
        >
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/25 text-xl transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3">
            🎙️
          </div>
          <span className="font-bold text-xl tracking-tight shimmer-text">
            Antigravity Dubs
          </span>
        </div>

        {/* Right side — config indicator */}
        <div className="flex items-center gap-3">
          {/* Whisper model pill */}
          {whisperModel && !configLoading && !configError && (
            <span className="hidden sm:flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full bg-slate-800/60 text-slate-400 font-medium border border-slate-700/40">
              🎙️ whisper/{whisperModel}
            </span>
          )}
          {/* Azure / TTS status badge */}
          <AzureBadge
            isAzureConfigured={isAzureConfigured}
            loading={configLoading}
            error={configError}
          />
        </div>
      </header>

      {/* ── Main Content ───────────────────────────────────────── */}
      <main className="flex-1 flex flex-col justify-center items-center px-4 py-8 md:p-12 w-full max-w-7xl mx-auto relative z-10">
        {view === 'home' && (
          <Home
            onStart={startJob}
            isAzureConfigured={isAzureConfigured}
          />
        )}
        {view === 'processing' && (
          <Processing
            taskId={taskId}
            youtubeUrl={youtubeUrl}
            targetLanguage={targetLanguage}
            onComplete={showResults}
            onCancel={reset}
          />
        )}
        {view === 'results' && <Results data={taskData} onBack={reset} />}
      </main>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer className="border-t border-white/[0.04] bg-slate-950/30 px-6 py-4 text-center text-xs text-slate-500 relative z-10">
        © 2026{' '}
        <span className="text-indigo-400 font-medium">Antigravity Dubs</span>.
        Built for seamless local & cloud video dubbing.
      </footer>
    </div>
  );
}

export default App;
