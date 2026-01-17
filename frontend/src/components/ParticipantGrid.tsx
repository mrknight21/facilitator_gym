import React from 'react';
import { ParticipantTile } from './ParticipantTile';

interface Participant {
    id: string;
    name: string;
    imageUrl: string;
    isSpeaking: boolean;
    subtitle?: string;
    mood?: 'neutral' | 'happy' | 'frustrated' | 'confused';
}

interface ParticipantGridProps {
    participants: Participant[];
}

export const ParticipantGrid: React.FC<ParticipantGridProps> = ({ participants }) => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 w-full h-full max-w-6xl mx-auto content-center">
            {participants.map((p) => (
                <ParticipantTile
                    key={p.id}
                    name={p.name}
                    imageUrl={p.imageUrl}
                    isSpeaking={p.isSpeaking}
                    subtitle={p.subtitle}
                    mood={p.mood}
                />
            ))}
        </div>
    );
};
