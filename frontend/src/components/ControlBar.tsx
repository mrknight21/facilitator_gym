import React from 'react';
import { Play, Pause, Mic, MicOff } from 'lucide-react';

interface ControlBarProps {
    isPlaying: boolean;
    onTogglePlay: () => void;
    timer: string;
    isMicOn: boolean;
    onToggleMic: () => void;
    onEnableAudio: () => void;
    isAudioEnabled: boolean;
}

export const ControlBar: React.FC<ControlBarProps> = ({
    isPlaying,
    onTogglePlay, // Using this as Start/Stop
    timer,
    isMicOn,
    onPttDown,
    onPttUp,
    onEnableAudio,
    isAudioEnabled,
}) => {
    if (!isPlaying) {
        // ... (Start Screen) ...
        return (
            <div className="bg-gray-900 border-t border-gray-800 p-6 flex items-center justify-center">
                <button
                    onClick={onTogglePlay}
                    className="flex items-center gap-3 bg-green-500 hover:bg-green-600 text-white px-8 py-4 rounded-full text-xl font-bold transition-transform hover:scale-105"
                >
                    <Play size={28} fill="currentColor" />
                    Start Session
                </button>
            </div>
        );
    }

    // Active Session Screen
    return (
        <div className="bg-gray-900 border-t border-gray-800 p-4 grid grid-cols-3 items-center">
            {/* Left: Timer & Formatting */}
            <div className="flex items-center gap-4 pl-4">
                <div className="text-xl font-mono text-gray-400">
                    {timer}
                </div>
            </div>

            {/* Center: PTT Button OR Enable Audio */}
            <div className="flex justify-center">
                {!isAudioEnabled ? (
                    <button
                        onClick={onEnableAudio}
                        className="flex items-center gap-2 bg-yellow-500 text-black px-6 py-3 rounded-full font-bold shadow-lg hover:bg-yellow-400 hover:scale-105 transition-all"
                    >
                        <MicOff size={24} />
                        Enable Audio
                    </button>
                ) : (
                    <button
                        onMouseDown={onPttDown}
                        onMouseUp={onPttUp}
                        onMouseLeave={onPttUp}
                        onTouchStart={onPttDown}
                        onTouchEnd={onPttUp}
                        className={`p-6 rounded-full transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg ${isMicOn
                            ? 'bg-red-500 text-white ring-4 ring-offset-2 ring-offset-gray-900 ring-red-500'
                            : 'bg-blue-600 text-white hover:bg-blue-500'
                            }`}
                        title="Hold Spacebar or Click to Speak"
                    >
                        {isMicOn ? <Mic size={32} /> : <MicOff size={32} />}
                    </button>
                )}
            </div>

            {/* Right: End Session (Small) */}
            <div className="flex justify-end pr-4">
                <button
                    onClick={onTogglePlay}
                    className="text-red-500 hover:text-red-400 font-medium text-sm flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-white/5 transition-colors"
                >
                    <Pause size={16} />
                    End Session
                </button>
            </div>
        </div>
    );
};
