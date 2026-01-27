import React from 'react';
import { Play, Pause, Mic, MicOff } from 'lucide-react';

interface ControlBarProps {
    timer: string;
    isMicOn: boolean;
    onToggleMic: () => void;
    onPttDown: () => void;
    onPttUp: () => void;
    onEndSession: () => void;
    onTimeStop: () => void;
}

export const ControlBar: React.FC<ControlBarProps> = ({
    timer,
    isMicOn,
    onPttDown,
    onPttUp,
    onEndSession,
    onTimeStop,
}) => {
    // Active Session Screen
    return (
        <div className="bg-gray-900 border-t border-gray-800 p-4 grid grid-cols-3 items-center">
            {/* Left: Timer & Formatting */}
            <div className="flex items-center gap-4 pl-4">
                <div className="text-xl font-mono text-gray-400">
                    {timer}
                </div>
            </div>

            {/* Center: PTT Button */}
            <div className="flex justify-center gap-4">
                 <button
                    onClick={onTimeStop}
                    className="w-12 h-12 rounded-full bg-yellow-600 hover:bg-yellow-500 flex items-center justify-center text-white shadow-lg transition-all"
                    title="Time Stop / Rewind"
                >
                    <Pause size={24} fill="currentColor" />
                </button>

                <button
                    onMouseDown={onPttDown}
                    onMouseUp={onPttUp}
                    onMouseLeave={onPttUp}
                    onTouchStart={onPttDown}
                    onTouchEnd={onPttUp}
                    className={`px-8 py-4 rounded-full transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg flex items-center gap-3 ${isMicOn
                        ? 'bg-red-500 text-white ring-4 ring-offset-2 ring-offset-gray-900 ring-red-500'
                        : 'bg-blue-600 text-white hover:bg-blue-500'
                        }`}
                    title="Hold Spacebar or Click to Speak"
                >
                    {isMicOn ? <Mic size={24} /> : <MicOff size={24} />}
                    <span className="font-semibold text-lg">Hold space bar to speak</span>
                </button>
            </div>

            {/* Right: End Session (Small) */}
            <div className="flex justify-end pr-4">
                <button
                    onClick={onEndSession}
                    className="text-red-500 hover:text-red-400 font-medium text-sm flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-white/5 transition-colors"
                >
                    <Pause size={16} />
                    End Session
                </button>
            </div>
        </div>
    );
};
