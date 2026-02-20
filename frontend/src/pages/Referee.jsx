import { useEffect, useMemo, useRef, useState } from "react";

import { assignReferee, getMatches, updateLineup, updateMatchStatus, updateScore } from "../api";

const STATUS_FILTERS = ["pending", "live", "completed"];

function StatusPill({ status }) {
    return <span className={`status-pill ${status}`}>{status}</span>;
}

function toMinutes(value) {
    if (!value || !value.includes(":")) {
        return Number.MAX_SAFE_INTEGER;
    }

    const [hourText, minuteText] = value.split(":");
    const hour = Number(hourText);
    const minute = Number(minuteText);

    if (Number.isNaN(hour) || Number.isNaN(minute)) {
        return Number.MAX_SAFE_INTEGER;
    }

    return hour * 60 + minute;
}

function compareMatchOrder(a, b) {
    const aDay = a.day ?? Number.MAX_SAFE_INTEGER;
    const bDay = b.day ?? Number.MAX_SAFE_INTEGER;
    if (aDay !== bDay) {
        return aDay - bDay;
    }

    const aTime = toMinutes(a.time);
    const bTime = toMinutes(b.time);
    if (aTime !== bTime) {
        return aTime - bTime;
    }

    const aCourt = a.court ?? Number.MAX_SAFE_INTEGER;
    const bCourt = b.court ?? Number.MAX_SAFE_INTEGER;
    if (aCourt !== bCourt) {
        return aCourt - bCourt;
    }

    return a.match_no - b.match_no;
}

function normalizeLineup(value) {
    return value
        .split("/")
        .map((item) => item.trim())
        .filter(Boolean)
        .join(" / ");
}

function toLineupParts(value) {
    return normalizeLineup(value)
        .split("/")
        .map((item) => item.trim())
        .filter(Boolean);
}

function lineupForScore(value, strict) {
    const parts = toLineupParts(value);
    if (strict) {
        if (parts.length < 2) {
            return "";
        }
        return `${parts[0]} / ${parts[1]}`;
    }
    return parts.join(" / ");
}

function requiresRefereeLineupEntry(match) {
    if (!match || match.stage !== "tie") {
        return false;
    }

    if (typeof match.lineup_needs_referee_input === "boolean") {
        return match.lineup_needs_referee_input;
    }

    const discipline = (match.discipline || "").toLowerCase();
    if (discipline.includes("set 3 / womens advance")) {
        return false;
    }
    if (discipline.includes("womens advance / women intermediate")) {
        return false;
    }

    return (
        discipline.includes(" or ") ||
        discipline.includes("set-4") ||
        discipline.includes("set 4") ||
        discipline.includes("set-5") ||
        discipline.includes("set 5")
    );
}

function getScoreCap(score, opponentScore) {
    if (score >= 30) {
        return 30;
    }
    if (score >= 21 && opponentScore < 20) {
        return 21;
    }
    return score >= 20 && opponentScore >= 20 ? 30 : 21;
}

function isWinningScore(score1, score2) {
    if (score1 === score2) {
        return false;
    }

    const high = Math.max(score1, score2);
    const low = Math.min(score1, score2);
    return (high >= 21 && high - low >= 2) || high === 30;
}

function formatMatchLabel(match) {
    if (!match) {
        return "";
    }

    return `Tie ${match.tie_no ?? "-"} • #${match.match_no} • ${match.team1} vs ${match.team2}`;
}

export default function Referee() {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");
    const [lastCompletedStatus, setLastCompletedStatus] = useState("");

    const [statusFilter, setStatusFilter] = useState("pending");
    const [selectedCourt, setSelectedCourt] = useState(null);
    const [activeMatchId, setActiveMatchId] = useState(null);

    const [refereeDrafts, setRefereeDrafts] = useState({});
    const [score1, setScore1] = useState(0);
    const [score2, setScore2] = useState(0);
    const [team1LineupInput, setTeam1LineupInput] = useState("");
    const [team2LineupInput, setTeam2LineupInput] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [scoreDraftDirty, setScoreDraftDirty] = useState(false);
    const [lineupDraftDirty, setLineupDraftDirty] = useState(false);

    const hydratedActiveMatchIdRef = useRef(null);

    useEffect(() => {
        let mounted = true;

        async function loadMatches() {
            try {
                const payload = await getMatches();
                if (!mounted) {
                    return;
                }

                setMatches(payload);
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

    useEffect(() => {
        let mounted = true;

        const intervalId = window.setInterval(async () => {
            try {
                const payload = await getMatches();
                if (mounted) {
                    setMatches(payload);
                }
            } catch {
                // Silent refresh failure: existing state is still usable.
            }
        }, 4000);

        return () => {
            mounted = false;
            window.clearInterval(intervalId);
        };
    }, []);

    const orderedMatches = useMemo(() => {
        return [...matches].sort(compareMatchOrder);
    }, [matches]);

    const courtOptions = useMemo(
        () => [...new Set(orderedMatches.map((match) => match.court))].sort((a, b) => a - b),
        [orderedMatches],
    );

    useEffect(() => {
        if (courtOptions.length === 0) {
            setSelectedCourt(null);
            return;
        }

        if (selectedCourt == null) {
            setSelectedCourt(courtOptions[0]);
        }
    }, [courtOptions, selectedCourt]);

    const courtStageMatches = useMemo(
        () => orderedMatches.filter((match) => match.court === selectedCourt),
        [orderedMatches, selectedCourt],
    );

    const stageStatusMatches = useMemo(() => {
        return courtStageMatches.filter((match) => match.status === statusFilter);
    }, [courtStageMatches, statusFilter]);

    const queueMatches = stageStatusMatches;

    const currentLiveOnCourt = useMemo(() => {
        return courtStageMatches.find((match) => match.status === "live") || null;
    }, [courtStageMatches]);

    const recommendedNextMatch = useMemo(() => {
        return courtStageMatches.find((match) => match.status !== "completed") || null;
    }, [courtStageMatches]);

    const hasPendingOnCourt = useMemo(
        () => courtStageMatches.some((match) => match.status === "pending"),
        [courtStageMatches],
    );
    const hasLiveOnCourt = useMemo(
        () => courtStageMatches.some((match) => match.status === "live"),
        [courtStageMatches],
    );
    const hasCompletedOnCourt = useMemo(
        () => courtStageMatches.some((match) => match.status === "completed"),
        [courtStageMatches],
    );

    useEffect(() => {
        if (activeMatchId == null) {
            return;
        }

        const visible = matches.some((match) => match.id === activeMatchId);
        if (!visible) {
            setActiveMatchId(null);
        }
    }, [activeMatchId, matches]);

    const activeMatch = useMemo(() => {
        return matches.find((match) => match.id === activeMatchId) || null;
    }, [matches, activeMatchId]);

    const courtPreferredRefereeName = useMemo(() => {
        for (let index = courtStageMatches.length - 1; index >= 0; index -= 1) {
            const referee = courtStageMatches[index].referee_name;
            if (referee) {
                return referee;
            }
        }
        return "";
    }, [courtStageMatches]);

    useEffect(() => {
        if (!activeMatch) {
            hydratedActiveMatchIdRef.current = null;
            setScoreDraftDirty(false);
            setLineupDraftDirty(false);
            return;
        }

        const switchedMatch = hydratedActiveMatchIdRef.current !== activeMatch.id;
        if (switchedMatch || !scoreDraftDirty) {
            setScore1(activeMatch.team1_score);
            setScore2(activeMatch.team2_score);
            if (switchedMatch) {
                setScoreDraftDirty(false);
            }
        }

        if (switchedMatch || !lineupDraftDirty) {
            setTeam1LineupInput(activeMatch.team1_lineup || "");
            setTeam2LineupInput(activeMatch.team2_lineup || "");
            if (switchedMatch) {
                setLineupDraftDirty(false);
            }
        }

        setRefereeDrafts((prev) => {
            if (prev[activeMatch.id]?.trim()) {
                return prev;
            }

            const fallback = activeMatch.referee_name || courtPreferredRefereeName || "";
            if (!fallback) {
                return prev;
            }

            return { ...prev, [activeMatch.id]: fallback };
        });

        hydratedActiveMatchIdRef.current = activeMatch.id;
    }, [activeMatch, courtPreferredRefereeName, lineupDraftDirty, scoreDraftDirty]);

    function upsertMatch(updatedMatch) {
        setMatches((prev) => prev.map((match) => (match.id === updatedMatch.id ? updatedMatch : match)));
    }

    function getRefereeDraft(match) {
        return refereeDrafts[match.id] ?? match.referee_name ?? courtPreferredRefereeName ?? "";
    }

    const requiresStrictLineup = useMemo(() => requiresRefereeLineupEntry(activeMatch), [activeMatch]);
    const normalizedTeam1Lineup = useMemo(() => normalizeLineup(team1LineupInput), [team1LineupInput]);
    const normalizedTeam2Lineup = useMemo(() => normalizeLineup(team2LineupInput), [team2LineupInput]);

    const lineupDirty = useMemo(() => {
        if (!activeMatch) {
            return false;
        }

        return (
            normalizeLineup(activeMatch.team1_lineup || "") !== normalizedTeam1Lineup ||
            normalizeLineup(activeMatch.team2_lineup || "") !== normalizedTeam2Lineup
        );
    }, [activeMatch, normalizedTeam1Lineup, normalizedTeam2Lineup]);

    const lineupConfirmed = activeMatch?.lineup_confirmed ?? false;
    const statusSummary = useMemo(() => {
        const now = error ? `Error: ${error}` : message || "Ready";
        const completed = lastCompletedStatus || "Last completed: none";
        return `${now} • ${completed}`;
    }, [error, message, lastCompletedStatus]);

    async function handleStartMatch(match) {
        const refereeName = getRefereeDraft(match).trim();
        if (!refereeName) {
            setError("Enter referee name before starting match.");
            setMessage("");
            return;
        }

        let latestMatch = match;
        let latestLiveOnCourt = currentLiveOnCourt;
        let earlierUnfinished = (() => {
            const index = courtStageMatches.findIndex((item) => item.id === match.id);
            if (index <= 0) {
                return [];
            }
            return courtStageMatches.slice(0, index).filter((item) => item.status !== "completed");
        })();

        try {
            const latestMatches = await getMatches();
            setMatches(latestMatches);

            const latestOrderedMatches = [...latestMatches].sort(compareMatchOrder);
            const latestCourtMatches = latestOrderedMatches.filter((item) => item.court === match.court);
            latestLiveOnCourt = latestCourtMatches.find((item) => item.status === "live") || null;
            latestMatch =
                latestCourtMatches.find((item) => item.id === match.id) ||
                latestMatches.find((item) => item.id === match.id) ||
                match;

            if (latestMatch.status === "completed") {
                setError("This match is already completed.");
                setMessage("");
                return;
            }

            const freshIndex = latestCourtMatches.findIndex((item) => item.id === match.id);
            if (freshIndex <= 0) {
                earlierUnfinished = [];
            } else {
                earlierUnfinished = latestCourtMatches.slice(0, freshIndex).filter((item) => item.status !== "completed");
            }
        } catch {
            // Continue with local state if sync fails.
        }

        const warnings = [];

        if (latestLiveOnCourt && latestLiveOnCourt.id !== latestMatch.id) {
            warnings.push(
                `Current live match on this court: ${formatMatchLabel(latestLiveOnCourt)}. It will be stopped and can continue later.`
            );
        }

        if (earlierUnfinished.length > 0) {
            warnings.push(`Preferred order warning: ${formatMatchLabel(earlierUnfinished[0])} is still unfinished.`);
        }

        if (warnings.length > 0) {
            const confirmText = `${warnings.join("\n")}\n\nAre you sure you want to start this match now?`;
            if (!window.confirm(confirmText)) {
                return;
            }
        }

        setSubmitting(true);
        setError("");
        setMessage("");

        try {
            if (latestLiveOnCourt && latestLiveOnCourt.id !== latestMatch.id) {
                const stopped = await updateMatchStatus(latestLiveOnCourt.id, "pending");
                upsertMatch(stopped);
            }

            const payload = await assignReferee({
                matchId: latestMatch.id,
                name: refereeName,
            });

            upsertMatch(payload.match);
            setRefereeDrafts((prev) => ({ ...prev, [latestMatch.id]: payload.referee.name }));
            setActiveMatchId(latestMatch.id);
            setScoreDraftDirty(false);
            setLineupDraftDirty(false);
            setStatusFilter("live");
            setMessage(`Match started: ${formatMatchLabel(payload.match)}`);
        } catch (err) {
            setError(err.message || "Failed to start match");
        } finally {
            setSubmitting(false);
        }
    }

    async function handleStopLiveMatch(match) {
        const ok = window.confirm(
            `Stop current live match?\n\n${formatMatchLabel(match)}\n\nYou can continue it later from pending list.`,
        );
        if (!ok) {
            return;
        }

        setSubmitting(true);
        setError("");
        setMessage("");

        try {
            const payload = await updateMatchStatus(match.id, "pending");
            upsertMatch(payload);
            if (activeMatchId === match.id) {
                setActiveMatchId(null);
            }
            setScoreDraftDirty(false);
            setLineupDraftDirty(false);
            setStatusFilter("pending");
            setMessage("Live match stopped. You can continue later.");
        } catch (err) {
            setError(err.message || "Failed to stop match");
        } finally {
            setSubmitting(false);
        }
    }

    async function handleSaveLineup() {
        if (!activeMatch) {
            return;
        }

        setSubmitting(true);
        setError("");
        setMessage("");

        try {
            const payload = await updateLineup(activeMatch.id, normalizedTeam1Lineup, normalizedTeam2Lineup);
            upsertMatch(payload);
            setTeam1LineupInput(payload.team1_lineup);
            setTeam2LineupInput(payload.team2_lineup);
            setLineupDraftDirty(false);
            setMessage("Lineup updated.");
        } catch (err) {
            setError(err.message || "Failed to update lineup");
        } finally {
            setSubmitting(false);
        }
    }

    async function saveScore(nextScore1, nextScore2, { autoComplete = false } = {}) {
        if (!activeMatch) {
            return;
        }

        const scoreTeam1Lineup = lineupForScore(team1LineupInput, requiresStrictLineup);
        const scoreTeam2Lineup = lineupForScore(team2LineupInput, requiresStrictLineup);
        if (!scoreTeam1Lineup || !scoreTeam2Lineup) {
            if (requiresStrictLineup) {
                setError("Enter exactly two player names per team (Player 1 / Player 2) before scoring.");
            } else {
                setError("Confirm player names for both teams before scoring.");
            }
            return;
        }

        setSubmitting(true);
        setError("");
        setMessage("");

        try {
            const persistedTeam1 = normalizeLineup(activeMatch.team1_lineup || "");
            const persistedTeam2 = normalizeLineup(activeMatch.team2_lineup || "");
            const needsLineupSync =
                !lineupConfirmed ||
                lineupDirty ||
                persistedTeam1 !== scoreTeam1Lineup ||
                persistedTeam2 !== scoreTeam2Lineup;

            if (needsLineupSync) {
                const lineupPayload = await updateLineup(activeMatch.id, scoreTeam1Lineup, scoreTeam2Lineup);
                upsertMatch(lineupPayload);
                setTeam1LineupInput(lineupPayload.team1_lineup);
                setTeam2LineupInput(lineupPayload.team2_lineup);
                setLineupDraftDirty(false);
            }

            const payload = await updateScore(activeMatch.id, nextScore1, nextScore2);
            upsertMatch(payload);
            setScore1(payload.team1_score);
            setScore2(payload.team2_score);
            setScoreDraftDirty(false);

            if (payload.status === "completed") {
                setLastCompletedStatus(
                    `Last completed: ${formatMatchLabel(payload)} • ${payload.team1_score}-${payload.team2_score}`,
                );
                setActiveMatchId(null);
                setStatusFilter("pending");
                setMessage(
                    autoComplete
                        ? "Match completed automatically at winning score."
                        : "Match completed. Switched to pending list for next match.",
                );
            } else {
                setStatusFilter("live");
                setMessage("Score updated.");
            }
        } catch (err) {
            setError(err.message || "Failed to update score");
        } finally {
            setSubmitting(false);
        }
    }

    async function handleSaveScore() {
        await saveScore(score1, score2);
    }

    function adjust(team, delta) {
        if (submitting) {
            return;
        }

        let nextScore1 = score1;
        let nextScore2 = score2;

        if (team === 1) {
            const cap = getScoreCap(score1, score2);
            nextScore1 = Math.max(0, Math.min(cap, score1 + delta));
        } else {
            const cap = getScoreCap(score2, score1);
            nextScore2 = Math.max(0, Math.min(cap, score2 + delta));
        }

        if (nextScore1 === score1 && nextScore2 === score2) {
            return;
        }

        setScore1(nextScore1);
        setScore2(nextScore2);
        setScoreDraftDirty(true);

        if (delta > 0 && isWinningScore(nextScore1, nextScore2)) {
            void saveScore(nextScore1, nextScore2, { autoComplete: true });
        }
    }

    if (loading) {
        return <section className="panel">Loading referee console...</section>;
    }

    return (
        <section className="stack-lg">
            <article className="panel" data-animate="true">
                <div className="panel-head">
                    <h3>Referee Queue</h3>
                    <p>Actionable matches segregated by court</p>
                </div>
                <p className={`ref-status-line ${error ? "is-error" : "is-info"}`}>{statusSummary}</p>

                {recommendedNextMatch && <p className="muted-note">Recommended next in order</p>}

                <div className="filters block-gap">
                    {STATUS_FILTERS.map((item) => (
                        <button
                            key={item}
                            className={`chip ${statusFilter === item ? "active" : ""}`}
                            onClick={() => setStatusFilter(item)}
                        >
                            {item}
                        </button>
                    ))}
                </div>

                <div className="filters block-gap">
                    {courtOptions.map((court) => (
                        <button
                            key={court}
                            className={`chip ${selectedCourt === court ? "active" : ""}`}
                            onClick={() => setSelectedCourt(court)}
                        >
                            Court {court}
                        </button>
                    ))}
                </div>

                {currentLiveOnCourt && statusFilter !== "live" && (
                    <div className="lineup-box stack-sm">
                        <p className="match-meta">Current live match on Court {selectedCourt}</p>
                        <h5>
                            {currentLiveOnCourt.team1} vs {currentLiveOnCourt.team2}
                        </h5>
                        <p className="lineup">
                            {currentLiveOnCourt.team1_lineup} <span>vs</span> {currentLiveOnCourt.team2_lineup}
                        </p>
                        <p className="match-meta">
                            Tie {currentLiveOnCourt.tie_no ?? "-"} • #{currentLiveOnCourt.match_no} •{" "}
                            {currentLiveOnCourt.discipline}
                        </p>
                        <div className="input-row">
                            <button className="btn btn-outline" onClick={() => setStatusFilter("live")}>
                                Show Live Match
                            </button>
                            <button
                                className="btn btn-outline"
                                onClick={() => {
                                    setStatusFilter("live");
                                    setActiveMatchId(currentLiveOnCourt.id);
                                    setError("");
                                    setMessage("");
                                }}
                            >
                                Open Scoring
                            </button>
                        </div>
                    </div>
                )}

                <div className="queue stack-sm">
                    {queueMatches.map((match, index) => {
                        const isActive = activeMatchId === match.id;
                        const needsInlineLineup = isActive && match.status === "live";
                        const needsInlineScore = isActive && match.status === "live";

                        return (
                            <div
                                key={match.id}
                                className={`queue-item ${isActive ? "active" : ""}`}
                                style={{ animationDelay: `${Math.min(index * 40, 300)}ms` }}
                            >
                                <div className="stack-sm">
                                    <div className="panel-head">
                                        <div>
                                            <p className="match-meta">
                                                Tie {match.tie_no ?? "-"} • #{match.match_no} • Day {match.day} • Court{" "}
                                                {match.court}
                                            </p>
                                            {recommendedNextMatch?.id === match.id && (
                                                <p className="match-meta">Recommended</p>
                                            )}
                                            <h5>
                                                {match.team1} vs {match.team2}
                                            </h5>
                                            <p className="match-meta">
                                                {match.session} • {match.time}
                                            </p>
                                        </div>
                                        <StatusPill status={match.status} />
                                    </div>

                                    <p className="lineup">
                                        {match.team1_lineup} <span>vs</span> {match.team2_lineup}
                                    </p>

                                    {match.status === "pending" && (
                                        <div className="stack-sm">
                                            <label htmlFor={`ref-name-${match.id}`}>Referee</label>
                                            <div className="input-row">
                                                <input
                                                    id={`ref-name-${match.id}`}
                                                    value={getRefereeDraft(match)}
                                                    onChange={(event) =>
                                                        setRefereeDrafts((prev) => ({
                                                            ...prev,
                                                            [match.id]: event.target.value,
                                                        }))
                                                    }
                                                    placeholder="Enter referee name"
                                                />
                                                <button
                                                    className="btn btn-outline"
                                                    disabled={submitting}
                                                    onClick={() => handleStartMatch(match)}
                                                >
                                                    Start
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {match.status === "live" && (
                                        <div className="input-row">
                                            <button
                                                className="btn btn-outline"
                                                disabled={submitting}
                                                onClick={() => {
                                                    setActiveMatchId(match.id);
                                                    setError("");
                                                    setMessage("");
                                                }}
                                            >
                                                Open Scoring
                                            </button>
                                            <button
                                                className="btn btn-outline"
                                                disabled={submitting}
                                                onClick={() => handleStopLiveMatch(match)}
                                            >
                                                Stop Match
                                            </button>
                                        </div>
                                    )}

                                    {match.status === "completed" && (
                                        <p className="match-meta">
                                            Final score: {match.team1_score} - {match.team2_score}
                                        </p>
                                    )}

                                    {needsInlineScore && (
                                        <div className="stack-md">
                                            <p className="match-meta">
                                                Active referee: {activeMatch?.referee_name || "Not assigned"}
                                            </p>

                                            {needsInlineLineup && (
                                                <div className="stack-sm">
                                                    <p className="match-meta">
                                                        Player names must be confirmed for this match before scoring.
                                                    </p>
                                                    <p className="match-meta">
                                                        Lineup status: {lineupConfirmed ? "Confirmed" : "Pending confirmation"}
                                                    </p>
                                                    <label htmlFor={`lineup-team1-${match.id}`}>{match.team1} lineup</label>
                                                    <input
                                                        id={`lineup-team1-${match.id}`}
                                                        value={team1LineupInput}
                                                        onChange={(event) => {
                                                            setTeam1LineupInput(event.target.value);
                                                            setLineupDraftDirty(true);
                                                        }}
                                                        placeholder={requiresStrictLineup ? "Player 1 / Player 2" : "Enter confirmed player name(s)"}
                                                    />

                                                    <label htmlFor={`lineup-team2-${match.id}`}>{match.team2} lineup</label>
                                                    <input
                                                        id={`lineup-team2-${match.id}`}
                                                        value={team2LineupInput}
                                                        onChange={(event) => {
                                                            setTeam2LineupInput(event.target.value);
                                                            setLineupDraftDirty(true);
                                                        }}
                                                        placeholder={requiresStrictLineup ? "Player 1 / Player 2" : "Enter confirmed player name(s)"}
                                                    />

                                                    <button
                                                        className="btn btn-outline"
                                                        disabled={submitting}
                                                        onClick={handleSaveLineup}
                                                    >
                                                        Save Lineup
                                                    </button>
                                                </div>
                                            )}

                                            <div className="score-grid">
                                                <div className="score-card">
                                                    <h4>{match.team1}</h4>
                                                    <p className="score-value">{score1}</p>
                                                    <div className="score-actions">
                                                        <button onClick={() => adjust(1, -1)}>-</button>
                                                        <button onClick={() => adjust(1, 1)}>+</button>
                                                    </div>
                                                </div>

                                                <div className="score-card">
                                                    <h4>{match.team2}</h4>
                                                    <p className="score-value">{score2}</p>
                                                    <div className="score-actions">
                                                        <button onClick={() => adjust(2, -1)}>-</button>
                                                        <button onClick={() => adjust(2, 1)}>+</button>
                                                    </div>
                                                </div>
                                            </div>

                                            <button
                                                className="btn btn-primary"
                                                disabled={
                                                    submitting ||
                                                    !activeMatch?.referee_name
                                                }
                                                onClick={handleSaveScore}
                                            >
                                                Save Score
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}

                    {queueMatches.length === 0 && (
                        <div className="stack-sm">
                            <p className="muted-note">No matches found for this status/court filter.</p>
                            <div className="filters">
                                {statusFilter !== "pending" && hasPendingOnCourt && (
                                    <button className="chip" onClick={() => setStatusFilter("pending")}>
                                        Show pending
                                    </button>
                                )}
                                {statusFilter !== "live" && hasLiveOnCourt && (
                                    <button className="chip" onClick={() => setStatusFilter("live")}>
                                        Show live
                                    </button>
                                )}
                                {statusFilter !== "completed" && hasCompletedOnCourt && (
                                    <button className="chip" onClick={() => setStatusFilter("completed")}>
                                        Show completed
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {recommendedNextMatch ? (
                    <p className="muted-note">{formatMatchLabel(recommendedNextMatch)}</p>
                ) : (
                    <p className="muted-note">All matches completed for selected court.</p>
                )}

                {error && <p className="error-text">{error}</p>}
                {message && <p className="success-text">{message}</p>}
            </article>
        </section>
    );
}
