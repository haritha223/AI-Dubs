import React, { useState, useRef } from 'react';
import { ArrowLeft, Download, PlayCircle, FileText, CheckCircle2 } from 'lucide-react';

function TranscriptCard({ title, icon, segments, colorClass }) {
  return (
    <div className="glass-panel rounded-2xl overflow-hidden flex flex-col h-full">
      <div className={`px-5 py-3.5 border-b border-white/5 flex items-center space-x-2 ${colorClass}`}>
        <span>{icon}</span>
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        <span className="ml-auto text-xs text-slate-500">{segments.length} segments</span>
      </div>
      <div className="overflow-y-auto flex-1 p-3 space-y-2 max-h-80">
        {segments.map((seg, idx) => (
          <div key={idx} className="flex space-x-2 group">
            <span className="text-xs text-indigo-500 font-mono tabular-nums pt-0.5 flex-shrink-0">
              {formatTime(seg.start)}
            </span>
            <p className="text-xs text-slate-300 leading-relaxed group-hover:text-slate-100 transition-colors">
              {seg.text || seg.original_text || '—'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTime(seconds) {
  if (!seconds && seconds !== 0) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

function Results({ data, onBack }) {
  const videoRef = useRef(null);
  const [videoError, setVideoError] = useState(false);

  const {
    original_transcript = [],
    translated_transcript = [],
    dubbed_video_url = '',
    original_video_url = '',
  } = data || {};

  const handleDownload = () => {
    if (dubbed_video_url) {
      const a = document.createElement('a');
      a.href = dubbed_video_url;
      a.download = 'dubbed_video.mp4';
      a.click();
    }
  };

  return (
    <div className="w-full max-w-5xl mt-4 space-y-6">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 text-sm text-slate-400 hover:text-slate-200 transition-colors cursor-pointer group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
          <span>Dub another video</span>
        </button>
        <div className="flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Dubbing complete</span>
        </div>
      </div>

      {/* Video Player */}
      <div className="glass-panel rounded-3xl overflow-hidden shadow-2xl">
        <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <PlayCircle className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-semibold text-slate-200">Dubbed Video</h2>
          </div>
          <button
            onClick={handleDownload}
            disabled={!dubbed_video_url}
            className="flex items-center space-x-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-xl transition-colors cursor-pointer disabled:opacity-40 shadow-sm shadow-indigo-500/20"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download MP4</span>
          </button>
        </div>

        <div className="bg-slate-950 aspect-video relative">
          {dubbed_video_url && !videoError ? (
            <video
              ref={videoRef}
              src={dubbed_video_url}
              controls
              className="w-full h-full object-contain"
              onError={() => setVideoError(true)}
            >
              Your browser does not support HTML5 video.
            </video>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center space-y-3 text-slate-500">
              {videoError ? (
                <>
                  <span className="text-3xl">⚠️</span>
                  <p className="text-sm">Video unavailable — try downloading directly.</p>
                  <a
                    href={dubbed_video_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-400 underline text-xs hover:text-indigo-300"
                  >
                    Open in browser
                  </a>
                </>
              ) : (
                <>
                  <span className="text-3xl">🎬</span>
                  <p className="text-sm">No video URL available</p>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Transcripts side by side */}
      <div>
        <div className="flex items-center space-x-2 mb-3 px-1">
          <FileText className="w-4 h-4 text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-300">Transcripts</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <TranscriptCard
            title="Original Transcript"
            icon="📝"
            segments={original_transcript}
            colorClass="bg-slate-800/30"
          />
          <TranscriptCard
            title="Translated Transcript"
            icon="🌐"
            segments={translated_transcript}
            colorClass="bg-indigo-900/20"
          />
        </div>
      </div>

      {/* Info pills */}
      <div className="flex flex-wrap gap-3 pb-2">
        {[
          { label: 'Segments', value: original_transcript.length },
          { label: 'Dubbed Language', value: translated_transcript.length > 0 ? 'Detected' : '—' },
          { label: 'Video URL', value: dubbed_video_url ? 'Ready' : 'Unavailable' }
        ].map(item => (
          <div key={item.label} className="glass-panel px-4 py-2 rounded-xl text-xs text-slate-400 space-x-1">
            <span className="font-medium text-slate-300">{item.label}:</span>
            <span>{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Results;
