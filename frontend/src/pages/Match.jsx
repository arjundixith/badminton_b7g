import { useEffect, useState } from "react";

import { getMatches, updateScore } from "../api";

export default function Match() {
    const [matches, setMatches] = useState([]);
    const [selectedMatchId, setSelectedMatchId] = useState("");
    const [s1, setS1] = useState(0);
    const [s2, setS2] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    useEffect(() => {
        let mounted = true;

        async function loadMatches() {
            try {
                const payload = await getMatches();
                if (!mounted) {
                    return;
                }

                setMatches(payload);
                if (payload.length > 0) {
                    setSelectedMatchId(String(payload[0].id));
                    setS1(payload[0].team1_score);
                    setS2(payload[0].team2_score);
                }
            } catch (err) {
                if (mounted) {
                    setError(err.message || "Failed to load matches");
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        }

        loadMatches();

        return () => {
            mounted = false;
        };
    }, []);

    const selectedMatch = matches.find((match) => String(match.id) === selectedMatchId);

    async function handleSubmit() {
        if (!selectedMatchId) {
            return;
        }

        setError("");
        setMessage("");

        try {
            const updated = await updateScore(Number(selectedMatchId), s1, s2);
            setMatches((prev) => prev.map((match) => (match.id === updated.id ? updated : match)));
            setMessage("Score saved.");
        } catch (err) {
            setError(err.message || "Failed to update score");
        }
    }

    function handleMatchChange(event) {
        const newMatchId = event.target.value;
        setSelectedMatchId(newMatchId);

        const found = matches.find((match) => String(match.id) === newMatchId);
        if (found) {
            setS1(found.team1_score);
            setS2(found.team2_score);
        }

        setMessage("");
        setError("");
    }

    if (loading) {
        return <div style={{ padding: 16 }}>Loading match data...</div>;
    }

    if (error && matches.length === 0) {
        return (
            <div style={{ padding: 16 }}>
                <h1>Live Score</h1>
                <p style={{ color: "#b91c1c" }}>{error}</p>
            </div>
        );
    }

    return (
        <div style={{ padding: 16 }}>
            <h1>Live Score</h1>

            {matches.length === 0 && <p>No matches found.</p>}

            {matches.length > 0 && (
                <>
                    <label htmlFor="match-select">Match</label>
                    <select
                        id="match-select"
                        style={{ marginLeft: 8, marginBottom: 12 }}
                        value={selectedMatchId}
                        onChange={handleMatchChange}
                    >
                        {matches.map((match) => (
                            <option key={match.id} value={match.id}>
                                #{match.id} {match.team1} vs {match.team2}
                            </option>
                        ))}
                    </select>

                    <div style={{ marginBottom: 12 }}>
                        <strong>{selectedMatch?.team1 || "Team 1"}</strong>
                        <button style={{ marginLeft: 8 }} onClick={() => setS1((value) => value + 1)}>
                            +
                        </button>
                        <span style={{ marginLeft: 8 }}>{s1}</span>
                    </div>

                    <div style={{ marginBottom: 12 }}>
                        <strong>{selectedMatch?.team2 || "Team 2"}</strong>
                        <button style={{ marginLeft: 8 }} onClick={() => setS2((value) => value + 1)}>
                            +
                        </button>
                        <span style={{ marginLeft: 8 }}>{s2}</span>
                    </div>

                    <button onClick={handleSubmit}>Submit</button>
                </>
            )}

            {message && <p style={{ color: "#166534" }}>{message}</p>}
            {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
        </div>
    );
}
