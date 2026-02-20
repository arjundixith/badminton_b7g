import { useEffect, useState } from "react";

import { getTeams } from "../api";

export default function Home() {
    const [teams, setTeams] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let mounted = true;

        async function loadTeams() {
            try {
                const payload = await getTeams();
                if (mounted) {
                    setTeams(payload);
                }
            } catch (err) {
                if (mounted) {
                    setError(err.message || "Failed to load teams");
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        }

        loadTeams();

        return () => {
            mounted = false;
        };
    }, []);

    return (
        <div style={{ padding: 16 }}>
            <h1>Teams</h1>

            {loading && <p>Loading teams...</p>}
            {!loading && error && <p style={{ color: "#b91c1c" }}>{error}</p>}

            {!loading && !error && teams.length === 0 && <p>No teams available.</p>}

            {!loading && !error && teams.map((team) => <div key={team.id}>{team.name}</div>)}
        </div>
    );
}
