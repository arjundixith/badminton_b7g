import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Match from "./pages/Match";
import Referee from "./pages/Referee";
import Schedule from "./pages/Schedule";


export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/match" element={<Match />} />
                <Route path="/ref" element={<Referee />} />
                <Route path="/schedule" element={<Schedule />} />

            </Routes>
        </BrowserRouter>
    );
}
