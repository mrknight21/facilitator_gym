const API_BASE = "/api";

export const api = {
    async startSession(caseStudyId: string, createdBy: string) {
        const res = await fetch(`${API_BASE}/sessions/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                case_study_id: caseStudyId,
                created_by: createdBy,
                config: {}
            })
        });
        if (!res.ok) throw new Error("Failed to start session");
        return res.json();
    },

    async stopSession(sessionId: string) {
        const res = await fetch(`${API_BASE}/sessions/${sessionId}/stop`, {
            method: "POST",
            keepalive: true // Important for window unload
        });
        if (!res.ok) throw new Error("Failed to stop session");
        return res.json();
    },

    async getToken(sessionId: string, identity: string) {
        const res = await fetch(`${API_BASE}/sessions/${sessionId}/token`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identity, role: "facilitator" })
        });
        if (!res.ok) throw new Error("Failed to get token");
        return res.json();
    },

    async intervene(sessionId: string, parentBranchId: string, atUtteranceId: string, text: string, createdBy: string) {
        const res = await fetch(`${API_BASE}/sessions/${sessionId}/intervene`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                parent_branch_id: parentBranchId,
                at_utterance_id: atUtteranceId,
                intervention_text: text,
                created_by: createdBy
            })
        });
        if (!res.ok) throw new Error("Failed to intervene");
        return res.json();
    },

    async getTranscript(sessionId: string, branchId: string) {
        const res = await fetch(`${API_BASE}/sessions/${sessionId}/branches/${branchId}/transcript`);
        if (!res.ok) throw new Error("Failed to get transcript");
        return res.json();
    },

    async getCaseStudies() {
        const res = await fetch(`${API_BASE}/case-studies`);
        if (!res.ok) throw new Error("Failed to get case studies");
        return res.json();
    }
};
