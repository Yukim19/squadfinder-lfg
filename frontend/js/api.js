/* =====================================================================
   SquadFinder LFG - Conexión con el backend y sesión del usuario
   Requiere (antes): el SDK de Auth0 (auth0-spa-js) en las páginas con sesión.

   Modos de inicio de sesión (los decide el backend en /health -> auth_mode):
     auth0 -> login real con Auth0 (correo o Google). Siempre en producción.
     dev   -> solo para programar: se entra como un usuario de prueba (demo|ana...).
   ===================================================================== */

const ES_LOCAL = ['localhost', '127.0.0.1'].includes(location.hostname);

const CONFIG = {
    // En la semana 6 se cambian por las direcciones de Render
    API_URL: ES_LOCAL ? `http://${location.hostname}:8001/api/v1` : 'https://squadfinder-api.onrender.com/api/v1',
    CHAT_URL: ES_LOCAL ? `ws://${location.hostname}:8002/ws/chat` : 'wss://squadfinder-chat.onrender.com/ws/chat',
    // Datos públicos de Auth0 (el Client Secret no se usa nunca en el navegador)
    AUTH0: {
        domain: 'squadfinder-lfg.us.auth0.com',
        clientId: 'Lj0skr3CdbzAQdv8lvHC37oW5c7CCElE',
        audience: 'https://api.squadfinder-lfg',
    },
};

const CLAVE_USUARIO_PRUEBA = 'sf-dev-user';

/* ---------------------------------------------------------------------
   Errores de la API: { error: { code, message, details } }
   --------------------------------------------------------------------- */
class ErrorApi extends Error {
    constructor(status, code, message, details = null) {
        super(message);
        this.status = status;
        this.code = code;
        this.details = details;
    }
}

/* ---------------------------------------------------------------------
   Sesión
   --------------------------------------------------------------------- */
let _modoAuth = null;
let _auth0 = null;

// 'auth0' o 'dev', según el backend. Se guarda mientras la pestaña esté abierta.
async function modoAuth() {
    if (_modoAuth) return _modoAuth;
    try {
        _modoAuth = sessionStorage.getItem('sf-modo-auth');
    } catch { /* sin almacenamiento: se consulta cada vez */ }
    if (!_modoAuth) {
        const salud = await pedir('/health', { sinSesion: true });
        _modoAuth = salud.auth_mode;
        try { sessionStorage.setItem('sf-modo-auth', _modoAuth); } catch { /* nada */ }
    }
    return _modoAuth;
}

async function clienteAuth0() {
    if (!_auth0) {
        _auth0 = await auth0.createAuth0Client({
            domain: CONFIG.AUTH0.domain,
            clientId: CONFIG.AUTH0.clientId,
            // La sesión se recuerda al cambiar de página (cada página es una carga nueva)
            cacheLocation: 'localstorage',
            authorizationParams: {
                audience: CONFIG.AUTH0.audience,
                redirect_uri: `${location.origin}/login.html`,
            },
        });
    }
    return _auth0;
}

function usuarioPrueba() {
    try { return localStorage.getItem(CLAVE_USUARIO_PRUEBA); } catch { return null; }
}

// Encabezado de autenticación para el backend (o null si no hay sesión)
async function credenciales() {
    if (await modoAuth() === 'dev') {
        const sub = usuarioPrueba();
        return sub ? { 'X-Dev-User': sub } : null;
    }
    try {
        const token = await (await clienteAuth0()).getTokenSilently();
        return { Authorization: `Bearer ${token}` };
    } catch {
        return null; // no inició sesión o la sesión expiró
    }
}

// Token para el primer mensaje del chat (WebSocket)
async function tokenChat() {
    const c = await credenciales();
    return c?.Authorization?.slice(7) ?? c?.['X-Dev-User'] ?? null;
}

async function iniciarSesion({ registro = false } = {}) {
    await (await clienteAuth0()).loginWithRedirect({
        authorizationParams: registro ? { screen_hint: 'signup' } : {},
    });
}

async function cerrarSesion() {
    if (await modoAuth() === 'dev') {
        try { localStorage.removeItem(CLAVE_USUARIO_PRUEBA); } catch { /* nada */ }
        location.href = 'login.html';
        return;
    }
    await (await clienteAuth0()).logout({ logoutParams: { returnTo: `${location.origin}/login.html` } });
}

/* ---------------------------------------------------------------------
   Peticiones a la API
   api('/lfg/posts')                                -> GET
   api('/lfg/posts', { method: 'POST', body: {...} })
   Lanza ErrorApi si algo falla. Los errores de sesión redirigen solos.
   --------------------------------------------------------------------- */
async function pedir(ruta, { method = 'GET', body, params, sinSesion = false, base = CONFIG.API_URL } = {}) {
    const url = new URL(base + ruta);
    for (const [clave, valor] of Object.entries(params ?? {})) {
        if (valor !== undefined && valor !== null && valor !== '') url.searchParams.set(clave, valor);
    }
    const headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (!sinSesion) Object.assign(headers, await credenciales());

    let respuesta;
    try {
        respuesta = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch {
        throw new ErrorApi(0, 'NETWORK_ERROR', 'No se pudo conectar con el servidor. Revisa tu conexión o que la API esté encendida.');
    }
    if (respuesta.status === 204) return null;
    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
        const e = datos?.error ?? {};
        throw new ErrorApi(respuesta.status, e.code ?? 'ERROR', e.message ?? 'Ocurrió un error inesperado.', e.details ?? null);
    }
    return datos;
}

const ERRORES_DE_SESION = {
    NOT_AUTHENTICATED: 'sesion',
    TOKEN_EXPIRED: 'expirada',
    INVALID_TOKEN: 'sesion',
    ACCOUNT_BANNED: 'eliminada',
    ACCOUNT_SUSPENDED: 'suspendida',
};

async function api(ruta, opciones = {}) {
    try {
        return await pedir(ruta, opciones);
    } catch (e) {
        if (e.code === 'ONBOARDING_REQUIRED' && !location.pathname.endsWith('onboarding.html')) {
            location.replace('onboarding.html');
            throw e;
        }
        const motivo = ERRORES_DE_SESION[e.code];
        if (motivo) {
            const extra = e.details?.suspended_until ? `&hasta=${encodeURIComponent(e.details.suspended_until)}` : '';
            location.replace(`login.html?motivo=${motivo}${extra}`);
        }
        throw e;
    }
}

/* ---------------------------------------------------------------------
   Usuario actual y catálogo (se piden una sola vez por página)
   --------------------------------------------------------------------- */
let _yo = null;
async function usuarioActual() {
    _yo ??= await api('/users/me');
    return _yo;
}

let _catalogo = null;
async function catalogo() {
    _catalogo ??= Promise.all([pedir('/catalog/games', { sinSesion: true }), pedir('/catalog/genres', { sinSesion: true })])
        .then(([juegos, generos]) => ({ juegos, generos }));
    return _catalogo;
}

// Muestra el error de la API en un aviso (si no es un error de sesión, que ya redirige)
function avisarError(e, porDefecto = 'No se pudo completar la acción.') {
    if (ERRORES_DE_SESION[e?.code] || e?.code === 'ONBOARDING_REQUIRED') return;
    mostrarToast(e?.message || porDefecto, 'danger');
}
