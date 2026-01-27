import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Play, X } from 'lucide-react';

interface RewindPanelProps {
    sessionId: string;
    branchId: string;
    onRewind: (targetUtteranceId: string) => void;
    onCancel: () => void;
}

interface Utterance {
    utterance_id: string;
    speaker_id: string;
    text: string;
    display_id: string;
    kind: string;
}

export const RewindPanel: React.FC<RewindPanelProps> = ({
    sessionId,
    branchId,
    onRewind,
    onCancel
}) => {
    const [utterances, setUtterances] = useState<Utterance[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        api.getTranscript(sessionId, branchId)
            .then(data => {
                // Filter out non-speech if needed, or keep all
                setUtterances(data.utterances);
            })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, [sessionId, branchId]);

    return (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm z-50 flex flex-col items-center justify-center p-8">
            <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-3xl h-[80vh] flex flex-col shadow-2xl">
                {/* Header */}
                <div className="p-6 border-b border-gray-800 flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-white">Time Stop</h2>
                        <p className="text-gray-400">Select a point to rewind to</p>
                    </div>
                    <button 
                        onClick={onCancel}
                        className="p-2 hover:bg-gray-800 rounded-full transition-colors"
                    >
                        <X size={24} className="text-gray-400 hover:text-white" />
                    </button>
                </div>

                {/* List */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                    {loading ? (
                        <div className="text-center text-gray-500 py-12">Loading transcript...</div>
                    ) : (
                        utterances.map((u) => {
                            const isFacilitatorTurn = u.kind === 'user_intervention' || u.speaker_id === 'user';
                            return (
                            <div 
                                key={u.utterance_id}
                                className={`group flex items-start gap-4 p-4 rounded-lg transition-colors border border-transparent ${
                                    isFacilitatorTurn 
                                        ? 'opacity-50 cursor-not-allowed' 
                                        : 'hover:bg-gray-800/50 hover:border-gray-700'
                                }`}
                            >
                                <div className="w-16 text-xs text-gray-500 font-mono mt-1">
                                    {u.display_id}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={`text-sm font-bold uppercase ${
                                            u.speaker_id === 'user' ? 'text-blue-400' : 'text-green-400'
                                        }`}>
                                            {u.speaker_id}
                                        </span>
                                        {isFacilitatorTurn && (
                                            <span className="text-xs text-gray-500">(Cannot rewind to facilitator turn)</span>
                                        )}
                                    </div>
                                    <p className="text-gray-300">{u.text}</p>
                                </div>
                                {!isFacilitatorTurn && (
                                <button
                                    onClick={() => onRewind(u.utterance_id)}
                                    className="opacity-0 group-hover:opacity-100 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-all transform translate-x-4 group-hover:translate-x-0"
                                >
                                    <Play size={16} />
                                    Rewind Here
                                </button>
                                )}
                            </div>
                        )})
                    )}
                </div>
            </div>
        </div>
    );
};
