import { CONFIG } from '../config.js';
const ML_URL = `${CONFIG.PYTHON_API}/ml`;
export const predictDifficulty = async (stats) => {
    try {
        const res = await fetch(`${ML_URL}/predict-difficulty`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(stats)
        });
        return await res.json();
    } catch(e) { console.error("ML Error", e); return null; }
};

export const classifySkill = async (gameResult) => {
    try {
        const res = await fetch(`${ML_URL}/classify-skill`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(gameResult)
        });
        return await res.json();
    } catch(e) { console.error("ML Error", e); return null; }
};

export const predictScore = async (req) => {
    try {
        const res = await fetch(`${ML_URL}/predict-score`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req)
        });
        return await res.json();
    } catch(e) { console.error("ML Error", e); return null; }
};

export const detectCheat = async (gameResult) => {
    try {
        const res = await fetch(`${ML_URL}/detect-cheat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(gameResult)
        });
        return await res.json();
    } catch(e) { console.error("ML Error", e); return null; }
};

export const recommendTheme = async (req) => {
    try {
        const res = await fetch(`${ML_URL}/recommend-theme`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req)
        });
        return await res.json();
    } catch(e) { console.error("ML Error", e); return null; }
};
