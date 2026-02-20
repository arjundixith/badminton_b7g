import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getViewerDashboard } from "../api";

export default function Home() {
    const [dashboard, setDashboard] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let mounted = true;
        let intervalId;

        async function loadDashboard({ initial = false } = {}) {
            try {
                const payload = await getViewerDashboard();
                if (mounted) {
                    setDashboard(payload);
                    setError("");
                }
            } catch (err) {
                if (mounted) {
                    setError(err.message || "Failed to load dashboard");
                }
            } finally {
                if (mounted && initial) {
                    setLoading(false);
                }
            }
        }

        loadDashboard({ initial: true });
        intervalId = window.setInterval(() => {
            loadDashboard();
        }, 4000);

        return () => {
            mounted = false;
            if (intervalId) {
                window.clearInterval(intervalId);
            }
        };
    }, []);

    const stats = dashboard?.summary ?? {
        total_games: 0,
        pending_games: 0,
        live_games: 0,
        completed_games: 0,
    };
    const standings = dashboard?.standings ?? [];
    const ties = dashboard?.ties ?? [];
    const totalTies = dashboard?.summary?.total_ties ?? ties.length;
    const completedTies = dashboard?.summary?.completed_ties ?? ties.filter((tie) => tie.status === "completed").length;
    const leagueComplete = totalTies > 0 && completedTies === totalTies;
    const medals = dashboard?.medals ?? {};
    const finalMatch = dashboard?.final_match ?? null;

    return (
        <section className="stack-lg">
            <article className="hero panel" data-animate="true">
                <p className="eyebrow">B7G Tournament Operations</p>
                <h2>Manage referee scoring and broadcast live tie status clearly.</h2>
                <p>
                    Referees can assign themselves per match and update points under badminton rules.
                    Viewers can track pending, live, and completed games across all league ties.
                </p>

                <div className="hero-actions">
                    <Link to="/viewer" className="btn btn-primary">
                        Open Viewer Console
                    </Link>
                    <Link to="/referee" className="btn btn-outline">
                        Open Referee Console
                    </Link>
                </div>
            </article>

            <div className="grid three">
                <article className="panel" data-animate="true" style={{ animationDelay: "80ms" }}>
                    <p className="metric-label">Games</p>
                    <h3>{stats.total_games}</h3>
                    <p>Total scheduled matches</p>
                </article>

                <article className="panel" data-animate="true" style={{ animationDelay: "140ms" }}>
                    <p className="metric-label">Pending</p>
                    <h3>{stats.pending_games}</h3>
                    <p>Waiting for kickoff</p>
                </article>

                <article className="panel" data-animate="true" style={{ animationDelay: "200ms" }}>
                    <p className="metric-label">Completed</p>
                    <h3>{stats.completed_games}</h3>
                    <p>Finished and locked</p>
                </article>
            </div>

            <div className="grid two">
                <article className="panel" data-animate="true" style={{ animationDelay: "260ms" }}>
                    <div className="podium-strip">
                        <article className="podium-card">
                            <p>Gold</p>
                            <h5>{medals.gold_team ?? "TBD"}</h5>
                        </article>
                        <article className="podium-card">
                            <p>Silver</p>
                            <h5>{medals.silver_team ?? "TBD"}</h5>
                        </article>
                        <article className="podium-card">
                            <p>Bronze</p>
                            <h5>{medals.bronze_team ?? "TBD"}</h5>
                        </article>
                    </div>

                    <h3>Tournament Rule Snapshot</h3>
                    {loading && <p>Loading rules...</p>}
                    {!loading && error && <p className="error-text">{error}</p>}
                    {!loading && !error && (
                        <ul className="clean-list">
                            {(dashboard?.rule_highlights ?? []).map((item) => (
                                <li key={item}>{item}</li>
                            ))}
                        </ul>
                    )}
                </article>

                <article className="panel" data-animate="true" style={{ animationDelay: "320ms" }}>
                    <h3>Table Outcome</h3>
                    {loading && <p>Loading standings summary...</p>}
                    {!loading && !error && (
                        <>
                            {leagueComplete ? (
                                <>
                                    <p>
                                        <strong>Finalist 1:</strong> {medals.finalist1 ?? "TBD"}
                                    </p>
                                    <p>
                                        <strong>Finalist 2:</strong> {medals.finalist2 ?? "TBD"}
                                    </p>
                                    <p>
                                        <strong>Final Tie:</strong>{" "}
                                        {finalMatch ? `${finalMatch.team1} vs ${finalMatch.team2}` : "Pending"}
                                    </p>
                                    <p>
                                        <strong>Final Score:</strong>{" "}
                                        {finalMatch ? `${finalMatch.team1_score} - ${finalMatch.team2_score} (${finalMatch.status})` : "-"}
                                    </p>
                                    <p>
                                        <strong>Gold:</strong> {medals.gold_team ?? "Pending"} • <strong>Silver:</strong>{" "}
                                        {medals.silver_team ?? "Pending"} • <strong>Bronze:</strong> {medals.bronze_team ?? "Pending"}
                                    </p>
                                </>
                            ) : (
                                <>
                                    <p>
                                        <strong>Current #1:</strong> {standings.length ? standings[0].team : "Not decided"}
                                    </p>
                                    <p className="muted-note">
                                        Finals will lock only after all {totalTies || 10} ties are completed.
                                    </p>
                                </>
                            )}
                        </>
                    )}
                </article>
            </div>
        </section>
    );
}
