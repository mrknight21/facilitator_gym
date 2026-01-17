const { GoogleGenerativeAI } = require("@google/generative-ai");
const fs = require('fs');
const path = require('path');

async function testModel() {
    const envPath = path.resolve(__dirname, '.env.local');
    const envContent = fs.readFileSync(envPath, 'utf8');
    const apiKeyMatch = envContent.match(/GEMINI_API_KEY=(.*)/);
    const apiKey = apiKeyMatch ? apiKeyMatch[1].trim() : null;

    if (!apiKey) {
        console.error("API Key not found in .env.local");
        return;
    }

    const genAI = new GoogleGenerativeAI(apiKey);
    // Test the suspicious model name
    console.log("Testing gemini-2.5-flash...");
    try {
        const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });
        const result = await model.generateContent("Hello");
        console.log("Success with gemini-2.5-flash:", result.response.text());
    } catch (error) {
        console.error("Error with gemini-2.5-flash:", error.message);
    }


}

testModel();
