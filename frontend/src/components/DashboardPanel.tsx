import React from 'react';
import { motion } from 'framer-motion';

interface DashboardPanelProps {
    tensionLevel: number; // 0 to 100
    speakingTime: { [name: string]: number }; // name -> percentage
    cues: string[];
}

export const DashboardPanel: React.FC<DashboardPanelProps> = ({
    tensionLevel,
    speakingTime,
    cues,
}) => {
    return (
        <div className="bg-gray-900 p-6 rounded-xl shadow-xl border border-gray-800 h-full flex flex-col gap-6">
            <h2 className="text-xl font-bold text-white mb-2">Facilitator Dashboard</h2>

            {/* Tension Meter */}
            <div>
                <h3 className="text-sm text-gray-400 mb-2 uppercase tracking-wider">Tension Level</h3>
                <div className="relative h-4 bg-gray-700 rounded-full overflow-hidden">
                    <motion.div
                        className="absolute top-0 left-0 h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500"
                        initial={{ width: 0 }}
                        animate={{ width: `${tensionLevel}%` }}
                        transition={{ duration: 0.5 }}
                    />
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Calm</span>
                    <span>Heated</span>
                </div>
            </div>

            {/* Speaking Time */}
            <div className="flex-1">
                <h3 className="text-sm text-gray-400 mb-2 uppercase tracking-wider">Airtime Balance</h3>
                <div className="space-y-3">
                    {Object.entries(speakingTime).map(([name, percentage]) => (
                        <div key={name}>
                            <div className="flex justify-between text-sm text-gray-300 mb-1">
                                <span>{name}</span>
                                <span>{percentage}%</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                                <motion.div
                                    className="h-full bg-blue-500"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${percentage}%` }}
                                    transition={{ duration: 0.5 }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Key Cues */}
            <div className="bg-gray-800/50 p-4 rounded-lg">
                <h3 className="text-sm text-gray-400 mb-2 uppercase tracking-wider">Recent Cues</h3>
                <ul className="space-y-2">
                    {cues.map((cue, index) => (
                        <motion.li
                            key={index}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            className="text-sm text-yellow-400 flex items-start gap-2"
                        >
                            <span>•</span>
                            <span>{cue}</span>
                        </motion.li>
                    ))}
                </ul>
            </div>
        </div>
    );
};
