import { generateAudio, VOICE_IDS } from '../src/lib/tts';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';

// Load environment variables
dotenv.config({ path: '.env.local' });

async function testTTS() {
    console.log("Testing OpenAI TTS...");
    
    if (!process.env.OPENAI_API_KEY) {
        console.error("❌ OPENAI_API_KEY is missing in .env.local");
        return;
    }
    console.log(`✅ Found API Key: ${process.env.OPENAI_API_KEY.substring(0, 5)}...`);

    const text = "Hello, this is a test of the OpenAI text to speech system.";
    const voiceId = VOICE_IDS.sarah; // "nova"

    console.log(`Generating audio for: "${text}" with voice: ${voiceId}`);

    try {
        const audioBuffer = await generateAudio(text, voiceId);
        
        if (audioBuffer) {
            const outputPath = path.join(process.cwd(), 'test_audio.mp3');
            fs.writeFileSync(outputPath, Buffer.from(audioBuffer));
            console.log(`✅ Audio generated successfully! Saved to ${outputPath}`);
            console.log(`Size: ${audioBuffer.byteLength} bytes`);
        } else {
            console.error("❌ Failed to generate audio (returned null).");
        }
    } catch (error) {
        console.error("❌ Error during test:", error);
    }
}

testTTS();
