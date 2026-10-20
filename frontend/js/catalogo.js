/* =====================================================================
   SquadFinder LFG - Constantes y utilidades compartidas del frontend
   Textos de los valores fijos de la base de datos (CHECK de schema.sql),
   niveles de honor y funciones para pintar formularios.
   Los datos (juegos, usuarios, salas...) vienen de la API: ver api.js.
   ===================================================================== */

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

/* ---------------------------------------------------------------------
   Idioma: reemplaza los textos de las constantes de arriba por los del idioma
   elegido (las mismas variables, así el resto del código no cambia).
   --------------------------------------------------------------------- */
function localizarCatalogo() {
    for (const k of Object.keys(REGIONES)) REGIONES[k] = t(`catalogo.regiones.${k}`);
    IDIOMAS_USUARIO.both = t('catalogo.idiomaAmbos');
    IDIOMAS_SALA.any = t('catalogo.idiomaTodos');
    for (const k of Object.keys(MODOS_JUEGO)) {
        MODOS_JUEGO[k].texto = t(`catalogo.modos.${k}.texto`);
        MODOS_JUEGO[k].detalle = t(`catalogo.modos.${k}.detalle`);
    }
    for (const k of Object.keys(ESTADOS_SALA)) ESTADOS_SALA[k].texto = t(`catalogo.estadosSala.${k}`);
    for (const k of Object.keys(NIVELES_FILTRO)) NIVELES_FILTRO[k] = t(`catalogo.filtro.${k}`);
    for (const k of Object.keys(ETIQUETAS_RESENA)) ETIQUETAS_RESENA[k] = t(`catalogo.etiquetas.${k}`);
    for (const k of Object.keys(MOTIVOS_REPORTE)) MOTIVOS_REPORTE[k].texto = t(`catalogo.motivos.${k}`);
    for (const k of Object.keys(ESTADOS_REPORTE)) ESTADOS_REPORTE[k].texto = t(`catalogo.estadosReporte.${k}`);
    for (const k of Object.keys(PLANTILLAS_SALA)) {
        PLANTILLAS_SALA[k].nombre = t(`catalogo.plantillas.${k}.nombre`);
        PLANTILLAS_SALA[k].titulo = t(`catalogo.plantillas.${k}.titulo`);
        PLANTILLAS_SALA[k].descripcion = t(`catalogo.plantillas.${k}.descripcion`);
    }
}
i18nListo.then(localizarCatalogo);
