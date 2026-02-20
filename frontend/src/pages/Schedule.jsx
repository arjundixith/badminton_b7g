import { useEffect, useState } from "react";

import { getSchedule } from "../api";

export default function Schedule() {
    const [data, setData] = useState({});
    const [day, setDay] = useState("1");
    const [session, setSession] = useState("morning");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let mounted = true;

        async function loadSchedule() {
            try {
                const payload = await getSchedule();
                if (!mounted) {
                    return;
                }

                setData(payload);
                const days = Object.keys(payload);
                if (days.length > 0 && !payload[day]) {
                    setDay(days[0]);
                    const sessions = Object.keys(payload[days[0]] || {});
                    if (sessions.length > 0) {
                        setSession(sessions[0]);
                    }
                }
            } catch (err) {
                if (mounted) {
                    setError(err.message || "Failed to load schedule");
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        }

        loadSchedule();

        return () => {
            mounted = false;
        };
    }, []);

    const dayOptions = Object.keys(data);
    const sessionOptions = Object.keys(data?.[day] || {});
    const matches = data?.[day]?.[session] || [];

    if (loading) {
        return <div style={{ padding: 16 }}>Loading schedule...</div>;
    }

    return (
        <div style={{ padding: 16, fontFamily: "Inter, system-ui" }}>
            <h1>Schedule</h1>
            {error && <p style={{ color: "#b91c1c" }}>{error}</p>}

            {dayOptions.length > 0 && (
                <div style={{ display: "flex", gap: 10 }}>
                    {dayOptions.map((value) => (
                        <button key={value} onClick={() => setDay(value)}>
                            Day {value}
                        </button>
                    ))}
                </div>
            )}

            {sessionOptions.length > 0 && (
                <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
                    {sessionOptions.map((value) => (
                        <button key={value} onClick={() => setSession(value)}>
                            {value}
                        </button>
                    ))}
                </div>
            )}

            <div style={{ marginTop: 20 }}>
                {matches.map((match) => (
                    <div
                        key={match.id}
                        style={{ padding: 12, border: "1px solid #ddd", marginBottom: 10 }}
                    >
                        <b>{match.team1}</b> vs <b>{match.team2}</b>

                        <div>Match {match.match_no}</div>
                        <div>
                            Court {match.court ?? "-"} | {match.time ?? "TBD"}
                        </div>

                        <div style={{ fontSize: 20, fontWeight: 700 }}>
                            {match.score1} - {match.score2}
                        </div>
                    </div>
                ))}

                {matches.length === 0 && <p>No matches in this slot.</p>}
            </div>
        </div>
    );
}
