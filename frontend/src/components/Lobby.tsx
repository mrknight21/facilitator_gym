import React, { useState, useEffect } from 'react';
import { Mic, CheckCircle, ArrowRight, AlertCircle } from 'lucide-react';

interface LobbyProps {
    onGrantMic: () => Promise<void>;
    micPermissionGranted: boolean;
    serverReady: boolean;
    onStartSession: () => void;
    isBusy?: boolean;
    stream?: MediaStream | null;
    intro?: string;
    participants?: string[];
}

export const Lobby: React.FC<LobbyProps> = ({
    onGrantMic,
    micPermissionGranted,
    serverReady,
    onStartSession,
    isBusy = false,
    stream,
    intro,
    participants = []
}) => {
    const [audioLevel, setAudioLevel] = useState(0);

    // RMS Metering
    useEffect(() => {
        if (!stream || !micPermissionGranted) return;

        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        const analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        let animationFrameId: number;

        const updateLevel = () => {
            analyser.getByteFrequencyData(dataArray);

            // Calculate RMS (roughly)
            let sum = 0;
            for (let i = 0; i < bufferLength; i++) {
                sum += dataArray[i];
            }
            const average = sum / bufferLength;
            // Normalize 0-255 to 0-100, boost low levels
            const normalized = Math.min(100, (average / 50) * 100);

            setAudioLevel(normalized);
            animationFrameId = requestAnimationFrame(updateLevel);
        };

        updateLevel();

        return () => {
            cancelAnimationFrame(animationFrameId);
            audioContext.close();
        };
    }, [stream, micPermissionGranted]);

    return (
        <div className="flex flex-col items-center justify-center min-h-[50vh] p-8 text-white max-w-2xl mx-auto">
            <h1 className="text-4xl font-bold mb-8 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-green-400">
                Session Setup
            </h1>

            <div className="w-full bg-gray-900/50 backdrop-blur-sm border border-gray-800 rounded-2xl p-8 space-y-8">

                {/* Session Info */}
                {(intro || participants.length > 0) && (
                    <div className="bg-gray-800/40 rounded-xl p-6 border border-gray-700/50">
                        {intro && (
                            <div className="mb-4">
                                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">Scenario</h3>
                                <p className="text-lg text-gray-200 leading-relaxed">{intro}</p>
                            </div>
                        )}

                        {participants.length > 0 && (
                            <div>
                                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Participants</h3>
                                <div className="flex flex-wrap gap-2">
                                    {participants.map((p) => (
                                        <span key={p} className="px-3 py-1 bg-gray-700 rounded-full text-sm font-medium text-blue-200 border border-gray-600">
                                            {p}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Step 1: Mic Permission */}
                <div className={`flex items-center justify-between p-4 rounded-xl border ${micPermissionGranted ? 'border-green-500/30 bg-green-500/10' : 'border-gray-700 bg-gray-800/50'} transition-all duration-300`}>
                    <div className="flex items-center gap-4">
                        <div className={`p-3 rounded-full ${micPermissionGranted ? 'bg-green-500' : 'bg-gray-700'}`}>
                            {micPermissionGranted ? <CheckCircle size={24} /> : <Mic size={24} />}
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold">Microphone Access</h3>
                            <p className="text-sm text-gray-400">Required for interaction</p>
                        </div>
                    </div>

                    {!micPermissionGranted && (
                        <button
                            onClick={onGrantMic}
                            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                        >
                            Grant Access
                        </button>
                    )}
                </div>

                {/* Step 2: Mic Check (Level Meter) */}
                {micPermissionGranted && (
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm text-gray-400">
                            <span>Microphone Input</span>
                            <span>{serverReady ? "Server Connected ✅" : "Connecting to server..."}</span>
                        </div>
                        <div className="h-4 bg-gray-800 rounded-full overflow-hidden border border-gray-700">
                            <div
                                className="h-full bg-gradient-to-r from-green-500 to-yellow-400 transition-all duration-75 ease-out"
                                style={{ width: `${audioLevel}%` }}
                            />
                        </div>
                        <p className="text-xs text-gray-500 text-center pt-2">
                            Say something to check input levels
                        </p>
                    </div>
                )}

                {/* Step 3: Start Session */}
                <div className="pt-4 flex justify-center">
                    <button
                        onClick={onStartSession}
                        disabled={!micPermissionGranted || !serverReady || isBusy}
                        className={`
                            flex items-center gap-3 px-8 py-4 rounded-full text-xl font-bold transition-all duration-300
                            ${micPermissionGranted && serverReady && !isBusy
                                ? 'bg-green-500 hover:bg-green-600 hover:scale-105 shadow-[0_0_20px_rgba(34,197,94,0.4)] text-white'
                                : 'bg-gray-800 text-gray-500 cursor-not-allowed'}
                        `}
                    >
                        {isBusy ? (
                            "Starting..."
                        ) : (
                            <>
                                Enter Session <ArrowRight size={24} />
                            </>
                        )}
                    </button>
                </div>
            </div>

            <div className="mt-8 text-sm text-gray-500 flex items-center gap-2">
                <AlertCircle size={14} />
                <span>Audio is processed securely and not stored permanently.</span>
            </div>
        </div>
    );
};
