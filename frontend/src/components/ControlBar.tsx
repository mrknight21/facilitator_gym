import React from 'react';
import { Play, Pause, Mic, MicOff } from 'lucide-react';

interface ControlBarProps {
    isPlaying: boolean;
    onTogglePlay: () => void;
    timer: string;
    isMicOn: boolean;
    onToggleMic: () => void;
}

export const ControlBar: React.FC<ControlBarProps> = ({
    isPlaying,
    onTogglePlay,
    timer,
    isMicOn,
    onToggleMic,
}) => {
    return (
        <div className="bg-gray-900 border-t border-gray-800 p-4 flex items-center justify-between px-8">
            {/* Timer */}
            <div className="text-2xl font-mono text-white w-32">
                {timer}
            </div>

            {/* Main Controls */}
            <div className="flex items-center gap-6">
                <button
                    onClick={onTogglePlay}
                    className={`p-4 rounded-full transition-all transform hover:scale-105 active:scale-95 ${isPlaying ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'
                        }`}
                >
                    {isPlaying ? <Pause size={32} className="text-white" /> : <Play size={32} className="text-white" />}
                </button>
            </div>

            {/* Mic Control */}
            <div className="w-32 flex justify-end">
                <button
                    onClick={onToggleMic}
                    className={`p-3 rounded-full transition-colors ${isMicOn ? 'bg-gray-700 text-white' : 'bg-red-500/20 text-red-500'
                        }`}
                >
                    {isMicOn ? <Mic size={24} /> : <MicOff size={24} />}
                </button>
            </div>
        </div>
    );
};
