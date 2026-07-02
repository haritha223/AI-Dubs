import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2, CheckCircle2, Circle, AlertCircle, XCircle } from 'lucide-react';

const STEPS = [
  { key: 'downloading', label: 'Downloading video & extracting audio', desc: 'Fetching the YouTube MP4 and extracting its audio stream.' },
  { key: 'transcribing', label: 'Transcribing speech-to-text', desc: 'Running Whisper local speech recognition to extract timestamps.' },
  { key: 'translating', label: 'Translating contextually (NLLB-200)', desc: 'Translating text segments while preserving flow and conversational tone.' },
  { key: 'tts_generation', label: 'Generating speech chunks (TTS)', desc: 'Synthesizing translated text chunks into speech files.' },
  { key: 'synchronizing', label: 'Aligning timeline (FFmpeg)', desc: 'Inserting audio clips and padding silence to sync with original speech.' },
  { key: 'merging', label: 'Merging audio and video (FFmpeg)', desc: 'Replacing the original sound track with the synchronized dubbed audio.' },
  { key: 'uploading', label: 'Saving & finalizing assets', desc: 'Uploading files to storage and generating URLs for playback.' }
];

function Processing({ taskId, youtubeUrl, targetLanguage, onComplete, onCancel }) {
  const [currentStep, setCurrentStep] = useState('queued');
  const [errorMsg, setErrorMsg] = useState('');
  const [dots, setDots] = useState('');

  // Simple dots animation
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => (prev.length >= 3 ? '' : prev + '.'));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!taskId) return;

    let timer;
    const checkStatus = async () => {
      try {
        // Use Vite proxy — /translate proxies to http://localhost:8000
        const response = await axios.get(`/translate/status/${taskId}`);
        const data = response.data;

        if (data.status === 'completed') {
          clearInterval(timer);
          onComplete(data);
        } else if (data.status === 'failed') {
          clearInterval(timer);
          setErrorMsg(data.error_message || 'An unknown error occurred during processing.');
          setCurrentStep('failed');
        } else {
          setCurrentStep(data.progress_step || 'queued');
        }
      } catch (err) {
        console.error('Error fetching task status:', err);
        // We do not abort immediately to allow for transient network dropouts,
        // but we show the error if it persists.
      }
    };

    // Initial check
    checkStatus();

    // Poll every 2 seconds
    timer = setInterval(checkStatus, 2000);

    return () => clearInterval(timer);
  }, [taskId, onComplete]);

  // Determine status of a specific step
  const getStepStatus = (stepKey, idx) => {
    if (currentStep === 'failed') {
      // If failed, the active or subsequent steps are failed
      const activeIdx = STEPS.findIndex(s => s.key === currentStep);
      return 'failed';
    }
    
    const activeIdx = STEPS.findIndex(s => s.key === currentStep);
    
    if (currentStep === 'completed') return 'completed';
    if (activeIdx === -1) return 'pending'; // queued
    
    if (idx < activeIdx) return 'completed';
    if (idx === activeIdx) return 'active';
    return 'pending';
  };

  return (
    <div className="w-full max-w-2xl mt-4 space-y-6">
      <div className="glass-panel rounded-3xl p-6 md:p-8 shadow-2xl relative overflow-hidden">
        <div className="flex justify-between items-start mb-6">
          <div className="space-y-1">
            <h2 className="text-xl md:text-2xl font-bold text-slate-100 flex items-center space-x-2">
              {currentStep !== 'failed' && currentStep !== 'completed' && (
                <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
              )}
              <span>Processing Video</span>
            </h2>
            <p className="text-xs text-slate-500 max-w-sm truncate">
              URL: {youtubeUrl}
            </p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-medium">
            Dubbing to {targetLanguage}
          </span>
        </div>

        {/* Stepper progress pipeline */}
        <div className="space-y-4">
          {STEPS.map((step, idx) => {
            const status = getStepStatus(step.key, idx);
            return (
              <div 
                key={step.key} 
                className={`flex items-start space-x-4 p-3 rounded-2xl transition-all ${
                  status === 'active' 
                    ? 'bg-indigo-500/5 border border-indigo-500/10' 
                    : 'border border-transparent'
                }`}
              >
                {/* Visual Indicators */}
                <div className="mt-0.5 flex-shrink-0">
                  {status === 'completed' && (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  )}
                  {status === 'active' && (
                    <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
                  )}
                  {status === 'pending' && (
                    <Circle className="w-5 h-5 text-slate-700" />
                  )}
                  {status === 'failed' && (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                </div>

                {/* Details */}
                <div className="space-y-0.5">
                  <div className={`text-sm font-semibold ${
                    status === 'active' 
                      ? 'text-indigo-400' 
                      : status === 'completed' 
                        ? 'text-slate-300' 
                        : 'text-slate-600'
                  }`}>
                    {step.label}
                    {status === 'active' && <span className="font-normal text-xs ml-1">{dots}</span>}
                  </div>
                  {status === 'active' && (
                    <p className="text-xs text-slate-400 leading-relaxed">
                      {step.desc}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Queued State */}
        {currentStep === 'queued' && (
          <div className="mt-6 p-4 rounded-2xl bg-indigo-950/20 border border-indigo-900/30 text-indigo-300 text-xs md:text-sm text-center">
            Your task is waiting in the pipeline queue. Downloading will begin shortly.
          </div>
        )}

        {/* Error/Failure State */}
        {currentStep === 'failed' && (
          <div className="mt-6 space-y-4">
            <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs md:text-sm flex items-start space-x-2.5">
              <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500" />
              <div className="space-y-1">
                <span className="font-semibold block">Translation Failed</span>
                <span className="text-xs text-red-300/80 leading-relaxed block">
                  {errorMsg || 'FastAPI backend raised a server pipeline exception.'}
                </span>
              </div>
            </div>
            
            <button
              onClick={onCancel}
              className="w-full bg-slate-900 border border-slate-800 hover:bg-slate-850 hover:border-slate-700 text-slate-300 font-semibold py-3 px-6 rounded-2xl transition-all text-sm cursor-pointer"
            >
              Back to Home
            </button>
          </div>
        )}

        {/* Cancel Button during active processing */}
        {currentStep !== 'failed' && (
          <div className="mt-6 pt-4 border-t border-slate-900 flex justify-end">
            <button
              onClick={onCancel}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors cursor-pointer font-medium"
            >
              Cancel Task
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Processing;
