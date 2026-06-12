/* ═══════════════════════════════════════════════════════════════════
   API Layer — Communication with backend
   ═══════════════════════════════════════════════════════════════════ */

const API_BASE = '/api';

/**
 * Make an API request
 * @param {string} endpoint - API endpoint path
 * @param {string} method - HTTP method
 * @param {object|null} body - Request body (auto-adds user_id)
 * @returns {Promise<object|null>} JSON response or null on error
 */
async function api(endpoint, method = 'GET', body = null) {
    try {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };

        if (body) {
            opts.body = JSON.stringify({ ...body, user_id: App.userId });
        }

        const url = method === 'GET'
            ? `${API_BASE}${endpoint}?user_id=${App.userId}`
            : `${API_BASE}${endpoint}`;

        const res = await fetch(url, opts);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error(`[API] ${method} ${endpoint}:`, e);
        return null;
    }
}

/**
 * Shorthand GET
 */
async function apiGet(endpoint) {
    return api(endpoint, 'GET');
}

/**
 * Shorthand POST
 */
async function apiPost(endpoint, body = {}) {
    return api(endpoint, 'POST', body);
}
