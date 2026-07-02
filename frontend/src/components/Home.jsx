import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Video,
  Languages,
  ArrowRight,
  AlertCircle,
  Sparkles,
  Zap,
  Globe,
  Mic,
  Cloud,
  MonitorSpeaker,
  ChevronDown,
  Link2,
} from 'lucide-react';

const LANGUAGES = [
  { label: '🇮🇳 Tamil',     value: 'Tamil' },
  { label: '🇮🇳 Telugu',    value: 'Telugu' },
  { label: '🇮🇳 Malayalam', value: 'Malayalam' },
  { label: '🇮🇳 Kannada',   value: 'Kannada' },
  { label: '🇬🇧 English',   value: 'English' },
  { label: '🇮🇳 Hindi',     value: 'Hindi' },
];

const FEATURES = [
  {
    icon: Zap,
    emoji: '⚡',
    title: 'Sub-Minute Sync',
    desc: 'Real-time timeline alignment',
    color: 'from-yellow-500/20 to-orange-500/10',
    ring: 'ring-yellow-500/20',
    iconColor: 'text-yellow-400',
  },
  {
    icon: Mic,
    emoji: '🎙️',
    title: 'Whisper STT',
    desc: 'OpenAI speech transcription',
    color: 'from-sky-500/20 to-blue-500/10',
    ring: 'ring-sky-500/20',
    iconColor: 'text-sky-400',
  },
  {
    icon: Globe,
    emoji: '🌐',
    title: 'NLLB-200 Translate',
    desc: 'Meta 200-language model',
    color: 'from-emerald-500/20 to-teal-500/10',
    ring: 'ring-emerald-500/20',
    iconColor: 'text-emerald-400',
  },
  {
    icon: MonitorSpeaker,
    emoji: '🗣️',
    title: 'Natural Indian TTS',
    desc: 'Azure / gTTS voice synthesis',
    color: 'from-purple-500/20 to-indigo-500/10',
    ring: 'ring-purple-500/20',
    iconColor: 'text-purple-400',
  },
];

function Home({ onStart, isAzureConfigured }) {
  const [url, setUrl] = useState('');
  const [language, setLanguage] = useState('Tamil');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mounted, setMounted] = useState(false);

  // Trigger mount animation
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 50);
    return () => clearTimeout(t);
  }, []);

  const validateYoutubeUrl = (urlStr) => {
    const regExp = /^(?:https?:\/\/)?(?:m\.|www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$/;
    return regExp.test(urlStr);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!url || !url.trim()) {
      setError('Please paste a YouTube video URL.');
      return;
    }
    if (!validateYoutubeUrl(url)) {
      setError('Please enter a valid YouTube URL (e.g., https://www.youtube.com/watch?v=...)');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`/translate?blocking=false`, {
        youtube_url: url.trim(),
        target_language: language,
      });

      if (response.data?.task_id) {
        onStart(url, language, response.data.task_id);
      } else {
        throw new Error('No task ID returned from translation server.');
      }
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
        'Could not communicate with the backend server. Make sure it is running on port 8000.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mt-4 md:mt-8 space-y-8">

      {/* ── Hero Section ─────────────────────────────────────── */}
      <div className={`text-center space-y-4 transition-all duration-700 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>

        {/* Floating badge */}
        <div className="inline-flex items-center gap-2 bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 rounded-full px-4 py-1.5 text-xs font-semibold tracking-wide animate-fade-in-up">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-bounce-subtle" />
          AI-Powered Dubbing Engine
          {isAzureConfigured && (
            <span className="ml-1 bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full text-[10px] border border-emerald-500/25">
              Azure TTS ✓
            </span>
          )}
        </div>

        {/* Main headline */}
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.1] animate-fade-in-up-d1">
          <span className="shimmer-text">Dub YouTube Videos</span>
          <br />
          <span className="text-white">Instantly with AI</span>
        </h1>

        {/* Sub-headline */}
        <p className="text-slate-400 max-w-lg mx-auto text-sm md:text-base leading-relaxed animate-fade-in-up-d2">
          Translate any video speech into natural local Indian languages using
          AI speech-to-speech synchronization — all in minutes.
        </p>
      </div>

      {/* ── Main Form Card ───────────────────────────────────── */}
      <div className={`transition-all duration-700 delay-200 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
        <form
          onSubmit={handleSubmit}
          className="gradient-border rounded-3xl p-6 md:p-10 shadow-2xl shadow-indigo-950/60 relative overflow-hidden space-y-6"
        >
          {/* Decorative background blobs */}
          <div className="absolute top-0 right-0 w-72 h-72 bg-indigo-600/8 rounded-full blur-3xl -z-10 animate-float" />
          <div className="absolute bottom-0 left-0 w-72 h-72 bg-purple-600/8 rounded-full blur-3xl -z-10 animate-float [animation-delay:2s]" />

          {/* YouTube URL Field */}
          <div className="space-y-2 animate-fade-in-up-d3">
            <label
              htmlFor="url"
              className="text-xs font-bold uppercase tracking-widest text-indigo-300/80 flex items-center gap-2"
            >
              <Link2 className="w-3.5 h-3.5 text-indigo-400" />
              YouTube Video URL
            </label>
            <div className="relative group">
              {/* Glow ring on focus-within */}
              <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-600/30 to-purple-600/30 rounded-2xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-300 blur-sm" />
              <input
                type="text"
                id="url"
                placeholder="https://www.youtube.com/watch?v=..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={loading}
                className="relative w-full bg-slate-950/90 border border-slate-800/80 rounded-2xl py-4 pl-4 pr-16 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 transition-all duration-300 input-glow shadow-inner disabled:opacity-50"
              />
              {url && (
                <button
                  type="button"
                  onClick={() => setUrl('')}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-200 text-xs font-semibold transition-colors duration-200 bg-slate-800/60 px-2 py-1 rounded-lg hover:bg-slate-700/60"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Language Dropdown */}
          <div className="space-y-2 animate-fade-in-up-d4">
            <label
              htmlFor="language"
              className="text-xs font-bold uppercase tracking-widest text-indigo-300/80 flex items-center gap-2"
            >
              <Languages className="w-3.5 h-3.5 text-indigo-400" />
              Target Dubbing Language
            </label>
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-600/30 to-purple-600/30 rounded-2xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-300 blur-sm" />
              <select
                id="language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                disabled={loading}
                className="relative w-full bg-slate-950/90 border border-slate-800/80 rounded-2xl py-4 px-4 pr-10 text-sm text-slate-100 focus:outline-none focus:border-indigo-500/60 appearance-none cursor-pointer transition-all duration-300 input-glow shadow-inner disabled:opacity-50"
              >
                {LANGUAGES.map(({ label, value }) => (
                  <option key={value} value={value} className="bg-slate-950 text-slate-200">
                    {label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500 w-4 h-4" />
            </div>
          </div>

          {/* Error Block */}
          {error && (
            <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs md:text-sm flex items-start gap-2.5 animate-scale-in">
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Submit Button */}
          <div className="animate-fade-in-up-d5">
            <button
              type="submit"
              disabled={loading}
              className="btn-glow w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold py-4 px-6 rounded-2xl transition-all duration-300 shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/45 hover:-translate-y-0.5 flex items-center justify-center gap-2.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:translate-y-0 group text-sm md:text-base"
            >
              {loading ? (
                <>
                  <svg className="animate-spin w-5 h-5 text-white/70" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>Submitting Video…</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5 text-indigo-200/80" />
                  <span>Start AI Dubbing</span>
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform duration-300" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* ── Feature Pills ────────────────────────────────────── */}
      <div className={`grid grid-cols-2 md:grid-cols-4 gap-3 transition-all duration-700 delay-500 ${mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
        {FEATURES.map((feat, idx) => {
          const Icon = feat.icon;
          return (
            <div
              key={idx}
              className={`feature-card glass-panel rounded-2xl p-4 ring-1 ${feat.ring} bg-gradient-to-br ${feat.color}`}
              style={{ animationDelay: `${0.6 + idx * 0.1}s` }}
            >
              <div className={`text-xl mb-2 ${feat.iconColor}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div className="text-xs font-bold text-slate-200 leading-tight">{feat.title}</div>
              <div className="text-[10px] text-slate-500 mt-0.5 leading-snug">{feat.desc}</div>
            </div>
          );
        })}
      </div>

      {/* ── TTS Engine Indicator ─────────────────────────────── */}
      <div className={`flex justify-center transition-all duration-700 delay-700 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
        <div className="inline-flex items-center gap-2 text-xs text-slate-500 bg-slate-900/40 rounded-full px-4 py-2 border border-slate-800/50">
          {isAzureConfigured ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <Cloud className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-medium">Azure Neural TTS enabled</span>
              <span className="text-slate-600">— premium voice quality</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-indigo-400/80" />
              <span>Using gTTS fallback</span>
              <span className="text-slate-600">— set AZURE_SPEECH_KEY for premium voices</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Home;
