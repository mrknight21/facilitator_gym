import React from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface ParticipantTileProps {
    name: string;
    imageUrl: string;
    isSpeaking: boolean;
    subtitle?: string;
    mood?: 'neutral' | 'happy' | 'frustrated' | 'confused';
    className?: string;
}

export const ParticipantTile: React.FC<ParticipantTileProps> = ({
    name,
    imageUrl,
    isSpeaking,
    subtitle,
    mood = 'neutral',
    className,
}) => {
    // Debug
    // if (isSpeaking) console.log(`[FAC_GYM] Tile ${name} is speaking`);

    return (
        <div className={cn("relative w-full aspect-video bg-gray-800 rounded-lg overflow-hidden shadow-lg transition-all duration-300",
            isSpeaking
                ? "ring-4 ring-green-500 shadow-[0_0_20px_rgba(34,197,94,0.6)] scale-[1.02] z-10"
                : "border-2 border-transparent hover:border-gray-600",
            className
        )}>
            {/* Avatar Image */}
            <div className="absolute inset-0">
                <Image
                    src={imageUrl}
                    alt={name}
                    fill
                    sizes="(max-width: 768px) 100vw, 50vw"
                    className="object-cover opacity-90 hover:opacity-100 transition-opacity"
                />
            </div>

            {/* Speaking Indicator Overlay */}
            {isSpeaking && (
                <motion.div
                    className="absolute inset-0 border-4 border-green-500 rounded-lg pointer-events-none"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                />
            )}

            {/* Subtitle Overlay */}
            {isSpeaking && subtitle && (
                <div className="absolute bottom-12 left-0 right-0 px-4 text-center">
                    <motion.span
                        className="inline-block bg-black/70 text-white text-sm px-3 py-1 rounded-lg backdrop-blur-md"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        {subtitle}
                    </motion.span>
                </div>
            )}

            {/* Name Tag */}
            <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur-sm px-3 py-1 rounded text-white text-sm font-medium flex items-center gap-2">
                <span>{name}</span>
                {isSpeaking && (
                    <motion.div
                        className="w-2 h-2 bg-green-500 rounded-full"
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 0.5, repeat: Infinity }}
                    />
                )}
            </div>

            {/* Mood Indicator (Optional) */}
            {mood !== 'neutral' && (
                <div className="absolute top-2 right-2 text-2xl">
                    {mood === 'happy' && '😊'}
                    {mood === 'frustrated' && '😠'}
                    {mood === 'confused' && '🤔'}
                </div>
            )}
        </div>
    );
};
