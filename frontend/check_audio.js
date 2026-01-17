const mongoose = require('mongoose');
const fs = require('fs');
const path = require('path');

const SessionLogSchema = new mongoose.Schema({
    sessionId: String,
    transcript: [{
        speakerName: String,
        text: String,
        audio: String
    }]
});

const SessionLog = mongoose.models.SessionLog || mongoose.model('SessionLog', SessionLogSchema);

async function checkAudio() {
    // Manually parse .env.local
    const envPath = path.resolve(__dirname, '.env.local');
    const envContent = fs.readFileSync(envPath, 'utf8');
    const mongoMatch = envContent.match(/MONGODB_URI=(.*)/);
    const mongoUri = mongoMatch ? mongoMatch[1].trim() : null;

    if (!mongoUri) {
        console.error("MONGODB_URI not found in .env.local");
        return;
    }

    try {
        await mongoose.connect(mongoUri);
        console.log("Connected to DB");

        const log = await SessionLog.findOne({ sessionId: 'demo-session' });
        if (!log) {
            console.log("No session log found");
        } else {
            // Check the last few turns
            const recentTurns = log.transcript.slice(-3);
            console.log(`Checking last ${recentTurns.length} turns:`);
            recentTurns.forEach((turn, i) => {
                console.log(`Turn ${i}: Speaker=${turn.speakerName}, HasAudio=${!!turn.audio}, AudioLen=${turn.audio ? turn.audio.length : 0}`);
            });
        }

    } catch (error) {
        console.error("Error:", error);
    } finally {
        await mongoose.disconnect();
    }
}

checkAudio();
