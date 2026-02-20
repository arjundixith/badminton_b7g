const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const API = baseUrl.replace(/\/$/, "");

async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
        cache: "no-store",
        ...options,
    });

    if (!response.ok) {
        let message = `Request failed (${response.status})`;

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

export function getViewerDashboard() {
    return request("/viewer/dashboard");
}

export function getStandings() {
    return request("/viewer/standings");
}

export function getMatches({ stage, status, tieId } = {}) {
    const query = new URLSearchParams();

    if (stage) {
        query.set("stage", stage);
    }
    if (status) {
        query.set("status", status);
    }
    if (tieId) {
        query.set("tie_id", String(tieId));
    }

    const suffix = query.toString() ? `?${query.toString()}` : "";
    return request(`/matches/${suffix}`);
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
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ score1, score2 }),
    });
}

export function updateLineup(matchId, team1Lineup, team2Lineup) {
    return request(`/matches/${matchId}/lineup`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            team1_lineup: team1Lineup,
            team2_lineup: team2Lineup,
        }),
    });
}

export function updateMatchStatus(matchId, status) {
    return request(`/matches/${matchId}/status`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ status }),
    });
}

export function assignFinalReferee(name) {
    const query = new URLSearchParams({ name: String(name || "") });
    return request(`/finals/assign?${query.toString()}`, {
        method: "POST",
    });
}

export function updateFinalScore(score1, score2) {
    return request("/finals/score", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ score1, score2 }),
    });
}

export function assignFinalGameReferee(gameId, name) {
    const query = new URLSearchParams({ name: String(name || "") });
    return request(`/finals/games/${gameId}/assign?${query.toString()}`, {
        method: "POST",
    });
}

export function updateFinalGameScore(gameId, score1, score2) {
    return request(`/finals/games/${gameId}/score`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ score1, score2 }),
    });
}
