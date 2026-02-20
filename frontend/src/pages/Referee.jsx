import { useEffect, useMemo, useState } from "react";

import { assignReferee, getMatches, updateScore } from "../api";

export default function Referee() {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const [tie, setTie] = useState(null);
    const [selectedMatch, setSelectedMatch] = useState(null);

    const [name, setName] = useState("");
    const [match, setMatch] = useState(null);
    const [ref, setRef] = useState(null);

    useEffect(() => {
        let mounted = true;

        async function loadMatches() {
            try {
                const payload = await getMatches();
                if (mounted) {
                    setMatches(payload);
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

    const ties = useMemo(() => {
        const values = new Set(matches.map((item) => item.tie_id));
        return [...values].sort((a, b) => a - b);
    }, [matches]);

    const tieMatches = useMemo(
        () => matches.filter((item) => item.tie_id === tie),
        [matches, tie],
    );

    async function start() {
        if (!name.trim()) {
            setError("Enter referee name");
            return;
        }
        if (!selectedMatch) {
            setError("Select a match first");
            return;
        }

        setError("");

        try {
            const payload = await assignReferee({
                matchId: selectedMatch,
                name,
            });

            setRef(payload.referee);
            setMatch(payload.match);
        } catch (err) {
            setError(err.message || "Failed to assign referee");
        }
    }

    async function score(team, delta) {
        if (!match) {
            return;
        }

        let s1 = match.team1_score;
        let s2 = match.team2_score;

        if (team === 1) {
            s1 += delta;
        } else {
            s2 += delta;
        }

        if (s1 < 0 || s2 < 0) {
            return;
        }

        setError("");

        try {
            const updated = await updateScore(match.id, s1, s2);
            setMatch(updated);
            setMatches((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
        } catch (err) {
            setError(err.message || "Failed to update score");
        }
    }

    if (loading) {
        return <div style={styles.page}>Loading referee console...</div>;
    }

    if (error && matches.length === 0) {
        return (
            <div style={styles.page}>
                <h1 style={styles.title}>Referee Console</h1>
                <p style={styles.error}>{error}</p>
            </div>
        );
    }

    if (!tie)
        return (
            <div style={styles.page}>
                <h1 style={styles.title}>Select Tie</h1>
                {error && <p style={styles.error}>{error}</p>}

                <div style={styles.tieBar}>
                    {ties.map((value) => (
                        <button key={value} onClick={() => setTie(value)} style={styles.tieBtn}>
                            Tie {value}
                        </button>
                    ))}
                </div>
            </div>
        );

    if (!selectedMatch)
        return (
            <div style={styles.page}>
                <div style={styles.headerRow}>
                    <button style={styles.back} onClick={() => setTie(null)}>
                        ←
                    </button>
                    <h2>Tie {tie}</h2>
                </div>
                {error && <p style={styles.error}>{error}</p>}

                <div style={styles.grid}>
                    {tieMatches.map((item) => {
                        const status =
                            item.team1_score === 0 && item.team2_score === 0
                                ? "pending"
                                : item.winner_side
                                  ? "done"
                                  : "live";

                        return (
                            <div
                                key={item.id}
                                style={styles.card}
                                onClick={() => setSelectedMatch(item.id)}
                            >
                                <div style={styles.set}>Set {item.match_no}</div>

                                <div style={styles.team}>{item.team1}</div>
                                <div style={styles.vs}>vs</div>
                                <div style={styles.team}>{item.team2}</div>

                                <div
                                    style={{
                                        ...styles.badge,
                                        background:
                                            status === "pending"
                                                ? "#6b7280"
                                                : status === "live"
                                                  ? "#f59e0b"
                                                  : "#16a34a",
                                    }}
                                >
                                    {status}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        );

    if (!match)
        return (
            <div style={styles.page}>
                <div style={styles.headerRow}>
                    <button style={styles.back} onClick={() => setSelectedMatch(null)}>
                        ←
                    </button>
                    <h2>Enter Referee Name</h2>
                </div>
                {error && <p style={styles.error}>{error}</p>}

                <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Enter name"
                    style={styles.input}
                />

                <button style={styles.start} onClick={start}>
                    Start Match
                </button>
            </div>
        );

    return (
        <div style={styles.page}>
            <div style={styles.headerRow}>
                <button
                    style={styles.back}
                    onClick={() => {
                        setMatch(null);
                        setRef(null);
                        setName("");
                        setSelectedMatch(null);
                    }}
                >
                    ←
                </button>

                <h2>
                    Tie {match.tie_id} | Set {match.match_no}
                </h2>
            </div>

            {error && <p style={styles.error}>{error}</p>}

            <div style={styles.teams}>
                {match.team1} vs {match.team2}
            </div>

            <div style={styles.ref}>Referee: {ref?.name || "N/A"}</div>

            <div style={styles.scoreBox}>
                <div style={styles.score}>{match.team1_score}</div>

                <div style={styles.row}>
                    <button style={styles.plus} onClick={() => score(1, 1)}>
                        +
                    </button>
                    <button style={styles.minus} onClick={() => score(1, -1)}>
                        -
                    </button>
                </div>
            </div>

            <div style={styles.scoreBox}>
                <div style={styles.score}>{match.team2_score}</div>

                <div style={styles.row}>
                    <button style={styles.plus} onClick={() => score(2, 1)}>
                        +
                    </button>
                    <button style={styles.minus} onClick={() => score(2, -1)}>
                        -
                    </button>
                </div>
            </div>
        </div>
    );
}

const styles = {
    page: {
        padding: 20,
        fontFamily: "Inter, system-ui",
    },

    title: {
        textAlign: "center",
        marginBottom: 25,
    },

    error: {
        color: "#b91c1c",
        marginBottom: 12,
    },

    tieBar: {
        display: "flex",
        gap: 10,
        overflowX: "auto",
        paddingBottom: 10,
    },

    tieBtn: {
        padding: "14px 22px",
        border: "none",
        borderRadius: 12,
        background: "#4f46e5",
        color: "#fff",
        fontWeight: 600,
        cursor: "pointer",
        whiteSpace: "nowrap",
    },

    headerRow: {
        display: "flex",
        alignItems: "center",
        gap: 10,
        marginBottom: 15,
    },

    back: {
        fontSize: 20,
        border: "none",
        background: "transparent",
        cursor: "pointer",
    },

    grid: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
        gap: 16,
    },

    card: {
        background: "#fff",
        borderRadius: 16,
        padding: 18,
        boxShadow: "0 6px 16px rgba(0,0,0,0.08)",
        textAlign: "center",
        cursor: "pointer",
        position: "relative",
    },

    set: {
        fontWeight: 700,
        color: "#4f46e5",
        marginBottom: 10,
    },

    team: {
        fontWeight: 600,
    },

    vs: {
        fontSize: 12,
        color: "#888",
        margin: "6px 0",
    },

    badge: {
        position: "absolute",
        top: 10,
        right: 10,
        color: "#fff",
        fontSize: 12,
        padding: "4px 10px",
        borderRadius: 20,
    },

    input: {
        padding: 14,
        borderRadius: 10,
        border: "1px solid #ccc",
        fontSize: 16,
        marginTop: 15,
    },

    start: {
        marginTop: 20,
        padding: "14px 40px",
        border: "none",
        borderRadius: 12,
        background: "#4f46e5",
        color: "#fff",
        fontWeight: 600,
        cursor: "pointer",
    },

    teams: {
        textAlign: "center",
        marginTop: 8,
        fontSize: 18,
    },

    ref: {
        textAlign: "center",
        marginTop: 6,
        color: "#666",
    },

    scoreBox: {
        marginTop: 35,
        textAlign: "center",
    },

    score: {
        fontSize: 72,
        fontWeight: 800,
    },

    row: {
        display: "flex",
        justifyContent: "center",
        gap: 15,
        marginTop: 10,
    },

    plus: {
        padding: "20px 32px",
        fontSize: 26,
        background: "#16a34a",
        color: "#fff",
        border: "none",
        borderRadius: 14,
    },

    minus: {
        padding: "20px 32px",
        fontSize: 26,
        background: "#dc2626",
        color: "#fff",
        border: "none",
        borderRadius: 14,
    },
};
