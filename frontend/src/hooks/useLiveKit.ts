import { useEffect, useState, useRef } from 'react';
import { Room, RoomEvent, RemoteParticipant, RemoteTrack, Track } from 'livekit-client';

export interface ParticipantState {
    identity: string;
    isSpeaking: boolean;
    audioTrack?: RemoteTrack;
}

export function useLiveKit(url: string, token: string | null) {
    const [room, setRoom] = useState<Room | null>(null);
    const [participants, setParticipants] = useState<ParticipantState[]>([]);
    const [error, setError] = useState<Error | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        if (!url || !token) return;

        const connect = async () => {
            try {
                console.log("[FAC_GYM] Connecting to LiveKit URL:", url);
                console.log("[FAC_GYM] With Token:", token?.slice(0, 10) + "...");
                const r = new Room();
                
                r.on(RoomEvent.Connected, () => setIsConnected(true));
                r.on(RoomEvent.Disconnected, () => setIsConnected(false));
                
                r.on(RoomEvent.ParticipantConnected, (p) => {
                    setParticipants(prev => [...prev, { identity: p.identity, isSpeaking: p.isSpeaking }]);
                });
                
                r.on(RoomEvent.ParticipantDisconnected, (p) => {
                    setParticipants(prev => prev.filter(x => x.identity !== p.identity));
                });

                r.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
                    setParticipants(prev => prev.map(p => ({
                        ...p,
                        isSpeaking: speakers.some(s => s.identity === p.identity)
                    })));
                });

                r.on(RoomEvent.TrackSubscribed, (track, pub, participant) => {
                    if (track.kind === Track.Kind.Audio) {
                        const element = track.attach();
                        document.body.appendChild(element);
                    }
                });

                await r.connect(url, token);
                setRoom(r);
                
                // Init participants
                const initialParticipants = Array.from(r.remoteParticipants.values()).map(p => ({
                    identity: p.identity,
                    isSpeaking: p.isSpeaking
                }));
                setParticipants(initialParticipants);

            } catch (e) {
                setError(e as Error);
            }
        };

        connect();

        return () => {
            room?.disconnect();
        };
    }, [url, token]);

    return { room, participants, isConnected, error };
}
