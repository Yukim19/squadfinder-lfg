/* =====================================================================
   SquadFinder LFG - Catálogo y datos de PRUEBA del frontend
   Mientras no exista el backend, las páginas leen los datos de aquí.
   En la semana 3 se reemplazan por llamadas a la API, por ejemplo:
     GET /api/v1/catalog/games      GET /api/v1/users/me
     GET /api/v1/lfg/posts          GET /api/v1/lfg/posts/{id}
     GET /api/v1/lfg/history        GET /api/v1/users/{id}
   Los IDs coinciden con backend/database/seed.sql y seed_demo.sql.
   ===================================================================== */

/* ---------------------------------------------------------------------
   Guardado local de la demo (localStorage). Cuando haya backend, todo esto
   se guarda en la base de datos y estas funciones desaparecen.
   --------------------------------------------------------------------- */
function leerLocal(clave, porDefecto) {
    try {
        return JSON.parse(localStorage.getItem(clave)) ?? porDefecto;
    } catch {
        return porDefecto; // modo privado o sin acceso a localStorage
    }
}

function guardarLocal(clave, valor) {
    try {
        localStorage.setItem(clave, JSON.stringify(valor));
    } catch {
        // Si no se puede guardar, el cambio dura solo hasta recargar la página
    }
}

/* ---------------------------------------------------------------------
   Catálogo: géneros y juegos (tablas genres, games y game_platforms)
   --------------------------------------------------------------------- */
const GENEROS = ['Shooter', 'MOBA', 'Battle Royale', 'RPG', 'Deportes', 'Estrategia', 'Lucha', 'Supervivencia',
    'Acción', 'Aventura', 'Carreras', 'Simulación', 'Cartas', 'Terror', 'MMO', 'Party'];

// platforms = tabla game_platforms; crossplay = games.crossplay
const JUEGOS = [
    { id: 1, name: 'Valorant', genre: 'Shooter', crossplay: false, platforms: ['PC', 'PlayStation', 'Xbox'] },
    { id: 2, name: 'Counter-Strike 2', genre: 'Shooter', crossplay: false, platforms: ['PC'] },
    { id: 3, name: 'Overwatch 2', genre: 'Shooter', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox', 'Switch'] },
    { id: 4, name: 'Marvel Rivals', genre: 'Shooter', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox'] },
    { id: 5, name: 'League of Legends', genre: 'MOBA', crossplay: false, platforms: ['PC'] },
    { id: 6, name: 'Dota 2', genre: 'MOBA', crossplay: false, platforms: ['PC'] },
    { id: 7, name: 'Fortnite', genre: 'Battle Royale', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox', 'Switch', 'Mobile'] },
    { id: 8, name: 'Apex Legends', genre: 'Battle Royale', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox', 'Switch'] },
    { id: 9, name: 'Call of Duty: Warzone', genre: 'Battle Royale', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox'] },
    { id: 10, name: 'Diablo IV', genre: 'RPG', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox'] },
    { id: 11, name: 'Destiny 2', genre: 'RPG', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox'] },
    { id: 12, name: 'Rocket League', genre: 'Deportes', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox', 'Switch'] },
    { id: 13, name: 'EA Sports FC', genre: 'Deportes', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox', 'Switch'] },
    { id: 14, name: 'Age of Empires IV', genre: 'Estrategia', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox'] },
    { id: 15, name: 'Street Fighter 6', genre: 'Lucha', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox'] },
    { id: 16, name: 'Minecraft', genre: 'Supervivencia', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox', 'Switch', 'Mobile'] },
    // Móviles
    { id: 17, name: 'Clash Royale', genre: 'Estrategia', crossplay: false, platforms: ['Mobile'] },
    { id: 18, name: 'Brawl Stars', genre: 'Acción', crossplay: false, platforms: ['Mobile'] },
    { id: 19, name: 'PUBG Mobile', genre: 'Battle Royale', crossplay: false, platforms: ['Mobile'] },
    { id: 20, name: 'Free Fire', genre: 'Battle Royale', crossplay: false, platforms: ['Mobile'] },
    { id: 21, name: 'Call of Duty: Mobile', genre: 'Shooter', crossplay: false, platforms: ['Mobile'] },
    { id: 22, name: 'Mobile Legends: Bang Bang', genre: 'MOBA', crossplay: false, platforms: ['Mobile'] },
    { id: 23, name: 'League of Legends: Wild Rift', genre: 'MOBA', crossplay: false, platforms: ['Mobile'] },
    { id: 24, name: 'Clash of Clans', genre: 'Estrategia', crossplay: false, platforms: ['Mobile'] },
    { id: 25, name: 'Pokémon Unite', genre: 'MOBA', crossplay: true, platforms: ['Switch', 'Mobile'] },
    { id: 26, name: 'Genshin Impact', genre: 'Aventura', crossplay: true, platforms: ['PC', 'PlayStation', 'Mobile'] },
    { id: 27, name: 'Among Us', genre: 'Party', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox', 'Switch', 'Mobile'] },
    { id: 28, name: 'Roblox', genre: 'Party', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox', 'Mobile'] },
    { id: 29, name: 'Marvel Snap', genre: 'Cartas', crossplay: true, platforms: ['PC', 'Mobile'] },
    // Otros géneros
    { id: 30, name: 'Mario Kart 8 Deluxe', genre: 'Carreras', crossplay: false, platforms: ['Switch'] },
    { id: 31, name: 'Phasmophobia', genre: 'Terror', crossplay: true, platforms: ['PC', 'PlayStation', 'Xbox'] },
    { id: 32, name: 'World of Warcraft', genre: 'MMO', crossplay: false, platforms: ['PC'] },
    { id: 33, name: 'Stardew Valley', genre: 'Simulación', crossplay: false, platforms: ['PC', 'PlayStation', 'Xbox', 'Switch', 'Mobile'] },
    { id: 34, name: 'Hearthstone', genre: 'Cartas', crossplay: true, platforms: ['PC', 'Mobile'] },
    { id: 35, name: 'It Takes Two', genre: 'Aventura', crossplay: false, platforms: ['PC', 'PlayStation', 'Xbox'] },
];

// Juegos que un administrador aprobó desde "Juegos sugeridos" (demo)
const CLAVE_JUEGOS_EXTRA = 'sf-juegos-extra';
JUEGOS.push(...leerLocal(CLAVE_JUEGOS_EXTRA, []));

/* ---------------------------------------------------------------------
   Textos para los valores fijos de la base de datos (CHECK de schema.sql)
   --------------------------------------------------------------------- */
const REGIONES = {
    NA_EAST: 'Norteamérica Este',
    NA_WEST: 'Norteamérica Oeste',
    LATAM_NORTH: 'Latinoamérica Norte',
    LATAM_SOUTH: 'Latinoamérica Sur',
    BRAZIL: 'Brasil',
    EUROPE: 'Europa',
    ASIA: 'Asia',
    OCEANIA: 'Oceanía',
};

const PLATAFORMAS = ['PC', 'PlayStation', 'Xbox', 'Switch', 'Mobile'];
const ICONOS_PLATAFORMA = { PC: '🖥️', PlayStation: '🎮', Xbox: '🕹️', Switch: '🎴', Mobile: '📱' };

// Idioma de la interfaz
const IDIOMAS = { es: 'Español', en: 'English' };

// Idiomas que el usuario habla o escribe: 'both' = español e inglés
const IDIOMAS_USUARIO = { ...IDIOMAS, both: 'Ambos (Español e Inglés)' };

// Idioma de una sala: además de es/en, 'any' = cualquier idioma
const IDIOMAS_SALA = { ...IDIOMAS, any: 'Todos los idiomas' };
const ICONOS_IDIOMA = { es: '🇪🇸', en: '🇺🇸', any: '🌐', both: '🌐' };

const MODOS_JUEGO = {
    CASUAL: { texto: 'Casual', icono: '😎', detalle: 'Sin requisito de rango' },
    COMPETITIVE: { texto: 'Competitivo', icono: '🏆', detalle: 'Con rango mínimo' },
};

// Rangos sugeridos por juego (para autocompletar al crear una sala)
const RANGOS_POR_JUEGO = {
    1: ['Hierro', 'Bronce', 'Plata', 'Oro', 'Platino', 'Diamante', 'Ascendente', 'Inmortal', 'Radiante'],
    2: ['Plata', 'Oro Nova', 'Águila', 'Supremo', 'Global Elite'],
    3: ['Bronce', 'Plata', 'Oro', 'Platino', 'Diamante', 'Maestro', 'Gran Maestro'],
    5: ['Hierro', 'Bronce', 'Plata', 'Oro', 'Platino', 'Esmeralda', 'Diamante', 'Maestro'],
    6: ['Heraldo', 'Guardián', 'Cruzado', 'Arconte', 'Leyenda', 'Ancestral', 'Divino', 'Inmortal'],
    7: ['Bronce', 'Plata', 'Oro', 'Platino', 'Diamante', 'Élite', 'Campeón', 'Unreal'],
    8: ['Bronce', 'Plata', 'Oro', 'Platino', 'Diamante', 'Maestro', 'Depredador'],
    12: ['Bronce', 'Plata', 'Oro', 'Platino', 'Diamante', 'Campeón', 'Gran Campeón', 'SSL'],
    18: ['Bronce', 'Plata', 'Oro', 'Diamante', 'Mítico', 'Legendario', 'Maestro', 'Pro'],
    19: ['Bronce', 'Plata', 'Oro', 'Platino', 'Diamante', 'Corona', 'As', 'Conquistador'],
    20: ['Bronce', 'Plata', 'Oro', 'Platino', 'Diamante', 'Heroico', 'Gran Maestro'],
    21: ['Novato', 'Veterano', 'Élite', 'Pro', 'Maestro', 'Gran Maestro', 'Legendario'],
    22: ['Guerrero', 'Élite', 'Maestro', 'Gran Maestro', 'Épico', 'Leyenda', 'Mítico'],
    23: ['Hierro', 'Bronce', 'Plata', 'Oro', 'Platino', 'Esmeralda', 'Diamante', 'Maestro'],
};

// Plantillas rápidas para llenar el formulario de crear sala
const PLANTILLAS_SALA = {
    ranked: { icono: '🏆', nombre: 'Ranked', titulo: 'Ranked: buscamos squad serio', mic: true, modo: 'COMPETITIVE',
              descripcion: 'Partidas competitivas para subir de rango. Comunicación activa y buena actitud.' },
    casual: { icono: '😎', nombre: 'Casual', titulo: 'Partidas casuales, buen ambiente', mic: false, modo: 'CASUAL',
              descripcion: 'Sin presión, solo a pasarla bien. Todos los niveles son bienvenidos.' },
    aprender: { icono: '📚', nombre: 'Aprender', titulo: 'Busco gente para aprender y mejorar', mic: true, modo: 'CASUAL',
                descripcion: 'Soy nuevo o quiero mejorar. Se agradecen consejos y paciencia.' },
    torneo: { icono: '⚔️', nombre: 'Torneo', titulo: 'Armando equipo para torneo', mic: true, modo: 'COMPETITIVE',
              descripcion: 'Buscamos equipo fijo para practicar y competir en torneos de la comunidad.' },
};

const ESTADOS_SALA = {
    OPEN: { texto: 'Abierta', clase: 'text-bg-success' },
    FULL: { texto: 'Llena', clase: 'text-bg-warning' },
    IN_PROGRESS: { texto: 'En partida', clase: 'text-bg-info' },
    CLOSED: { texto: 'Terminada', clase: 'text-bg-secondary' },
    CANCELLED: { texto: 'Cancelada', clase: 'text-bg-danger' },
};

const NIVELES_FILTRO = {
    STRICT: 'Estricto',
    MEDIUM: 'Medio',
    OFF: 'Apagado',
};

const ETIQUETAS_RESENA = {
    GREAT_LEADER: 'Gran líder',
    FRIENDLY: 'Compañero amigable',
    GOOD_COMMS: 'Buena comunicación',
    SKILLED: 'Gran habilidad',
    TEAM_PLAYER: 'Juega en equipo',
};

const PROVEEDORES = {
    discord: 'Discord',
    steam: 'Steam',
    twitch: 'Twitch',
    kick: 'Kick',
};

/* ---------------------------------------------------------------------
   Niveles de honor (igual que level_from_xp() en schema.sql)
   Reseña recibida: 5★ = 30 XP, 4★ = 20, 3★ = 10, 1-2★ = 0.
   Cada 100 XP = 1 nivel (máximo 10). XP negativa = nivel 0 (Rookie).
   --------------------------------------------------------------------- */
const XP_POR_NIVEL = 100;
const NIVEL_MAXIMO = 10;
const XP_POR_ESTRELLAS = { 5: 30, 4: 20, 3: 10, 2: 0, 1: 0 };

function nivelDesdeXp(xp) {
    if (xp < 0) return 0;
    return Math.min(NIVEL_MAXIMO, 1 + Math.floor(xp / XP_POR_NIVEL));
}

// Avatares prediseñados (users.avatar_url = 'preset:<emoji>')
const AVATARES_PRESET = ['🦊', '🐺', '🐉', '🦄', '🤖', '👾', '👻', '🐱', '🦁', '🐸', '🎮', '⚡'];

// Valores de user_reports.reason
const MOTIVOS_REPORTE = {
    TOXIC_CHAT: { texto: 'Lenguaje tóxico o insultos', icono: '🤬' },
    HARASSMENT: { texto: 'Acoso o amenazas', icono: '⚠️' },
    AFK_GRIEFING: { texto: 'Abandonó o saboteó la partida', icono: '💤' },
    CHEATING: { texto: 'Trampas o hacks', icono: '🕵️' },
    OTHER: { texto: 'Otro motivo', icono: '📝' },
};

// Valores de user_reports.status (resultado de la revisión del administrador)
const ESTADOS_REPORTE = {
    PENDING: { texto: 'Pendiente', clase: 'text-bg-warning' },
    DISMISSED: { texto: 'Descartado', clase: 'text-bg-secondary' },
    WARNED: { texto: 'Advertencia', clase: 'text-bg-warning' },
    SUSPENDED: { texto: 'Cuenta suspendida', clase: 'text-bg-info' },
    BANNED: { texto: 'Cuenta eliminada', clase: 'text-bg-danger' },
};

/* ---------------------------------------------------------------------
   Usuarios de prueba (tabla users + preferencias + cuentas vinculadas)
   ana_gg es ADMIN para poder probar el panel de moderación.
   --------------------------------------------------------------------- */
const USUARIOS_DEMO = [
    { id: 1, username: 'ana_gg', role: 'ADMIN', account_status: 'ACTIVE', region: 'NA_EAST',
      xp: 230, level: 3, warnings_count: 0, avatar_url: 'preset:🦊',
      juegos: [1, 7], generos: ['Shooter', 'Battle Royale'],
      cuentas: { discord: 'ana_gg', twitch: 'ana_gg_live' }, en_vivo: true, miembro_desde: '2026-10-01' },
    { id: 2, username: 'bruno_tank', role: 'USER', account_status: 'ACTIVE', region: 'LATAM_NORTH',
      xp: 420, level: 5, warnings_count: 0, avatar_url: null,
      juegos: [1, 5], generos: ['Shooter', 'MOBA'],
      cuentas: { steam: 'brunotank', discord: 'bruno#tank' }, en_vivo: false, miembro_desde: '2026-10-02' },
    { id: 3, username: 'carla_heals', role: 'USER', account_status: 'ACTIVE', region: 'NA_WEST',
      xp: 0, level: 1, warnings_count: 0, avatar_url: 'preset:🦄',
      juegos: [5, 10, 25], generos: ['MOBA', 'RPG'],
      cuentas: {}, en_vivo: false, miembro_desde: '2026-10-03' },
    { id: 4, username: 'diego_entry', role: 'USER', account_status: 'ACTIVE', region: 'LATAM_SOUTH',
      xp: -100, level: 0, warnings_count: 1, avatar_url: null,
      juegos: [1, 2, 7, 20], generos: ['Shooter'],
      cuentas: { kick: 'diego_entry' }, en_vivo: false, miembro_desde: '2026-10-05' },
];

// Usuario que "inició sesión" (ana_gg). En la semana 3: GET /api/v1/users/me
// Mientras no hay backend, los cambios del perfil se guardan en el navegador
// (localStorage) para que todas las páginas los vean, incluso al recargar.
const CLAVE_USUARIO_DEMO = 'sf-usuario-demo';

const USUARIO_DEMO = {
    ...USUARIOS_DEMO[0],
    ui_language: 'es',
    preferred_language_speak: 'both',
    preferred_language_write: 'es',
    toxicity_filter_level: 'STRICT',
    ...leerLocal(CLAVE_USUARIO_DEMO, {}),
};
USUARIOS_DEMO[0] = USUARIO_DEMO; // el resto de páginas ve los cambios (foto, nombre...)

// Semana 3: se reemplaza por PUT /api/v1/users/me
function guardarUsuarioDemo(cambios) {
    Object.assign(USUARIO_DEMO, cambios);
    guardarLocal(CLAVE_USUARIO_DEMO, USUARIO_DEMO);
}

// Vuelve a los datos originales de seed_demo.sql
function restablecerUsuarioDemo() {
    try {
        for (const clave of [CLAVE_USUARIO_DEMO, CLAVE_LISTA_NEGRA, CLAVE_SUGERENCIAS, CLAVE_JUEGOS_EXTRA]) {
            localStorage.removeItem(clave);
        }
    } catch {
        // Nada que borrar
    }
}

function usuarioPorId(id) {
    return USUARIOS_DEMO.find((u) => u.id === Number(id));
}

function usuarioPorNombre(username) {
    return USUARIOS_DEMO.find((u) => u.username === username);
}

function juegoPorId(id) {
    return JUEGOS.find((j) => j.id === Number(id));
}

/* ---------------------------------------------------------------------
   Lista negra (tabla user_blocks). Solo afecta lo que ve quien la creó:
   no ve las salas de los usuarios bloqueados.
   --------------------------------------------------------------------- */
const CLAVE_LISTA_NEGRA = 'sf-lista-negra';

function listaNegra() {
    return leerLocal(CLAVE_LISTA_NEGRA, []);
}

function estaBloqueado(usuarioId) {
    return listaNegra().some((b) => b.blocked_id === Number(usuarioId));
}

// Semana 3: POST /api/v1/users/me/blocks
function bloquearUsuario(usuarioId, motivo = null) {
    if (estaBloqueado(usuarioId)) return;
    const u = usuarioPorId(usuarioId);
    guardarLocal(CLAVE_LISTA_NEGRA, [...listaNegra(),
        { blocked_id: u.id, username: u.username, reason: motivo, created_at: new Date().toLocaleDateString('en-CA') }]); // AAAA-MM-DD en hora local
}

// Semana 3: DELETE /api/v1/users/me/blocks/{id}
function desbloquearUsuario(usuarioId) {
    guardarLocal(CLAVE_LISTA_NEGRA, listaNegra().filter((b) => b.blocked_id !== Number(usuarioId)));
}

/* ---------------------------------------------------------------------
   Salas (vista v_lfg_posts), miembros (v_post_members) y solicitudes
   --------------------------------------------------------------------- */
const SALAS_DEMO = [
    { id: 1, host_id: 1, game_id: 1, game_name: 'Valorant', game_crossplay: false, title: 'Ranked tranqui esta noche',
      description: 'Buscamos dúo/trío para subir a Platino. Buena onda y comunicación.',
      platforms: ['PC'], play_mode: 'COMPETITIVE', max_players: 5, current_players: 2, rank_required: 'Oro',
      mic_required: true, required_language: 'es', status: 'OPEN', host_username: 'ana_gg', host_region: 'NA_EAST',
      host_level: 3, created_at: '2026-10-10 20:00' },
    { id: 2, host_id: 3, game_id: 5, game_name: 'League of Legends', game_crossplay: false, title: 'Flex queue, chill vibes',
      description: null, platforms: ['PC'], play_mode: 'CASUAL', max_players: 5, current_players: 1, rank_required: null,
      mic_required: false, required_language: 'en', status: 'OPEN', host_username: 'carla_heals',
      host_region: 'NA_WEST', host_level: 1, created_at: '2026-10-10 18:30' },
    { id: 4, host_id: 4, game_id: 7, game_name: 'Fortnite', game_crossplay: true, title: 'Dúos cross-plataforma',
      description: 'Cualquier plataforma e idioma, solo buena onda.', platforms: ['PC', 'PlayStation', 'Switch'],
      play_mode: 'CASUAL', max_players: 4, current_players: 1, rank_required: null, mic_required: false,
      required_language: 'any', status: 'OPEN', host_username: 'diego_entry', host_region: 'LATAM_SOUTH',
      host_level: 0, created_at: '2026-10-10 21:15' },
];

// Salas que el usuario puede ver: sin las de su lista negra (feed_for_user() en la BD)
function salasVisibles() {
    return SALAS_DEMO.filter((s) => !estaBloqueado(s.host_id));
}

const MIEMBROS_DEMO = {
    1: [
        { user_id: 1, username: 'ana_gg', role: 'HOST', region: 'NA_EAST', level: 3 },
        { user_id: 2, username: 'bruno_tank', role: 'MEMBER', region: 'LATAM_NORTH', level: 5 },
    ],
    2: [
        { user_id: 3, username: 'carla_heals', role: 'HOST', region: 'NA_WEST', level: 1 },
    ],
    4: [
        { user_id: 4, username: 'diego_entry', role: 'HOST', region: 'LATAM_SOUTH', level: 0 },
    ],
};

// Solicitudes pendientes (tabla applications), por sala
const SOLICITUDES_DEMO = {
    1: [
        { id: 2, applicant_id: 4, username: 'diego_entry', region: 'LATAM_SOUTH', level: 0,
          message: '¡Juego de entry! Tengo micrófono.' },
    ],
    2: [],
    4: [],
};

/* ---------------------------------------------------------------------
   Chat (tabla chat_messages). toxicity_level lo decide el filtro PNL del
   servidor; cada usuario ve el mensaje oculto o no según su propio nivel.
   --------------------------------------------------------------------- */
const MENSAJES_DEMO = {
    1: [
        { sender_id: 1, username: 'ana_gg', message: '¡Hola! Entramos en 10 min', toxicity_level: 'NONE', sent_at: '20:01' },
        { sender_id: 2, username: 'bruno_tank', message: 'Listo, ya estoy conectado', toxicity_level: 'NONE', sent_at: '20:03' },
        { sender_id: 2, username: 'bruno_tank', message: 'El de la otra sala es malísimo, que desinstale', toxicity_level: 'MILD', sent_at: '20:04' },
        { sender_id: 1, username: 'ana_gg', message: 'Jaja tranqui, a lo nuestro 🎯', toxicity_level: 'NONE', sent_at: '20:05' },
    ],
    2: [],
    3: [
        { sender_id: 2, username: 'bruno_tank', message: 'Diego eres un inútil, nos hiciste perder', toxicity_level: 'SEVERE', sent_at: '22:40' },
    ],
    4: [],
};

/* ---------------------------------------------------------------------
   Historial (vista v_match_history) y reseñas (tabla user_reviews)
   --------------------------------------------------------------------- */
const HISTORIAL_DEMO = [
    { post_id: 3, title: 'Partida de ayer', game_name: 'Valorant', platforms: ['PC'], closed_at: '2026-10-09',
      host_id: 2, teammate_id: 2, teammate_username: 'bruno_tank', teammate_region: 'LATAM_NORTH',
      teammate_level: 5, already_reviewed: true, already_reported: false,
      my_review: { rating: 5, tag: 'GREAT_LEADER', comment: 'Muy buen shotcalling' } },
    { post_id: 3, title: 'Partida de ayer', game_name: 'Valorant', platforms: ['PC'], closed_at: '2026-10-09',
      host_id: 2, teammate_id: 4, teammate_username: 'diego_entry', teammate_region: 'LATAM_SOUTH',
      teammate_level: 0, already_reviewed: false, already_reported: false, my_review: null },
];

// Reseñas recibidas por cada usuario (para su perfil público)
const RESENAS_DEMO = [
    { target_user_id: 2, reviewer_id: 1, reviewer_username: 'ana_gg', rating: 5, tag: 'GREAT_LEADER',
      comment: 'Muy buen shotcalling', game_name: 'Valorant', created_at: '2026-10-09' },
    { target_user_id: 2, reviewer_id: 4, reviewer_username: 'diego_entry', rating: 4, tag: 'FRIENDLY',
      comment: null, game_name: 'Valorant', created_at: '2026-10-09' },
    { target_user_id: 1, reviewer_id: 2, reviewer_username: 'bruno_tank', rating: 5, tag: 'SKILLED',
      comment: 'Clutch increíble', game_name: 'Valorant', created_at: '2026-10-09' },
];

/* ---------------------------------------------------------------------
   Moderación (vista v_reports_admin y tabla moderation_settings).
   flagged_messages = mensajes del reportado en esa partida que el filtro
   PNL marcó como tóxicos.
   --------------------------------------------------------------------- */
const REGLAS_MODERACION_DEMO = {
    warnings_limit: 3,
    auto_action: 'BAN',
    auto_suspension_days: 30,
    warning_levels_removed: 1,
    suspension_levels_removed: 2,
};

const REPORTES_DEMO = [
    { id: 1, reporter_id: 4, reporter_username: 'diego_entry', reported_user_id: 2, reported_username: 'bruno_tank',
      reported_level: 5, reported_warnings: 0, reported_account_status: 'ACTIVE', post_id: 3, post_title: 'Partida de ayer',
      reason: 'TOXIC_CHAT', comment: 'Me insultó en el chat cuando perdimos la ronda y siguió burlándose.',
      status: 'PENDING', suspension_days: null, levels_removed: 0, is_automatic: false,
      admin_notes: null, resolved_at: null, created_at: '2026-10-10 09:15', total_reports: 1 },
    { id: 2, reporter_id: 2, reporter_username: 'bruno_tank', reported_user_id: 4, reported_username: 'diego_entry',
      reported_level: 0, reported_warnings: 1, reported_account_status: 'ACTIVE', post_id: 3, post_title: 'Partida de ayer',
      reason: 'AFK_GRIEFING', comment: 'Se quedó quieto dos rondas sin jugar.',
      status: 'WARNED', suspension_days: null, levels_removed: 1, is_automatic: false,
      admin_notes: 'Primera advertencia: abandonar la partida perjudica al equipo.',
      resolved_at: '2026-10-10 11:00', created_at: '2026-10-09 23:10', total_reports: 1 },
];

// Mensajes marcados por el filtro que sirven de evidencia en un reporte
function evidenciaChat(postId, usuarioId) {
    return (MENSAJES_DEMO[postId] ?? []).filter((m) => m.sender_id === usuarioId && m.toxicity_level !== 'NONE');
}

/* ---------------------------------------------------------------------
   Juegos sugeridos por los usuarios (tabla game_requests)
   --------------------------------------------------------------------- */
const CLAVE_SUGERENCIAS = 'sf-sugerencias-juegos';

const SUGERENCIAS_DEMO = [
    { id: 1, user_id: 3, username: 'carla_heals', game_name: 'Deadlock', platforms_note: 'PC',
      status: 'PENDING', created_at: '2026-10-10 14:20' },
    ...leerLocal(CLAVE_SUGERENCIAS, []),
];

// Semana 3: POST /api/v1/catalog/game-requests
function sugerirJuego(nombre, plataformas) {
    const nueva = {
        id: Date.now(), user_id: USUARIO_DEMO.id, username: USUARIO_DEMO.username, game_name: nombre,
        platforms_note: plataformas || null, status: 'PENDING', created_at: new Date().toLocaleString('es'),
    };
    SUGERENCIAS_DEMO.push(nueva);
    guardarLocal(CLAVE_SUGERENCIAS, SUGERENCIAS_DEMO.filter((s) => s.id !== 1));
    return nueva;
}

/* ---------------------------------------------------------------------
   Utilidades para pintar formularios
   --------------------------------------------------------------------- */

// Escapa texto que viene de usuarios antes de meterlo en HTML (evita XSS)
function esc(texto) {
    const div = document.createElement('div');
    div.textContent = String(texto ?? '');
    return div.innerHTML;
}

// Llena un <select> con las opciones de un objeto { valor: texto }
function llenarSelect(selectId, opciones, seleccionada = '') {
    const select = document.getElementById(selectId);
    for (const [valor, texto] of Object.entries(opciones)) {
        select.add(new Option(texto, valor, false, valor === seleccionada));
    }
}

function llenarRegiones(selectId, seleccionada = '') {
    llenarSelect(selectId, REGIONES, seleccionada);
}

// Crea botones seleccionables (chips) dentro de un contenedor.
// items: [{ value, label, plataformas? }]; seleccionados: lista de values marcados.
function renderChips(contenedorId, items, nombre, seleccionados = []) {
    const contenedor = document.getElementById(contenedorId);
    contenedor.innerHTML = items.map(({ value, label, plataformas = [] }) => {
        const id = `${nombre}-${String(value).replace(/\W+/g, '-')}`;
        const marcado = seleccionados.includes(value) ? 'checked' : '';
        return `<span class="sf-chip-item" data-texto="${esc(String(label).toLowerCase())}" data-plataformas="${esc(plataformas.join(','))}">
                <input type="checkbox" class="btn-check" name="${nombre}" id="${id}" value="${esc(value)}" ${marcado} autocomplete="off">
                <label class="btn btn-outline-light sf-chip" for="${id}">${esc(label)}</label></span>`;
    }).join('');
}

// Devuelve los values marcados de un grupo de chips
function chipsMarcados(nombre) {
    return [...document.querySelectorAll(`input[name="${nombre}"]:checked`)].map((i) => i.value);
}
