import fs from 'fs';
import path from 'path';
import { MOCK_TRANSCRIPT } from '../src/data/mockTranscript';
import { generateAudio, VOICE_IDS } from '../src/lib/tts';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });

async function main() {
    console.log("Starting audio generation for transcript...");
    
    const outputDir = path.join(process.cwd(), 'public', 'audio', 'transcript');
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    for (let i = 0; i < MOCK_TRANSCRIPT.length; i++) {
        const turn = MOCK_TRANSCRIPT[i];
        const fileName = `turn_${i}.mp3`;
        const filePath = path.join(outputDir, fileName);

        if (fs.existsSync(filePath)) {
            console.log(`Skipping ${fileName} (already exists)`);
            continue;
        }

        console.log(`Generating audio for Turn ${i} (${turn.speakerName})...`);
        
        const voiceId = VOICE_IDS[turn.speakerName.toLowerCase() as keyof typeof VOICE_IDS] || VOICE_IDS.sarah;
        
        try {
            const audioBuffer = await generateAudio(turn.text, voiceId);
            if (audioBuffer) {
                fs.writeFileSync(filePath, Buffer.from(audioBuffer));
                console.log(`Saved ${fileName}`);
            } else {
                console.error(`Failed to generate audio for Turn ${i}`);
            }
        } catch (error) {
            console.error(`Error generating Turn ${i}:`, error);
        }
    }

    console.log("Audio generation complete.");
}

main().catch(console.error);
