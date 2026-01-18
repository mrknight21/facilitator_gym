'use client';

import React, { useState, useEffect } from 'react';
import { ParticipantGrid } from '@/components/ParticipantGrid';
import { DashboardPanel } from '@/components/DashboardPanel';
import { ControlBar } from '@/components/ControlBar';
import { ParticipantTile } from '@/components/ParticipantTile';
import { api } from '@/lib/api';
import { useLiveKit } from '@/hooks/useLiveKit';
import { RoomEvent } from 'livekit-client';

// Mock avatars for now
const AVATARS: Record<string, string> = {
    "alice": "/avatars/sarah.png",
    "bob": "/avatars/mike.png",
    "charlie": "/avatars/jessica.png"
};

export default function Home() {
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isStarting, setIsStarting] = useState(false);

    // LiveKit Hook
    const { room, participants, isConnected } = useLiveKit(
        process.env.NEXT_PUBLIC_LIVEKIT_URL || "ws://localhost:7880",
        token
    );

    const handleStart = async (caseStudyId: string) => {
        setIsStarting(true);
        try {
            // 1. Start Session
            const session = await api.startSession(caseStudyId, "user");
            setSessionId(session.session_id);

            // 2. Get Token
            const tokenData = await api.getToken(session.session_id, "user");
            setToken(tokenData.token);

        } catch (e) {
            console.error(e);
            alert("Failed to start session");
        } finally {
            setIsStarting(false);
        }
    };



    const [caseStudies, setCaseStudies] = useState<any[]>([]);
    const [selectedCaseStudy, setSelectedCaseStudy] = useState<string>("");

    useEffect(() => {
        api.getCaseStudies().then(data => {
            setCaseStudies(data);
            if (data.length > 0) setSelectedCaseStudy(data[0].case_study_id);
        }).catch(console.error);
    }, []);

    // Silence Handling
    const [isSilence, setIsSilence] = useState(false);

    // Mic & Intervention
    // Mic & Intervention (PTT)
    const [isMicOn, setIsMicOn] = useState(false);
    const [isAudioEnabled, setIsAudioEnabled] = useState(false);
    const isPttPressed = React.useRef(false);

    // Manual speaking state from backend messages
    const [speakingState, setSpeakingState] = useState<Record<string, boolean>>({});

    useEffect(() => {
        if (!room) return;
        const onData = (payload: Uint8Array) => {
            try {
                const str = new TextDecoder().decode(payload);
                const msg = JSON.parse(str);
                console.log(`[FAC_GYM] onData: type=${msg.type}, payload=`, msg.payload);

                // Existing silence handling
                if (msg.type === 'silence_start') {
                    setIsSilence(true);
                    setTimeout(() => setIsSilence(false), 3000);
                } else if (msg.type === 'speak_cmd') {
                    // Start speaking visual
                    setIsSilence(false);
                    const spk = msg.payload?.speaker_id || msg.speaker_id; // Support both just in case
                    console.log(`[FAC_GYM] SET SPEAKING: ${spk}`);
                    if (spk) setSpeakingState(prev => ({ ...prev, [spk]: true }));
                } else if (msg.type === 'playback_done') {
                    // Stop speaking visual
                    const spk = msg.payload?.speaker_id || msg.speaker_id;
                    console.log(`[FAC_GYM] CLEAR SPEAKING: ${spk}`);
                    if (spk) setSpeakingState(prev => ({ ...prev, [spk]: false }));
                }
            } catch (e) { console.error(e); }
        };
        room.on(RoomEvent.DataReceived, onData);
        return () => { room.off(RoomEvent.DataReceived, onData); };
    }, [room]);

    // Map LiveKit participants to UI model
    const uiParticipants = participants
        .filter(p => p.identity !== "conductor-bot")
        .map(p => ({
            id: p.identity,
            name: p.identity, // Use identity as name for now
            imageUrl: AVATARS[p.identity] || "/avatars/david.png",
            // Combine audio level detection AND manual state
            isSpeaking: p.isSpeaking || !!speakingState[p.identity],
            mood: 'neutral' as const
        }));

    // Audio Persistence: Enable mic on join but keep muted
    useEffect(() => {
        if (!room) return;
        const initMic = async () => {
            console.log("[FAC_GYM] Initializing Microphone...");
            try {
                // Enable mic (publishes track)
                await room.localParticipant.setMicrophoneEnabled(true);
                // Immediately mute so we don't broadcast yet
                room.localParticipant.audioTrackPublications.forEach(p => {
                    console.log(`[FAC_GYM] Muted initial track: ${p.trackSid}`);
                    p.track?.mute();
                });
                console.log("[FAC_GYM] Microphone initialized and muted.");
            } catch (e) {
                console.error("[FAC_GYM] Init Mic Failed:", e);
            }
        };
        initMic();
    }, [room]);

    const startPtt = async () => {
        if (!room || !sessionId || isPttPressed.current) return;
        isPttPressed.current = true;
        setIsMicOn(true);

        try {
            // 1. Unmute Mic (Instant)
            const trackPub = Array.from(room.localParticipant.audioTrackPublications.values())
                .find(p => p.kind === 'audio');

            if (trackPub?.track) {
                trackPub.track.unmute();
            } else {
                // Fallback if track missing
                await room.localParticipant.setMicrophoneEnabled(true);
            }

            // 2. Send Start Signal
            const encode = (msg: any) => new TextEncoder().encode(JSON.stringify(msg));
            const msg = { type: "fac_start", session_id: sessionId };
            await room.localParticipant.publishData(encode(msg), { reliable: true });
        } catch (e) {
            console.error("Failed to start PTT:", e);
        }
    };

    const endPtt = async () => {
        if (!room || !sessionId || !isPttPressed.current) return;
        isPttPressed.current = false;
        setIsMicOn(false);

        try {
            // 1. Mute Mic
            const trackPub = Array.from(room.localParticipant.audioTrackPublications.values())
                .find(p => p.kind === 'audio');

            if (trackPub?.track) {
                trackPub.track.mute();
            }

            // 2. Send End Signal
            const encode = (msg: any) => new TextEncoder().encode(JSON.stringify(msg));
            const msg = { type: "fac_end", session_id: sessionId };
            await room.localParticipant.publishData(encode(msg), { reliable: true });
        } catch (e) {
            console.error("Failed to end PTT:", e);
        }
    };

    // Keyboard PTT (Spacebar)
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.code === 'Space' && !e.repeat) {
                e.preventDefault(); // Prevent scrolling
                startPtt();
            }
        };
        const handleKeyUp = (e: KeyboardEvent) => {
            if (e.code === 'Space') {
                e.preventDefault();
                endPtt();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, [startPtt, endPtt]);

    const handleEndSession = async () => {
        if (!sessionId) return;

        // 1. Notify Conductor
        if (room && room.state === 'connected') {
            const encode = (msg: any) => new TextEncoder().encode(JSON.stringify(msg));
            const msg = { type: "finish", session_id: sessionId };
            try {
                await room.localParticipant.publishData(encode(msg), { reliable: true });
            } catch (e) { console.error("Failed to send finish:", e); }
        }

        // 2. Call API to stop
        try {
            await api.stopSession(sessionId);
        } catch (e) {
            console.error("Failed to stop session:", e);
        }
        setSessionId(null);
        setToken(null);
        setIsMicOn(false);
    };

    // Handle window close
    useEffect(() => {
        const handleUnload = () => {
            if (sessionId) {
                // We use sendBeacon or fetch with keepalive (handled in api.ts)
                api.stopSession(sessionId).catch(console.error);
            }
        };
        window.addEventListener('beforeunload', handleUnload);
        return () => window.removeEventListener('beforeunload', handleUnload);
    }, [sessionId]);

    if (!token) {
        const selectedCS = caseStudies.find(cs => cs.case_study_id === selectedCaseStudy);

        return (
            <div className="flex h-screen bg-black text-white p-8 gap-8">
                {/* Left: List */}
                <div className="w-1/3 flex flex-col gap-6 border-r border-gray-800 pr-8">
                    <h1 className="text-3xl font-bold">Facilitator Gym</h1>
                    <p className="text-gray-400">Select a scenario to practice your facilitation skills.</p>

                    <div className="flex flex-col gap-3 overflow-y-auto">
                        {caseStudies.map(cs => (
                            <button
                                key={cs.case_study_id}
                                onClick={() => setSelectedCaseStudy(cs.case_study_id)}
                                className={`text-left p-4 rounded-lg border transition-all ${selectedCaseStudy === cs.case_study_id
                                    ? "bg-blue-900/30 border-blue-500"
                                    : "bg-gray-900 border-gray-800 hover:border-gray-600"
                                    }`}
                            >
                                <h3 className="font-bold text-lg">{cs.title}</h3>
                                <p className="text-sm text-gray-400 mt-1 line-clamp-2">{cs.description}</p>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Right: Details */}
                <div className="w-2/3 flex flex-col justify-center items-start pl-8">
                    {selectedCS ? (
                        <div className="max-w-2xl w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div>
                                <h2 className="text-4xl font-bold mb-4">{selectedCS.title}</h2>
                                <p className="text-xl text-gray-300 leading-relaxed">{selectedCS.description}</p>
                            </div>

                            <div className="bg-gray-900/50 p-6 rounded-xl border border-gray-800">
                                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Participants</h3>
                                <div className="flex flex-wrap gap-3">
                                    {selectedCS.participants?.map((p: string, i: number) => (
                                        <span key={i} className="px-3 py-1 bg-gray-800 rounded-full text-sm border border-gray-700">
                                            {p}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            <button
                                onClick={() => handleStart(selectedCS.case_study_id)}
                                disabled={isStarting}
                                className="w-full py-4 bg-blue-600 rounded-xl hover:bg-blue-500 disabled:opacity-50 font-bold text-lg transition-all shadow-lg shadow-blue-900/20"
                            >
                                {isStarting ? "Initializing Simulation..." : "Start Session"}
                            </button>
                        </div>
                    ) : (
                        <div className="text-gray-500 text-xl">Select a case study to begin</div>
                    )}
                </div>
            </div>
        );
    }


    return (
        <main className="flex h-screen flex-col bg-black overflow-hidden relative">
            {/* ... Header ... */}
            <header className="p-6 border-b border-gray-800 flex justify-between items-center bg-gray-900/50 backdrop-blur z-10">
                <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full shadow-[0_0_10px] ${isConnected ? 'bg-green-500 shadow-green-500/50' : 'bg-red-500 shadow-red-500/50'}`} />
                    <h1 className="text-xl font-medium tracking-wide text-gray-200">FACILITATOR GYM</h1>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-xs text-gray-400">
                        SESSION: {sessionId}
                    </div>

                </div>
            </header>

            {/* Main Content Area */}
            <div className="flex-1 flex overflow-hidden">
                {/* Left: Participant Grid */}
                <div className="flex-1 relative flex flex-col items-center justify-center p-8">
                    <div className="grid grid-cols-2 gap-12 w-full max-w-4xl">
                        {uiParticipants.map((p) => (
                            <ParticipantTile key={p.id} {...p} />
                        ))}
                    </div>

                    {/* Silence Indicator */}
                    {isSilence && (
                        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none fade-in zoom-in duration-300">
                            <div className="bg-blue-500/20 backdrop-blur-md border border-blue-400/50 rounded-2xl px-8 py-4 shadow-[0_0_30px_rgba(59,130,246,0.5)]">
                                <h2 className="text-2xl font-bold text-blue-100 tracking-widest uppercase animate-pulse">Floor Open</h2>
                            </div>
                        </div>
                    )}

                </div>

                {/* Right: Dashboard Panel */}
                <div className="w-80 border-l border-gray-800 bg-gray-900/50 backdrop-blur">
                    <DashboardPanel
                        tensionLevel={30}
                        speakingTime={{}}
                        cues={["Session Active"]}
                    />
                </div>
            </div>

            {/* Bottom: Control Bar */}
            <ControlBar
                isPlaying={isConnected}
                onTogglePlay={handleEndSession}
                timer="00:00"
                isMicOn={isMicOn}
                onToggleMic={() => { }} // Disabled click toggle
                onPttDown={startPtt}
                onPttUp={endPtt}
            />
        </main>
    );
}
