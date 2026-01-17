import fetch from 'node-fetch';

async function testPlayback() {
    console.log("Testing Playback Mode...");
    try {
        const response = await fetch('http://localhost:3000/api/simulation/turn', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scenario: "Test",
                history: [],
                currentSpeakerId: null,
                mode: 'playback',
                turnIndex: 0
            })
        });

        if (!response.ok) {
            console.error("Playback request failed:", response.status, await response.text());
            return;
        }

        const data = await response.json();
        console.log("Playback Response:", {
            speakerName: data.speakerName,
            text: data.text,
            isPlayback: data.isPlayback,
            hasAudio: !!data.audio
        });

        if (data.speakerName === 'Sarah' && data.isPlayback) {
            console.log("✅ Playback Mode Verified");
        } else {
            console.error("❌ Playback Mode Verification Failed");
        }

    } catch (error) {
        console.error("Error testing playback:", error);
    }
}

testPlayback();
