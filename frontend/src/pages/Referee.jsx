import { useEffect, useMemo, useRef, useState } from "react";

import {
    assignFinalGameReferee,
    assignReferee,
    getMatches,
    getViewerDashboard,
    updateFinalGameScore,
    updateLineup,
    updateMatchStatus,
    updateScore,
} from "../api";

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

function formatTime12Hour(value) {
    if (!value) {
        return "-";
    }

    const text = String(value).trim();
    if (!text.includes(":")) {
        return text;
    }

    const [hourText, minuteText] = text.split(":");
    const hour = Number(hourText);
    const minute = Number(minuteText);
    if (Number.isNaN(hour) || Number.isNaN(minute) || hour < 0 || hour > 23 || minute < 0 || minute > 59) {
        return text;
    }

    const suffix = hour >= 12 ? "PM" : "AM";
    const hour12 = hour % 12 || 12;
    return `${hour12}:${String(minute).padStart(2, "0")} ${suffix}`;
}

function getTieToneClass(tieNo) {
    const value = Number(tieNo);
    if (!Number.isFinite(value) || value <= 0) {
        return "tie-tone-1";
    }
    return `tie-tone-${((Math.trunc(value) - 1) % 6) + 1}`;
}

function medalClassForTeam(teamName, medals) {
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

function medalLabelFromClass(value) {
    if (value === "gold") {
        return "Gold";
    }
    if (value === "silver") {
        return "Silver";
    }
    if (value === "bronze") {
        return "Bronze";
    }
    return "";
}

export default function Referee() {
    const [matches, setMatches] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");
    const [lastCompletedStatus, setLastCompletedStatus] = useState("");
    const [finalMatch, setFinalMatch] = useState(null);
    const [medals, setMedals] = useState({
        finalist1: null,
        finalist2: null,
        gold_team: null,
        silver_team: null,
        bronze_team: null,
    });
    const [finalGameDrafts, setFinalGameDrafts] = useState({});

    const [statusFilter, setStatusFilter] = useState("pending");
    const [selectedCourt, setSelectedCourt] = useState(null);
    const [activeMatchId, setActiveMatchId] = useState(null);

    const [refereeDrafts, setRefereeDrafts] = useState({});
    const [score1, setScore1] = useState(0);
    const [score2, setScore2] = useState(0);
    const [team1LineupInput, setTeam1LineupInput] = useState("");
    const [team2LineupInput, setTeam2LineupInput] = useState("");
    const [pendingLineups, setPendingLineups] = useState({});
    const [pendingLineupReady, setPendingLineupReady] = useState({});
    const [decrementConfirm, setDecrementConfirm] = useState(null);
    const [finalDecrementConfirm, setFinalDecrementConfirm] = useState(null);
    const [tieExpandedByContext, setTieExpandedByContext] = useState({});
    const [submitting, setSubmitting] = useState(false);
    const [scoreDraftDirty, setScoreDraftDirty] = useState(false);
    const [lineupDraftDirty, setLineupDraftDirty] = useState(false);

    const hydratedActiveMatchIdRef = useRef(null);
    const autoFilterInitializedRef = useRef(false);

    function applyDashboardSnapshot(payload) {
        setFinalMatch(payload?.final_match ?? null);
        setMedals(
            payload?.medals ?? {
                finalist1: null,
                finalist2: null,
                gold_team: null,
                silver_team: null,
                bronze_team: null,
            },
        );
        setFinalGameDrafts(() => {
            const drafts = {};
            const games = payload?.final_match?.matches ?? [];
            for (const game of games) {
                drafts[game.id] = {
                    referee: game.referee_name || "",
                    score1: game.team1_score ?? 0,
                    score2: game.team2_score ?? 0,
                };
            }
            return drafts;
        });
    }

    useEffect(() => {
        let mounted = true;

        async function loadMatches() {
            try {
                const [matchesResult, dashboardResult] = await Promise.allSettled([getMatches(), getViewerDashboard()]);
                if (matchesResult.status !== "fulfilled") {
                    throw matchesResult.reason;
                }
                if (!mounted) {
                    return;
                }

                setMatches(matchesResult.value);
                if (dashboardResult.status === "fulfilled") {
                    applyDashboardSnapshot(dashboardResult.value);
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

    useEffect(() => {
        let mounted = true;

        const intervalId = window.setInterval(async () => {
            try {
                const [matchesResult, dashboardResult] = await Promise.allSettled([getMatches(), getViewerDashboard()]);
                if (mounted) {
                    if (matchesResult.status === "fulfilled") {
                        setMatches(matchesResult.value);
                    }
                    if (dashboardResult.status === "fulfilled") {
                        applyDashboardSnapshot(dashboardResult.value);
                    }
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
    const finalGames = useMemo(
        () => (finalMatch?.matches ? [...finalMatch.matches].sort((a, b) => a.match_no - b.match_no) : []),
        [finalMatch],
    );
    const finalGamesCompletedCount = useMemo(
        () => finalGames.filter((game) => game.status === "completed").length,
        [finalGames],
    );
    const finalGamesByStatus = useMemo(
        () => ({
            pending: finalGames.filter((game) => game.status === "pending").length,
            live: finalGames.filter((game) => game.status === "live").length,
            completed: finalGames.filter((game) => game.status === "completed").length,
        }),
        [finalGames],
    );
    const finalGamesForStatus = useMemo(
        () => finalGames.filter((game) => game.status === statusFilter),
        [finalGames, statusFilter],
    );

    const stageStatusMatches = useMemo(() => {
        return courtStageMatches.filter((match) => match.status === statusFilter);
    }, [courtStageMatches, statusFilter]);
    const statusCountsOverall = useMemo(() => {
        const counts = {
            pending: 0,
            live: 0,
            completed: 0,
        };

        for (const match of orderedMatches) {
            if (match.status in counts) {
                counts[match.status] += 1;
            }
        }

        counts.pending += finalGamesByStatus.pending;
        counts.live += finalGamesByStatus.live;
        counts.completed += finalGamesByStatus.completed;

        return counts;
    }, [orderedMatches, finalGamesByStatus]);

    const queueMatches = stageStatusMatches;
    const tieGroups = useMemo(() => {
        const byTie = new Map();
        for (const match of queueMatches) {
            const key = match.tie_no ?? -1;
            if (!byTie.has(key)) {
                byTie.set(key, {
                    tieNo: key,
                    matches: [],
                });
            }
            byTie.get(key).matches.push(match);
        }

        return [...byTie.values()]
            .map((group) => ({
                ...group,
                matches: [...group.matches].sort((a, b) => a.match_no - b.match_no),
            }))
            .sort((a, b) => a.tieNo - b.tieNo);
    }, [queueMatches]);

    const currentLiveOnCourt = useMemo(() => {
        return courtStageMatches.find((match) => match.status === "live") || null;
    }, [courtStageMatches]);
    const liveTieNoOnCourt = currentLiveOnCourt?.tie_no ?? null;

    const recommendedNextMatch = useMemo(() => {
        return courtStageMatches.find((match) => match.status !== "completed") || null;
    }, [courtStageMatches]);
    const lastCompletedOnCourt = useMemo(() => {
        for (let index = courtStageMatches.length - 1; index >= 0; index -= 1) {
            if (courtStageMatches[index].status === "completed") {
                return courtStageMatches[index];
            }
        }
        return null;
    }, [courtStageMatches]);
    const recommendedStartsNewTie = useMemo(() => {
        if (!recommendedNextMatch || !lastCompletedOnCourt) {
            return false;
        }
        return recommendedNextMatch.tie_no !== lastCompletedOnCourt.tie_no;
    }, [recommendedNextMatch, lastCompletedOnCourt]);
    const tieProgressByNo = useMemo(() => {
        const byTie = new Map();
        for (const match of courtStageMatches) {
            const key = match.tie_no ?? -1;
            if (!byTie.has(key)) {
                byTie.set(key, { total: 0, completed: 0 });
            }
            const row = byTie.get(key);
            row.total += 1;
            if (match.status === "completed") {
                row.completed += 1;
            }
        }
        return byTie;
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
        if (selectedCourt == null) {
            return;
        }

        // Set default tab once on initial load: prefer live queue when a live match exists.
        if (autoFilterInitializedRef.current) {
            return;
        }

        autoFilterInitializedRef.current = true;
        if (statusFilter === "completed") {
            return;
        }
        setStatusFilter(hasLiveOnCourt ? "live" : "pending");
    }, [selectedCourt, hasLiveOnCourt, statusFilter]);

    useEffect(() => {
        setPendingLineupReady((prev) => {
            const next = {};
            for (const match of matches) {
                if (match.status === "pending" && prev[match.id]) {
                    next[match.id] = true;
                }
            }
            return next;
        });
    }, [matches]);

    const tieExpansionContextKey = `${selectedCourt ?? "none"}:${statusFilter}`;
    const preferredExpandedTieNo = useMemo(() => {
        if (tieGroups.length === 0) {
            return null;
        }

        const visibleTieNos = new Set(tieGroups.map((group) => String(group.tieNo ?? -1)));
        const hasVisibleTie = (tieNo) => tieNo != null && visibleTieNos.has(String(tieNo));
        const firstIncompleteTie = tieGroups.find((group) => {
            const progress = tieProgressByNo.get(group.tieNo ?? -1);
            const completed = progress?.completed ?? 0;
            const total = progress?.total ?? group.matches.length;
            return completed < total;
        });

        if (statusFilter === "live") {
            if (hasVisibleTie(liveTieNoOnCourt)) {
                return liveTieNoOnCourt;
            }
            return tieGroups[0].tieNo;
        }

        if (statusFilter === "pending") {
            if (hasVisibleTie(liveTieNoOnCourt)) {
                return liveTieNoOnCourt;
            }
            if (firstIncompleteTie) {
                return firstIncompleteTie.tieNo;
            }
            return tieGroups[0].tieNo;
        }

        if (firstIncompleteTie) {
            return firstIncompleteTie.tieNo;
        }
        if (hasVisibleTie(liveTieNoOnCourt)) {
            return liveTieNoOnCourt;
        }
        return tieGroups[0].tieNo;
    }, [statusFilter, tieGroups, tieProgressByNo, liveTieNoOnCourt]);

    useEffect(() => {
        if (selectedCourt == null || tieGroups.length === 0) {
            return;
        }

        const preferredKey = preferredExpandedTieNo == null ? null : String(preferredExpandedTieNo);
        if (preferredKey == null) {
            return;
        }

        setTieExpandedByContext((prev) => {
            const visibleTieKeys = new Set(tieGroups.map((group) => String(group.tieNo ?? -1)));
            const hasStoredContext = Object.prototype.hasOwnProperty.call(prev, tieExpansionContextKey);
            const existingKey = hasStoredContext ? prev[tieExpansionContextKey] : undefined;

            if (!hasStoredContext) {
                return { ...prev, [tieExpansionContextKey]: preferredKey };
            }

            // User explicitly collapsed this context. Keep it collapsed until user expands.
            if (existingKey == null) {
                return prev;
            }

            const existingVisible = visibleTieKeys.has(existingKey);

            if (!existingVisible) {
                if (existingKey === preferredKey) {
                    return prev;
                }
                return { ...prev, [tieExpansionContextKey]: preferredKey };
            }

            const currentTieNo = Number(existingKey);
            const currentProgress = tieProgressByNo.get(Number.isFinite(currentTieNo) ? currentTieNo : -1);
            const currentCompleted = currentProgress?.completed ?? 0;
            const currentTotal = currentProgress?.total ?? 0;
            const currentTieCompleted = currentTotal > 0 && currentCompleted >= currentTotal;

            const shouldForceLiveTie =
                (statusFilter === "live" || statusFilter === "pending") &&
                liveTieNoOnCourt != null &&
                preferredKey !== existingKey;
            const shouldForceCompletedAdvance =
                statusFilter === "completed" && currentTieCompleted && preferredKey !== existingKey;

            if (shouldForceLiveTie || shouldForceCompletedAdvance) {
                return { ...prev, [tieExpansionContextKey]: preferredKey };
            }

            return prev;
        });
    }, [
        selectedCourt,
        tieGroups,
        tieExpansionContextKey,
        preferredExpandedTieNo,
        tieProgressByNo,
        statusFilter,
        liveTieNoOnCourt,
    ]);

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

    function getPendingLineupDraft(match, side) {
        const saved = pendingLineups[match.id];
        if (saved) {
            return side === 1 ? saved.team1 : saved.team2;
        }
        return side === 1 ? match.team1_lineup || "" : match.team2_lineup || "";
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

    async function refreshFinalDashboard() {
        try {
            const payload = await getViewerDashboard();
            applyDashboardSnapshot(payload);
        } catch {
            // Silent refresh failure: existing state is still usable.
        }
    }

    function getFinalGameDraft(game) {
        const saved = finalGameDrafts[game.id];
        if (saved) {
            return saved;
        }
        return {
            referee: game.referee_name || "",
            score1: game.team1_score ?? 0,
            score2: game.team2_score ?? 0,
        };
    }

    async function handleAssignFinalGameReferee(game) {
        const draft = getFinalGameDraft(game);
        const name = String(draft.referee || "").trim();
        if (!name) {
            setError(`Enter referee name before starting final game ${game.match_no}.`);
            setMessage("");
            return;
        }

        setSubmitting(true);
        setError("");
        setMessage("");

        try {
            const payload = await assignFinalGameReferee(game.id, name);
            setFinalMatch(payload);
            setMessage(`Final game ${game.match_no} referee assigned: ${name}`);
            await refreshFinalDashboard();
        } catch (err) {
            setError(err.message || "Failed to assign final game referee");
        } finally {
            setSubmitting(false);
        }
    }

    async function handleSaveFinalGameScore(game, providedScores = null, { autoTriggered = false } = {}) {
        const draft = getFinalGameDraft(game);
        const nextScore1 = Number(providedScores?.score1 ?? draft.score1);
        const nextScore2 = Number(providedScores?.score2 ?? draft.score2);
        if (!Number.isFinite(nextScore1) || !Number.isFinite(nextScore2)) {
            setError(`Enter valid numeric scores for final game ${game.match_no}.`);
            setMessage("");
            return;
        }

        const boundedScore1 = Math.max(0, Math.min(30, Math.trunc(nextScore1)));
        const boundedScore2 = Math.max(0, Math.min(30, Math.trunc(nextScore2)));

        setSubmitting(true);
        setError("");
        setMessage("");

        try {
            const payload = await updateFinalGameScore(game.id, boundedScore1, boundedScore2);
            setFinalMatch(payload);
            if (payload.status === "completed") {
                setMessage(`Final tie completed: ${payload.team1} ${payload.team1_score} - ${payload.team2_score} ${payload.team2}.`);
            } else if (!autoTriggered) {
                setMessage(`Final game ${game.match_no} score updated.`);
            }
            await refreshFinalDashboard();
        } catch (err) {
            setError(err.message || "Failed to update final game score");
        } finally {
            setSubmitting(false);
        }
    }

    function applyFinalScoreDelta(game, team, delta) {
        if (submitting) {
            return;
        }

        const draft = getFinalGameDraft(game);
        const currentScore1 = Math.max(0, Math.min(30, Number(draft.score1) || 0));
        const currentScore2 = Math.max(0, Math.min(30, Number(draft.score2) || 0));

        let nextScore1 = currentScore1;
        let nextScore2 = currentScore2;

        if (team === 1) {
            const cap = getScoreCap(currentScore1, currentScore2);
            nextScore1 = Math.max(0, Math.min(cap, currentScore1 + delta));
        } else {
            const cap = getScoreCap(currentScore2, currentScore1);
            nextScore2 = Math.max(0, Math.min(cap, currentScore2 + delta));
        }

        if (nextScore1 === currentScore1 && nextScore2 === currentScore2) {
            return;
        }

        setFinalGameDrafts((prev) => ({
            ...prev,
            [game.id]: {
                referee: prev[game.id]?.referee ?? game.referee_name ?? "",
                score1: nextScore1,
                score2: nextScore2,
            },
        }));
        void handleSaveFinalGameScore(
            game,
            {
                score1: nextScore1,
                score2: nextScore2,
            },
            { autoTriggered: true },
        );
    }

    function adjustFinalScore(game, team, delta) {
        if (delta < 0) {
            const draft = getFinalGameDraft(game);
            const from = team === 1 ? Number(draft.score1) || 0 : Number(draft.score2) || 0;
            if (from > 0) {
                setFinalDecrementConfirm({
                    gameId: game.id,
                    gameNo: game.match_no,
                    team,
                    from,
                    to: Math.max(0, from + delta),
                });
                return;
            }
        }

        applyFinalScoreDelta(game, team, delta);
    }

    function closeFinalDecrementModal() {
        setFinalDecrementConfirm(null);
    }

    function confirmFinalDecrement() {
        if (!finalDecrementConfirm) {
            return;
        }

        const game = finalGames.find((item) => item.id === finalDecrementConfirm.gameId);
        if (!game) {
            setFinalDecrementConfirm(null);
            return;
        }

        const { team } = finalDecrementConfirm;
        setFinalDecrementConfirm(null);
        applyFinalScoreDelta(game, team, -1);
    }

    async function handleStartMatch(match) {
        const refereeName = getRefereeDraft(match).trim();
        if (!refereeName) {
            setError("Enter referee name before starting match.");
            setMessage("");
            return;
        }
        if (!pendingLineupReady[match.id]) {
            setError("Update player names for both teams before starting match.");
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
            setPendingLineupReady((prev) => {
                const next = { ...prev };
                delete next[latestMatch.id];
                return next;
            });
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
            setPendingLineupReady((prev) => {
                const next = { ...prev };
                delete next[match.id];
                return next;
            });
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

    async function handlePendingLineupUpdate(match) {
        const team1 = normalizeLineup(getPendingLineupDraft(match, 1));
        const team2 = normalizeLineup(getPendingLineupDraft(match, 2));

        if (!team1 || !team2) {
            setError("Enter player names for both teams before updating.");
            setMessage("");
            return;
        }

        setSubmitting(true);
        setError("");
        setMessage("");

        try {
            const payload = await updateLineup(match.id, team1, team2);
            upsertMatch(payload);
            setPendingLineups((prev) => ({
                ...prev,
                [match.id]: {
                    team1: payload.team1_lineup,
                    team2: payload.team2_lineup,
                },
            }));
            setPendingLineupReady((prev) => ({ ...prev, [match.id]: true }));
            setMessage("Players updated. You can start match.");
        } catch (err) {
            setError(err.message || "Failed to update players");
            setPendingLineupReady((prev) => ({ ...prev, [match.id]: false }));
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
                setStatusFilter("completed");
                setMessage(
                    autoComplete
                        ? "Match completed automatically at winning score."
                        : "Match completed. Switched to completed list.",
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

    function applyScoreDelta(team, delta) {
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
        setScoreDraftDirty(false);
        void saveScore(nextScore1, nextScore2, { autoComplete: isWinningScore(nextScore1, nextScore2) });
    }

    function adjust(team, delta) {
        if (delta < 0) {
            const from = team === 1 ? score1 : score2;
            if (from > 0) {
                setDecrementConfirm({
                    team,
                    delta,
                    from,
                    to: Math.max(0, from + delta),
                });
                return;
            }
        }

        applyScoreDelta(team, delta);
    }

    function closeDecrementModal() {
        setDecrementConfirm(null);
    }

    function confirmDecrement() {
        if (!decrementConfirm) {
            return;
        }
        const { team, delta } = decrementConfirm;
        setDecrementConfirm(null);
        applyScoreDelta(team, delta);
    }

    function expandTieForCurrentView(tieNo) {
        const tieKey = String(tieNo ?? -1);
        setTieExpandedByContext((prev) => {
            const hasStoredContext = Object.prototype.hasOwnProperty.call(prev, tieExpansionContextKey);
            const currentExpandedKey = hasStoredContext
                ? prev[tieExpansionContextKey]
                : preferredExpandedTieNo == null
                  ? null
                  : String(preferredExpandedTieNo);

            if (currentExpandedKey === tieKey) {
                return { ...prev, [tieExpansionContextKey]: null };
            }
            return { ...prev, [tieExpansionContextKey]: tieKey };
        });
    }

    const decrementTeamName =
        decrementConfirm?.team === 1
            ? activeMatch?.team1 || "Team 1"
            : decrementConfirm?.team === 2
              ? activeMatch?.team2 || "Team 2"
              : "Team";
    const finalDecrementTeamName =
        finalDecrementConfirm?.team === 1
            ? finalMatch?.team1 || "Team 1"
            : finalDecrementConfirm?.team === 2
              ? finalMatch?.team2 || "Team 2"
              : "Team";
    const hasStoredExpandedTie = Object.prototype.hasOwnProperty.call(tieExpandedByContext, tieExpansionContextKey);
    const expandedTieKey = hasStoredExpandedTie
        ? tieExpandedByContext[tieExpansionContextKey]
        : preferredExpandedTieNo == null
          ? null
          : String(preferredExpandedTieNo);

    if (loading) {
        return <section className="panel">Loading referee console...</section>;
    }

    return (
        <section className="stack-lg">
            <article className="panel" data-animate="true">
                <div className="panel-head">
                    <h3>Referee Queue</h3>
                    <p>Actionable matches by court, with finals in same tabs</p>
                </div>
                <p className={`ref-status-line ${error ? "is-error" : "is-info"}`}>{statusSummary}</p>

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

                {recommendedNextMatch && (
                    <div className={`recommended-banner ${getTieToneClass(recommendedNextMatch.tie_no)} ${recommendedStartsNewTie ? "is-new-tie" : ""}`}>
                        <p className="match-meta">Recommended next in order</p>
                        <p>
                            <strong>
                                Tie {recommendedNextMatch.tie_no} • #{recommendedNextMatch.match_no}
                            </strong>{" "}
                            • {recommendedNextMatch.team1} vs {recommendedNextMatch.team2}
                        </p>
                        {recommendedStartsNewTie && (
                            <p className="match-meta">
                                New tie starts now. Previous completed tie on this court: Tie {lastCompletedOnCourt?.tie_no}.
                            </p>
                        )}
                    </div>
                )}

                <div className="filters block-gap">
                    {STATUS_FILTERS.map((item) => (
                        <button
                            key={item}
                            className={`chip ${statusFilter === item ? "active" : ""}`}
                            onClick={() => setStatusFilter(item)}
                        >
                            {item} ({statusCountsOverall[item] ?? 0})
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
                    {tieGroups.map((group, groupIndex) => {
                        const progress = tieProgressByNo.get(group.tieNo ?? -1);
                        const completed = progress?.completed ?? 0;
                        const total = progress?.total ?? group.matches.length;
                        const tieKey = String(group.tieNo ?? -1);
                        const isExpanded = expandedTieKey === tieKey;
                        const tieRepresentativeMatch = group.matches[0] || null;
                        const tieTeamsLabel = tieRepresentativeMatch
                            ? `${tieRepresentativeMatch.team1} vs ${tieRepresentativeMatch.team2}`
                            : "Teams TBD";

                        return (
                            <section key={`tie-${statusFilter}-${tieKey}`} className={`tie-accordion ${getTieToneClass(group.tieNo)}`}>
                                <button
                                    className={`tie-accordion-head ${isExpanded ? "expanded" : ""}`}
                                    onClick={() => expandTieForCurrentView(group.tieNo)}
                                >
                                    <span className="tie-accordion-title">
                                        Tie {group.tieNo} • {tieTeamsLabel}
                                    </span>
                                    <span className="tie-accordion-meta">
                                        {completed}/{total} completed
                                    </span>
                                    <span className="tie-accordion-arrow">{isExpanded ? "−" : "+"}</span>
                                </button>

                                {isExpanded && (
                                    <div className="tie-accordion-body stack-sm">
                                        {group.matches.map((match, index) => {
                                            const isActive = activeMatchId === match.id;
                                            const needsInlineLineup = isActive && match.status === "live";
                                            const needsInlineScore = isActive && match.status === "live";
                                            const isRecommended = recommendedNextMatch?.id === match.id;
                                            const showLineupPreview = match.status === "live" || isActive;

                                            return (
                                                <div
                                                    key={match.id}
                                                    className={`queue-item ${isActive ? "active" : ""} ${getTieToneClass(match.tie_no)} ${isRecommended ? "is-recommended" : ""}`}
                                                    style={{ animationDelay: `${Math.min((groupIndex * 4 + index) * 35, 300)}ms` }}
                                                >
                                                    <div className="stack-sm">
                                                        <div className="panel-head">
                                                            <div>
                                                                <div className="match-topline">
                                                                    <p className="match-meta">
                                                                        Match #{match.match_no} • {match.discipline}
                                                                    </p>
                                                                </div>
                                                                <h5>
                                                                    {match.team1} vs {match.team2}
                                                                </h5>
                                                                <p className="match-meta">
                                                                    Day {match.day} • {match.session} • {formatTime12Hour(match.time)}
                                                                </p>
                                                            </div>
                                                            <StatusPill status={match.status} />
                                                        </div>

                                                        {showLineupPreview && (
                                                            <p className="lineup">
                                                                {match.team1_lineup} <span>vs</span> {match.team2_lineup}
                                                            </p>
                                                        )}

                                                        {match.status === "pending" && (
                                                            <div className="stack-sm">
                                                                <div className="pending-lineup-grid">
                                                                    <div className="stack-sm">
                                                                        <label htmlFor={`pending-lineup-team1-${match.id}`}>{match.team1} players</label>
                                                                        <input
                                                                            id={`pending-lineup-team1-${match.id}`}
                                                                            value={getPendingLineupDraft(match, 1)}
                                                                            onChange={(event) => {
                                                                                const value = event.target.value;
                                                                                setPendingLineups((prev) => ({
                                                                                    ...prev,
                                                                                    [match.id]: {
                                                                                        team1: value,
                                                                                        team2: prev[match.id]?.team2 ?? match.team2_lineup ?? "",
                                                                                    },
                                                                                }));
                                                                                setPendingLineupReady((prev) => ({ ...prev, [match.id]: false }));
                                                                            }}
                                                                            placeholder="Player 1 / Player 2"
                                                                        />
                                                                    </div>

                                                                    <div className="stack-sm">
                                                                        <label htmlFor={`pending-lineup-team2-${match.id}`}>{match.team2} players</label>
                                                                        <input
                                                                            id={`pending-lineup-team2-${match.id}`}
                                                                            value={getPendingLineupDraft(match, 2)}
                                                                            onChange={(event) => {
                                                                                const value = event.target.value;
                                                                                setPendingLineups((prev) => ({
                                                                                    ...prev,
                                                                                    [match.id]: {
                                                                                        team1: prev[match.id]?.team1 ?? match.team1_lineup ?? "",
                                                                                        team2: value,
                                                                                    },
                                                                                }));
                                                                                setPendingLineupReady((prev) => ({ ...prev, [match.id]: false }));
                                                                            }}
                                                                            placeholder="Player 1 / Player 2"
                                                                        />
                                                                    </div>
                                                                </div>

                                                                <div className="input-row">
                                                                    <button
                                                                        className="btn btn-outline"
                                                                        disabled={submitting}
                                                                        onClick={() => handlePendingLineupUpdate(match)}
                                                                    >
                                                                        Update Players
                                                                    </button>
                                                                    <span
                                                                        className={`pending-lineup-state ${pendingLineupReady[match.id] ? "ready" : "pending"}`}
                                                                    >
                                                                        {pendingLineupReady[match.id]
                                                                            ? "Players Updated"
                                                                            : "Update players required"}
                                                                    </span>
                                                                </div>

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
                                                                        disabled={submitting || !pendingLineupReady[match.id]}
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
                                                                            placeholder={
                                                                                requiresStrictLineup
                                                                                    ? "Player 1 / Player 2"
                                                                                    : "Enter confirmed player name(s)"
                                                                            }
                                                                        />

                                                                        <label htmlFor={`lineup-team2-${match.id}`}>{match.team2} lineup</label>
                                                                        <input
                                                                            id={`lineup-team2-${match.id}`}
                                                                            value={team2LineupInput}
                                                                            onChange={(event) => {
                                                                                setTeam2LineupInput(event.target.value);
                                                                                setLineupDraftDirty(true);
                                                                            }}
                                                                            placeholder={
                                                                                requiresStrictLineup
                                                                                    ? "Player 1 / Player 2"
                                                                                    : "Enter confirmed player name(s)"
                                                                            }
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
                                                                    disabled={submitting || !activeMatch?.referee_name}
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
                                    </div>
                                )}
                            </section>
                        );
                    })}

                    {finalMatch && finalGamesForStatus.length > 0 && (
                        <section className="tie-accordion tie-tone-6">
                            <div className="tie-accordion-head expanded">
                                <span className="tie-accordion-title">
                                    Final Tie • {finalMatch.team1} vs {finalMatch.team2}
                                </span>
                                <span className="tie-accordion-meta">
                                    {finalGamesCompletedCount}/{finalGames.length || 12} completed
                                </span>
                                <span className="tie-accordion-arrow">•</span>
                            </div>

                            <div className="tie-accordion-body stack-sm">
                                <p className="match-meta">
                                    Status: {finalMatch.status} • Score: {finalMatch.team1_score} - {finalMatch.team2_score}
                                </p>
                                <p className="match-meta">
                                    {finalMatch.team1}
                                    {medalClassForTeam(finalMatch.team1, medals) ? (
                                        <span className={`standing-badge ${medalClassForTeam(finalMatch.team1, medals)}`}>
                                            {medalLabelFromClass(medalClassForTeam(finalMatch.team1, medals))}
                                        </span>
                                    ) : null}
                                    {" vs "}
                                    {finalMatch.team2}
                                    {medalClassForTeam(finalMatch.team2, medals) ? (
                                        <span className={`standing-badge ${medalClassForTeam(finalMatch.team2, medals)}`}>
                                            {medalLabelFromClass(medalClassForTeam(finalMatch.team2, medals))}
                                        </span>
                                    ) : null}
                                    {medals.bronze_team ? (
                                        <>
                                            {" • "}
                                            Bronze: {medals.bronze_team}
                                            <span className="standing-badge bronze">Bronze</span>
                                        </>
                                    ) : null}
                                </p>

                                {finalGamesForStatus.map((game) => {
                                    const draft = getFinalGameDraft(game);
                                    const finalScore1 = Math.max(0, Math.min(30, Number(draft.score1) || 0));
                                    const finalScore2 = Math.max(0, Math.min(30, Number(draft.score2) || 0));
                                    const canEditFinalScore =
                                        finalMatch.status !== "completed" && game.status !== "completed" && Boolean(game.referee_name);

                                    return (
                                        <div key={`final-${game.id}`} className={`queue-item ${game.status === "completed" ? "tie-tone-2" : "tie-tone-6"}`}>
                                            <div className="stack-sm">
                                                <div className="panel-head">
                                                    <div>
                                                        <p className="match-meta">
                                                            Final Game #{game.match_no} • {game.discipline}
                                                        </p>
                                                        <h5>
                                                            {finalMatch.team1} vs {finalMatch.team2}
                                                        </h5>
                                                    </div>
                                                    <StatusPill status={game.status} />
                                                </div>

                                                <p className="lineup">
                                                    {game.team1_lineup} <span>vs</span> {game.team2_lineup}
                                                </p>
                                                <p className="match-meta">
                                                    Referee: {game.referee_name || "Not assigned"} • Score: {game.team1_score} - {game.team2_score}
                                                </p>

                                                {finalMatch.status !== "completed" && game.status !== "completed" && !game.referee_name && (
                                                    <div className="stack-sm">
                                                        <label htmlFor={`final-referee-${game.id}`}>Game referee</label>
                                                        <div className="input-row">
                                                            <input
                                                                id={`final-referee-${game.id}`}
                                                                value={draft.referee}
                                                                onChange={(event) =>
                                                                    setFinalGameDrafts((prev) => ({
                                                                        ...prev,
                                                                        [game.id]: {
                                                                            referee: event.target.value,
                                                                            score1: prev[game.id]?.score1 ?? game.team1_score ?? 0,
                                                                            score2: prev[game.id]?.score2 ?? game.team2_score ?? 0,
                                                                        },
                                                                    }))
                                                                }
                                                                placeholder="Enter referee name"
                                                            />
                                                            <button
                                                                className="btn btn-outline"
                                                                disabled={submitting}
                                                                onClick={() => handleAssignFinalGameReferee(game)}
                                                            >
                                                                Assign
                                                            </button>
                                                        </div>
                                                    </div>
                                                )}

                                                {canEditFinalScore && (
                                                    <div className="stack-md">
                                                        <div className="score-grid">
                                                            <div className="score-card">
                                                                <h4>{finalMatch.team1}</h4>
                                                                <p className="score-value">{finalScore1}</p>
                                                                <div className="score-actions">
                                                                    <button onClick={() => adjustFinalScore(game, 1, -1)}>-</button>
                                                                    <button onClick={() => adjustFinalScore(game, 1, 1)}>+</button>
                                                                </div>
                                                            </div>

                                                            <div className="score-card">
                                                                <h4>{finalMatch.team2}</h4>
                                                                <p className="score-value">{finalScore2}</p>
                                                                <div className="score-actions">
                                                                    <button onClick={() => adjustFinalScore(game, 2, -1)}>-</button>
                                                                    <button onClick={() => adjustFinalScore(game, 2, 1)}>+</button>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <button
                                                            className="btn btn-primary"
                                                            disabled={submitting}
                                                            onClick={() => handleSaveFinalGameScore(game)}
                                                        >
                                                            Save Score
                                                        </button>
                                                    </div>
                                                )}

                                                {game.status === "completed" && (
                                                    <p className="match-meta">
                                                        Final score: {game.team1_score} - {game.team2_score}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </section>
                    )}

                    {queueMatches.length === 0 && finalGamesForStatus.length === 0 && (
                        <div className="stack-sm">
                            <p className="muted-note">No matches found for this status/court filter.</p>
                            <div className="filters">
                                {statusFilter !== "pending" && (statusCountsOverall.pending ?? 0) > 0 && (
                                    <button className="chip" onClick={() => setStatusFilter("pending")}>
                                        Show pending
                                    </button>
                                )}
                                {statusFilter !== "live" && (statusCountsOverall.live ?? 0) > 0 && (
                                    <button className="chip" onClick={() => setStatusFilter("live")}>
                                        Show live
                                    </button>
                                )}
                                {statusFilter !== "completed" && (statusCountsOverall.completed ?? 0) > 0 && (
                                    <button className="chip" onClick={() => setStatusFilter("completed")}>
                                        Show completed
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {recommendedNextMatch || finalGamesForStatus.length > 0 ? null : (
                    <p className="muted-note">All matches completed for selected court.</p>
                )}

                {error && <p className="error-text">{error}</p>}
                {message && <p className="success-text">{message}</p>}
            </article>

            {decrementConfirm && (
                <div className="modal-backdrop" onClick={closeDecrementModal}>
                    <div
                        className="confirm-modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="decrement-score-title"
                        onClick={(event) => event.stopPropagation()}
                    >
                        <p className="eyebrow">Confirm Score Change</p>
                        <h4 id="decrement-score-title">Reduce score?</h4>
                        <p>
                            Are you sure you want to reduce score from <strong>{decrementConfirm.from}</strong> to{" "}
                            <strong>{decrementConfirm.to}</strong> for <strong>{decrementTeamName}</strong>?
                        </p>
                        <p className="muted-note">This updates the live score immediately.</p>
                        <div className="modal-actions">
                            <button className="btn btn-outline" disabled={submitting} onClick={closeDecrementModal}>
                                Cancel
                            </button>
                            <button className="btn btn-primary" disabled={submitting} onClick={confirmDecrement}>
                                Yes, Reduce
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {finalDecrementConfirm && (
                <div className="modal-backdrop" onClick={closeFinalDecrementModal}>
                    <div
                        className="confirm-modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="decrement-final-score-title"
                        onClick={(event) => event.stopPropagation()}
                    >
                        <p className="eyebrow">Confirm Score Change</p>
                        <h4 id="decrement-final-score-title">Reduce final game score?</h4>
                        <p>
                            Are you sure you want to reduce score from <strong>{finalDecrementConfirm.from}</strong> to{" "}
                            <strong>{finalDecrementConfirm.to}</strong> for <strong>{finalDecrementTeamName}</strong> in Final Game{" "}
                            <strong>#{finalDecrementConfirm.gameNo}</strong>?
                        </p>
                        <p className="muted-note">This updates the live final score immediately.</p>
                        <div className="modal-actions">
                            <button className="btn btn-outline" disabled={submitting} onClick={closeFinalDecrementModal}>
                                Cancel
                            </button>
                            <button className="btn btn-primary" disabled={submitting} onClick={confirmFinalDecrement}>
                                Yes, Reduce
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </section>
    );
}
