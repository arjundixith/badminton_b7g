const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const API = baseUrl.replace(/\/$/, "");

async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, options);

    if (!response.ok) {
        let message = `Request failed with status ${response.status}`;
        try {
            const payload = await response.json();
            if (payload?.detail) {
                message = payload.detail;
            }
        } catch {
            // Keep default message when response body is not JSON.
        }
        throw new Error(message);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

export function getTeams() {
    return request("/teams/");
}

export function getMatches() {
    return request("/matches/");
}

export function getSchedule() {
    return request("/schedule/");
}

export function assignReferee({ matchId, name }) {
    const query = new URLSearchParams({
        match_id: String(matchId),
        name,
    });

    return request(`/referee/assign?${query.toString()}`, {
        method: "POST",
    });
}

export function updateScore(matchId, score1, score2) {
    return request(`/matches/score/${matchId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ score1, score2 }),
    });
}
