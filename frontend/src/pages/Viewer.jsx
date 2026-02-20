import { useEffect, useMemo, useState } from "react";

import { getViewerDashboard } from "../api";

function isDeciderMatch(match) {
    if (match.match_no === 13) {
        return true;
    }

    return (match.discipline || "").toLowerCase().includes("decider");
}

function getTieResultForSide(tie, side) {
    if (tie.status !== "completed" || !tie.winner_team_id) {
        return "tbd";
    }

    const winnerIsTeam1 = tie.winner_team_id === tie.team1_id;
    const won = (side === 1 && winnerIsTeam1) || (side === 2 && !winnerIsTeam1);
    return won ? "win" : "loss";
}

function formatSignedNumber(value) {
    const number = Number(value ?? 0);
    if (!Number.isFinite(number)) {
        return "0";
    }
    return `${number > 0 ? "+" : ""}${number}`;
}

function formatAverageLead(value) {
    const number = Number(value ?? 0);
    if (!Number.isFinite(number)) {
        return "0.00";
    }
    return `${number > 0 ? "+" : ""}${number.toFixed(2)}`;
}

function getMedalForTeam(teamName, medals) {
    if (!teamName || !medals) {
        return "";
    }
    if (medals.gold_team === teamName) {
        return "gold";
    }
    if (medals.silver_team === teamName) {
        return "silver";
    }
    if (medals.bronze_team === teamName) {
        return "bronze";
    }
    return "";
}

export default function Viewer() {
    const [dashboard, setDashboard] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [selectedTeamId, setSelectedTeamId] = useState(null);

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
                    setError(err.message || "Failed to load viewer dashboard");
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
        }, 1500);

        return () => {
            mounted = false;
            if (intervalId) {
                window.clearInterval(intervalId);
            }
        };
    }, []);

    const ties = dashboard?.ties ?? [];
    const tieStandings = dashboard?.standings ?? [];
    const finalMatch = dashboard?.final_match ?? null;
    const medals = dashboard?.medals ?? {};
    const completedTieCount = ties.filter((tie) => tie.status === "completed").length;
    const tieProgress = useMemo(() => [...ties].sort((a, b) => a.tie_no - b.tie_no), [ties]);
    const leagueComplete =
        Number(dashboard?.summary?.total_ties ?? ties.length) > 0 &&
        Number(dashboard?.summary?.completed_ties ?? completedTieCount) === Number(dashboard?.summary?.total_ties ?? ties.length);
    const liveMatches = useMemo(() => {
        return tieProgress
            .flatMap((tie) =>
                tie.matches
                    .filter((match) => match.status === "live")
                    .map((match) => ({ ...match, tie_no: tie.tie_no })),
            )
            .sort((a, b) => {
                if ((a.tie_no ?? 0) !== (b.tie_no ?? 0)) {
                    return (a.tie_no ?? 0) - (b.tie_no ?? 0);
                }
                return a.match_no - b.match_no;
            });
    }, [tieProgress]);

    const teamTabs = useMemo(
        () =>
            tieStandings.map((row) => ({
                teamId: row.team_id,
                team: row.team,
                qualification: row.qualification,
                medal: getMedalForTeam(row.team, medals),
            })),
        [tieStandings, medals],
    );

    useEffect(() => {
        if (teamTabs.length === 0) {
            setSelectedTeamId(null);
            return;
        }

        const exists = teamTabs.some((team) => team.teamId === selectedTeamId);
        if (!exists) {
            setSelectedTeamId(teamTabs[0].teamId);
        }
    }, [teamTabs, selectedTeamId]);

    const selectedTeamTab = useMemo(
        () => teamTabs.find((team) => team.teamId === selectedTeamId) || null,
        [teamTabs, selectedTeamId],
    );

    const selectedTeamTies = useMemo(() => {
        if (!selectedTeamTab) {
            return [];
        }

        return tieProgress
            .filter((tie) => tie.team1_id === selectedTeamTab.teamId || tie.team2_id === selectedTeamTab.teamId)
            .map((tie) => {
                const selectedTeamIsSide1 = tie.team1_id === selectedTeamTab.teamId;
                const scoreFor = selectedTeamIsSide1 ? tie.score1 : tie.score2;
                const scoreAgainst = selectedTeamIsSide1 ? tie.score2 : tie.score1;
                const result = getTieResultForSide(tie, selectedTeamIsSide1 ? 1 : 2);
                const regularMatches = tie.matches.filter((match) => !isDeciderMatch(match));
                const deciderMatch = tie.matches.find((match) => isDeciderMatch(match));
                const includeDecider = deciderMatch ? deciderMatch.status !== "pending" : false;
                const visibleMatches = includeDecider ? [...regularMatches, deciderMatch] : regularMatches;
                const completedGames = visibleMatches.filter((match) => match.status === "completed").length;

                return {
                    ...tie,
                    opponent: selectedTeamIsSide1 ? tie.team2 : tie.team1,
                    scoreFor,
                    scoreAgainst,
                    result,
                    completedGames,
                    totalGames: visibleMatches.length,
                };
            })
            .sort((a, b) => a.tie_no - b.tie_no);
    }, [selectedTeamTab, tieProgress]);

    if (loading) {
        return <section className="panel">Loading viewer console...</section>;
    }

    if (error) {
        return <section className="panel error-text">{error}</section>;
    }

    return (
        <section className="stack-lg viewer-shell">
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

            <article className="panel viewer-hero" data-animate="true">
                <div className="viewer-hero-head">
                    <div>
                        <p className="eyebrow">Viewer Console</p>
                        <h2>Live Tournament Center</h2>
                        <p>Fast, mobile-first live score tracking across all round-robin ties.</p>
                    </div>
                    <div className={`live-pill ${dashboard.summary.live_games > 0 ? "is-live" : ""}`}>
                        {dashboard.summary.live_games > 0 ? `${dashboard.summary.live_games} Live` : "No Live"}
                    </div>
                </div>

                <div className="live-score-grid" aria-live="polite">
                    {liveMatches.length === 0 && (
                        <article className="live-score-card live-score-empty">
                            <p className="match-meta">No live match</p>
                            <h4>Live scores will appear here automatically.</h4>
                        </article>
                    )}

                    {liveMatches.slice(0, 2).map((match) => (
                        <article key={match.id} className="live-score-card">
                            <div className="live-score-head">
                                <p className="match-meta">
                                    Tie {match.tie_no} • #{match.match_no} • Court {match.court}
                                </p>
                                <span className="status-pill live">Live</span>
                            </div>
                            <h4>
                                {match.team1} vs {match.team2}
                            </h4>
                            <p className="live-score-value">
                                {match.team1_score} - {match.team2_score}
                            </p>
                        </article>
                    ))}

                    {liveMatches.length === 1 && (
                        <article className="live-score-card live-score-empty">
                            <p className="match-meta">Live slot 2</p>
                            <h4>Waiting for next live court.</h4>
                        </article>
                    )}
                </div>
                {liveMatches.length > 2 && <p className="match-meta">+{liveMatches.length - 2} more live matches</p>}

                <div className="kpi-strip">
                    <div className="kpi-card">
                        <p>Total Games</p>
                        <strong>{dashboard.summary.total_games}</strong>
                    </div>
                    <div className="kpi-card">
                        <p>Pending</p>
                        <strong>{dashboard.summary.pending_games}</strong>
                    </div>
                    <div className="kpi-card">
                        <p>Completed</p>
                        <strong>{dashboard.summary.completed_games}</strong>
                    </div>
                    <div className="kpi-card">
                        <p>Completed Ties</p>
                        <strong>
                            {dashboard.summary.completed_ties ?? completedTieCount}/{(dashboard.summary.total_ties ?? ties.length) || 10}
                        </strong>
                    </div>
                </div>
            </article>

            <div className="viewer-grid">
                <article className="panel viewer-team-panel" data-animate="true" style={{ animationDelay: "40ms" }}>
                    <div className="panel-head">
                        <h3>Team-Wise Ties</h3>
                        <p>Open a team tab to see its 4 league ties.</p>
                    </div>

                    <div className="team-tabs-scroll">
                        {teamTabs.map((team) => (
                            <button
                                key={team.teamId}
                                className={`chip ${selectedTeamId === team.teamId ? "active" : ""}`}
                                onClick={() => setSelectedTeamId(team.teamId)}
                            >
                                {team.team}
                                {team.medal === "gold" ? " • Gold" : ""}
                                {team.medal === "silver" ? " • Silver" : ""}
                                {team.medal === "bronze" ? " • Bronze" : ""}
                                {!team.medal && team.qualification === "finalist" ? " • Finalist" : ""}
                                {!team.medal && team.qualification === "bronze" ? " • Bronze Medal" : ""}
                            </button>
                        ))}
                    </div>

                    <div className="table-wrap desktop-only-table" style={{ marginTop: 12 }}>
                        <table>
                            <thead>
                                <tr>
                                    <th>Tie</th>
                                    <th>Opponent</th>
                                    <th>Day</th>
                                    <th>Session</th>
                                    <th>Court</th>
                                    <th>Games</th>
                                    <th>Score</th>
                                    <th>Result</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {selectedTeamTies.map((tie) => (
                                    <tr key={tie.id}>
                                        <td>{tie.tie_no}</td>
                                        <td>{tie.opponent}</td>
                                        <td>{tie.day}</td>
                                        <td>{tie.session}</td>
                                        <td>{tie.court}</td>
                                        <td>
                                            {tie.completedGames}/{tie.totalGames}
                                        </td>
                                        <td>
                                            {tie.scoreFor} - {tie.scoreAgainst}
                                        </td>
                                        <td>{tie.result === "win" ? "W" : tie.result === "loss" ? "L" : "-"}</td>
                                        <td>{tie.status}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <div className="mobile-tie-list">
                        {selectedTeamTies.map((tie) => (
                            <article key={`mobile-${tie.id}`} className="mobile-tie-card">
                                <div className="mobile-tie-head">
                                    <p className="match-meta">
                                        Tie {tie.tie_no} • Day {tie.day} • Court {tie.court}
                                    </p>
                                    <span className={`status-pill ${tie.status}`}>{tie.status}</span>
                                </div>
                                <h5>
                                    {selectedTeamTab?.team} vs {tie.opponent}
                                </h5>
                                <p className="score">
                                    {tie.scoreFor} - {tie.scoreAgainst}
                                </p>
                                <p className="match-meta">
                                    Session {tie.session} • Games {tie.completedGames}/{tie.totalGames} •{" "}
                                    {tie.result === "win" ? "W" : tie.result === "loss" ? "L" : "-"}
                                </p>
                            </article>
                        ))}
                    </div>

                    {selectedTeamTies.length === 0 && <p className="muted-note">No ties found for selected team.</p>}
                </article>

                <article className="panel viewer-standings-panel" data-animate="true" style={{ animationDelay: "60ms" }}>
                    <div className="panel-head">
                        <h3>Round-Robin Standings</h3>
                        <p>Complete tie-result standings.</p>
                    </div>

                    {leagueComplete && (
                        <div className="podium-strip">
                            <article className="podium-card">
                                <p>Finalist 1</p>
                                <h5>{medals.finalist1 ?? "TBD"}</h5>
                            </article>
                            <article className="podium-card">
                                <p>Finalist 2</p>
                                <h5>{medals.finalist2 ?? "TBD"}</h5>
                            </article>
                            <article className="podium-card">
                                <p>Final Tie</p>
                                <h5>{finalMatch ? `${finalMatch.team1} vs ${finalMatch.team2}` : "Pending"}</h5>
                                <span>
                                    {finalMatch
                                        ? `${finalMatch.team1_score} - ${finalMatch.team2_score} (${finalMatch.status})`
                                        : "Will start after league completion"}
                                </span>
                            </article>
                        </div>
                    )}

                    <div className="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Team</th>
                                    <th>TP</th>
                                    <th>TW</th>
                                    <th>TL</th>
                                    <th>GW</th>
                                    <th>Pts</th>
                                    <th>Game Diff</th>
                                    <th>Avg Lead</th>
                                    <th>Medal</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tieStandings.map((row) => (
                                    <tr key={row.team_id}>
                                        <td>{row.rank}</td>
                                        <td>
                                            {row.team}
                                            {getMedalForTeam(row.team, medals) === "bronze" && (
                                                <span className="standing-badge bronze">Bronze Medal</span>
                                            )}
                                        </td>
                                        <td>{row.ties_played}</td>
                                        <td>{row.ties_won}</td>
                                        <td>{row.ties_lost}</td>
                                        <td>{row.games_won}</td>
                                        <td>{row.tie_points}</td>
                                        <td>{formatSignedNumber(row.game_difference)}</td>
                                        <td>{formatAverageLead(row.average_match_lead)}</td>
                                        <td>
                                            {getMedalForTeam(row.team, medals) === "gold" && (
                                                <span className="standing-badge gold">Gold</span>
                                            )}
                                            {getMedalForTeam(row.team, medals) === "silver" && (
                                                <span className="standing-badge silver">Silver</span>
                                            )}
                                            {getMedalForTeam(row.team, medals) === "bronze" && (
                                                <span className="standing-badge bronze">Bronze Medal</span>
                                            )}
                                            {getMedalForTeam(row.team, medals) === "" && row.qualification === "finalist" && (
                                                <span className="standing-badge finalist">Finalist</span>
                                            )}
                                            {getMedalForTeam(row.team, medals) === "" && row.qualification === "none" && "-"}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <p className="muted-note">
                        Tie-break order: ties won, games won, then average lead per game.
                    </p>
                </article>
            </div>
        </section>
    );
}
