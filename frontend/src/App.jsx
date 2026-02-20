import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";

import Home from "./pages/Home";
import PostFinals from "./pages/PostFinals";
import Referee from "./pages/Referee";
import Viewer from "./pages/Viewer";

const ROUTE_PREFIX = "/referee_b7g";

function withPrefix(path) {
    if (!path.startsWith("/")) {
        return `${ROUTE_PREFIX}/${path}`;
    }
    if (path === "/") {
        return ROUTE_PREFIX;
    }
    return `${ROUTE_PREFIX}${path}`;
}

export default function App() {
    const usePrefixedRoutes = window.location.pathname.startsWith(ROUTE_PREFIX);
    const toPath = (path) => (usePrefixedRoutes ? withPrefix(path) : path);
    const navItems = usePrefixedRoutes
        ? [
            { to: "/", label: "Home", end: true },
            { to: "/viewer", label: "Viewer" },
            { to: "/referee", label: "Referee" },

        ]
        : [
            { to: "/", label: "Home", end: true },
            { to: "/viewer", label: "Viewer" },
        ];

    return (
        <BrowserRouter>
            <div className="shell">
                <header className="topbar" data-animate="true">
                    <div className="brand">
                        <span className="brand-mark">B7G</span>
                        <div>
                            <h1>Badminton League Console (UI v2)</h1>
                            <p>Round-robin ties</p>
                        </div>
                    </div>

                    <nav className="menu">
                        {navItems.map((item) => (
                            <NavLink key={item.label} to={toPath(item.to)} end={item.end}>
                                {item.label}
                            </NavLink>
                        ))}
                    </nav>
                </header>

                <main className="page-body">
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/viewer" element={<Viewer />} />
                        <Route path="/post-finals" element={<PostFinals />} />
                        <Route path="/referee" element={<Referee />} />
                        <Route path={ROUTE_PREFIX} element={<Home />} />
                        <Route path={`${ROUTE_PREFIX}/viewer`} element={<Viewer />} />
                        <Route path={`${ROUTE_PREFIX}/post-finals`} element={<PostFinals />} />
                        <Route path={`${ROUTE_PREFIX}/referee`} element={<Referee />} />

                        <Route path="/ref" element={<Navigate to="/referee" replace />} />
                        <Route path="/match" element={<Navigate to="/referee" replace />} />
                        <Route path="/schedule" element={<Navigate to="/viewer" replace />} />
                        <Route path={`${ROUTE_PREFIX}/ref`} element={<Navigate to={`${ROUTE_PREFIX}/referee`} replace />} />
                        <Route path={`${ROUTE_PREFIX}/match`} element={<Navigate to={`${ROUTE_PREFIX}/referee`} replace />} />
                        <Route path={`${ROUTE_PREFIX}/schedule`} element={<Navigate to={`${ROUTE_PREFIX}/viewer`} replace />} />
                        <Route path={`${ROUTE_PREFIX}/*`} element={<Navigate to={ROUTE_PREFIX} replace />} />
                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                </main>
            </div>
        </BrowserRouter>
    );
}
