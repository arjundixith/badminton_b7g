import { useEffect, useState } from "react";

import { getPostFinalsSummary } from "../api";

function medalCardClass(label) {
    if (label === "Gold") {
        return "podium-card gold";
    }
    if (label === "Silver") {
        return "podium-card silver";
    }
    return "podium-card bronze";
}

export default function PostFinals() {
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let mounted = true;
        let intervalId;

        async function loadSummary({ initial = false } = {}) {
            try {
                const payload = await getPostFinalsSummary();
                if (mounted) {
                    setSummary(payload);
                    setError("");
                }
            } catch (err) {
                if (mounted) {
                    setError(err.message || "Failed to load post-finals summary");
                }
            } finally {
                if (mounted && initial) {
                    setLoading(false);
                }
            }
        }

        loadSummary({ initial: true });
        intervalId = window.setInterval(() => {
            loadSummary();
        }, 2500);

        return () => {
            mounted = false;
            if (intervalId) {
                window.clearInterval(intervalId);
            }
        };
    }, []);

    if (loading) {
        return <section className="panel">Loading post-finals summary...</section>;
    }

    if (error) {
        return <section className="panel error-text">{error}</section>;
    }

    const medals = summary?.medals ?? {};
    const categories = summary?.categories ?? [];

    return (
        <section className="stack-lg">
            <article className="panel" data-animate="true">
                <p className="eyebrow">Post Finals</p>
                <h2>Individual Category Winners</h2>
                <p>Leaders are based on total individual match wins in each category across completed matches.</p>
                <p className="match-meta">Tie-break: lower opponent points, then higher lead.</p>
                <p className="match-meta">
                    Final status: {summary?.final_status ?? "pending"} • Completed matches considered: {summary?.total_matches_considered ?? 0}
                </p>
                {!summary?.final_completed && (
                    <p className="muted-note">Final tie is not completed yet. Results will keep updating until final completion.</p>
                )}
            </article>

            <div className="podium-strip">
                <article className={medalCardClass("Gold")}>
                    <p>Gold Team</p>
                    <h5>{medals.gold_team ?? "TBD"}</h5>
                </article>
                <article className={medalCardClass("Silver")}>
                    <p>Silver Team</p>
                    <h5>{medals.silver_team ?? "TBD"}</h5>
                </article>
                <article className={medalCardClass("Bronze")}>
                    <p>Bronze Team</p>
                    <h5>{medals.bronze_team ?? "TBD"}</h5>
                </article>
            </div>

            <article className="panel">
                <div className="panel-head">
                    <h3>Category Champions</h3>
                    <p>Best performer in each requested category</p>
                </div>

                <div className="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Category</th>
                                <th>Champion(s)</th>
                                <th>Wins</th>
                                <th>Opponent Points</th>
                                <th>Lead</th>
                            </tr>
                        </thead>
                        <tbody>
                            {categories.map((item) => (
                                <tr key={item.category}>
                                    <td>{item.category}</td>
                                    <td>{item.winner_names?.length ? item.winner_names.join(", ") : "-"}</td>
                                    <td>{item.winner_wins ?? 0}</td>
                                    <td>{item.winner_opponent_score ?? 0}</td>
                                    <td>{item.winner_lead_score ?? 0}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </article>

            <article className="panel">
                <div className="panel-head">
                    <h3>Detailed Individual Wins</h3>
                    <p>All counted players per category</p>
                </div>
                <div className="stack-sm">
                    {categories.map((item) => (
                        <div key={`detail-${item.category}`} className="lineup-box stack-sm">
                            <h5>{item.category}</h5>
                            {item.rankings?.length ? (
                                <div className="table-wrap">
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Player</th>
                                                <th>Wins</th>
                                                <th>Opponent Points</th>
                                                <th>Lead</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {item.rankings.map((row) => (
                                                <tr key={`${item.category}-${row.player_name}`}>
                                                    <td>{row.player_name}</td>
                                                    <td>{row.wins}</td>
                                                    <td>{row.opponent_score ?? 0}</td>
                                                    <td>{row.lead_score ?? 0}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <p className="muted-note">No individual wins recorded in this category yet.</p>
                            )}
                        </div>
                    ))}
                </div>
            </article>
        </section>
    );
}
