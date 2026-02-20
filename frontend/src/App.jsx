import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";

import Home from "./pages/Home";
import Referee from "./pages/Referee";
import Viewer from "./pages/Viewer";

export default function App() {
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
                        <NavLink to="/" end>
                            Home
                        </NavLink>
                        <NavLink to="/viewer">Viewer</NavLink>
                        <NavLink to="/referee">Referee</NavLink>
                    </nav>
                </header>

                <main className="page-body">
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/viewer" element={<Viewer />} />
                        <Route path="/referee" element={<Referee />} />

                        <Route path="/ref" element={<Navigate to="/referee" replace />} />
                        <Route path="/match" element={<Navigate to="/referee" replace />} />
                        <Route path="/schedule" element={<Navigate to="/viewer" replace />} />
                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                </main>
            </div>
        </BrowserRouter>
    );
}
