const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

export const CONFIG = {
    BACKEND_URL: isLocal ? 'http://localhost:8000' : 'https://flipgame-production.up.railway.app',
    WS_URL: isLocal ? 'ws://localhost:8000' : 'wss://flipgame-production.up.railway.app',
    PYTHON_API: isLocal ? 'http://localhost:8000/api/v1' : 'https://flipgame-production.up.railway.app/api/v1',
};
