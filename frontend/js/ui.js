/* =====================================================================
   SquadFinder LFG - Componentes de interfaz compartidos
   Requiere: Bootstrap (bundle), js/catalogo.js y js/api.js cargados antes.
   ===================================================================== */

/* ---------------------------------------------------------------------
   Mensajes emergentes (toasts) para confirmar acciones
   tipo: 'success' | 'danger' | 'info' | 'warning'
   --------------------------------------------------------------------- */
function mostrarToast(mensaje, tipo = 'success') {
    let zona = document.getElementById('sf-toasts');
    if (!zona) {
        zona = document.createElement('div');
        zona.id = 'sf-toasts';
        zona.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        zona.setAttribute('aria-live', 'polite');
        document.body.appendChild(zona);
    }
    const toast = document.createElement('div');
    toast.className = `toast align-items-center sf-toast sf-toast-${tipo} border-0`;
    toast.setAttribute('role', tipo === 'danger' ? 'alert' : 'status');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${esc(mensaje)}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="${esc(t('comun.cerrar'))}"></button>
        </div>`;
    zona.appendChild(toast);
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
    bootstrap.Toast.getOrCreateInstance(toast, { delay: 3500 }).show();
}

/* ---------------------------------------------------------------------
   Ventana de confirmación para acciones que no se pueden deshacer.
   Devuelve una Promesa: true si el usuario confirma, false si cancela.
   --------------------------------------------------------------------- */
function confirmar({ titulo, mensaje, textoBoton = t('ui.confirmar'), peligro = true }) {
    return new Promise((resolver) => {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.tabIndex = -1;
        modal.setAttribute('aria-labelledby', 'sf-confirmar-titulo');
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content sf-modal">
                    <div class="modal-header border-0">
                        <h2 class="modal-title h5" id="sf-confirmar-titulo">${esc(titulo)}</h2>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="${esc(t('comun.cerrar'))}"></button>
                    </div>
                    <div class="modal-body pt-0 text-secondary">${esc(mensaje)}</div>
                    <div class="modal-footer border-0">
                        <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">${esc(t('comun.cancelar'))}</button>
                        <button type="button" class="btn ${peligro ? 'btn-danger' : 'btn-primary'}" data-sf-ok>${esc(textoBoton)}</button>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(modal);
        const instancia = new bootstrap.Modal(modal);
        let confirmado = false;
        modal.querySelector('[data-sf-ok]').addEventListener('click', () => {
            confirmado = true;
            instancia.hide();
        });
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
            resolver(confirmado);
        });
        instancia.show();
    });
}

/* ---------------------------------------------------------------------
   Pequeños componentes HTML reutilizables
   --------------------------------------------------------------------- */
function enlaceUsuario(id, username) {
    return `<a class="sf-user-link" href="usuario.html?id=${Number(id)}">${esc(username)}</a>`;
}

// Avatar del usuario: su foto, un avatar prediseñado o la inicial del nombre
function avatar(username, tamano = '', url = null) {
    if (url?.startsWith('preset:')) {
        return `<span class="sf-avatar sf-avatar-preset ${tamano}" aria-hidden="true">${esc(url.slice(7))}</span>`;
    }
    if (url) {
        return `<img class="sf-avatar sf-avatar-foto ${tamano}" src="${esc(url)}" alt="" aria-hidden="true">`;
    }
    return `<span class="sf-avatar ${tamano}" aria-hidden="true">${esc(String(username)[0] ?? '?')}</span>`;
}

// Nivel de honor: "⭐ Nv. 3" o "🐣 Rookie" si está en nivel 0
function badgeNivel(nivel) {
    const n = Number(nivel);
    if (n <= 0) {
        return `<span class="badge sf-badge-rookie" title="${esc(t('ui.rookieTitulo'))}">${esc(t('ui.rookie'))}</span>`;
    }
    return `<span class="badge sf-badge-honor sf-nivel-${Math.min(n, NIVEL_MAXIMO)}" title="${esc(t('ui.nivelTitulo', { n, max: NIVEL_MAXIMO }))}">${esc(t('ui.nivelCorto', { n }))}</span>`;
}

// Barra de progreso hacia el siguiente nivel
function barraNivel(xp) {
    const nivel = nivelDesdeXp(xp);
    if (nivel === 0) {
        const falta = -xp;
        return `<div class="small text-secondary mb-1">${esc(t('ui.faltanXp', { n: falta }))}</div>
                <div class="progress sf-progress-rookie" role="progressbar" aria-label="${esc(t('ui.progresoRookie'))}"
                     aria-valuenow="0"><div class="progress-bar" style="width: 0%"></div></div>`;
    }
    if (nivel === NIVEL_MAXIMO) {
        return `<div class="small text-secondary mb-1">${esc(t('ui.nivelMaximo', { xp }))}</div>
                <div class="progress" role="progressbar" aria-label="${esc(t('ui.nivelMaximoAria'))}" aria-valuenow="100">
                    <div class="progress-bar" style="width: 100%"></div></div>`;
    }
    const enNivel = xp % XP_POR_NIVEL;
    return `<div class="small text-secondary mb-1">${esc(t('ui.xpSiguiente', { xp: enNivel, por: XP_POR_NIVEL, nivel: nivel + 1 }))}</div>
            <div class="progress" role="progressbar" aria-label="${esc(t('ui.progresoAria'))}" aria-valuenow="${enNivel}">
                <div class="progress-bar" style="width: ${enNivel}%"></div></div>`;
}

// Íconos de las cuentas vinculadas (Discord, Steam, Twitch, Kick)
const ICONOS_CUENTA = {
    discord: '<i class="bi bi-discord"></i>',
    steam: '<i class="bi bi-steam"></i>',
    twitch: '<i class="bi bi-twitch"></i>',
    kick: '<span class="sf-icono-kick">K</span>',
};

function iconosCuentas(cuentas = {}) {
    return Object.entries(cuentas).map(([clave, usuario]) =>
        `<span class="sf-cuenta sf-cuenta-${clave}" title="${esc(PROVEEDORES[clave])}: ${esc(usuario)}">
            ${ICONOS_CUENTA[clave]}<span class="visually-hidden">${esc(PROVEEDORES[clave])}: ${esc(usuario)}</span></span>`).join('');
}

function estrellas(rating) {
    const n = Math.round(Number(rating));
    return `<span class="sf-stars" aria-label="${esc(t('ui.estrellasAria', { n }))}">${'★'.repeat(n)}<span class="sf-stars-off">${'★'.repeat(5 - n)}</span></span>`;
}

function badgeEstado(status) {
    const e = ESTADOS_SALA[status] ?? { texto: status, clase: 'text-bg-secondary' };
    return `<span class="badge ${e.clase}">${esc(e.texto)}</span>`;
}

// "🖥️ PC · 🎮 PlayStation" a partir de la lista de plataformas de una sala
function textoPlataformas(plataformas) {
    return plataformas.map((p) => `${ICONOS_PLATAFORMA[p] ?? ''} ${p}`).join(' · ');
}

function badgeModo(modo) {
    const m = MODOS_JUEGO[modo];
    return m ? `<span class="badge ${modo === 'COMPETITIVE' ? 'text-bg-warning' : 'text-bg-info'}">${m.icono} ${esc(m.texto)}</span>` : '';
}

// % de compatibilidad entre una sala y el usuario. Versión simple de lo que
// calculará el matchmaking-service: juego 40 + idioma 30 + región 30.
function calcularCompatibilidad(sala, usuario) {
    let puntos = 0;
    if (usuario.games.includes(sala.game_id)) puntos += 40;
    const habla = usuario.preferred_language_speak;
    if (sala.required_language === 'any' || habla === 'both' || sala.required_language === habla) puntos += 30;
    if (sala.host_region === usuario.region) puntos += 30;
    return puntos;
}

/* ---------------------------------------------------------------------
   Buscador y filtro por plataforma para una lista larga de chips de juegos.
   Requiere un <input type="search"> y botones con data-filtro-plataforma.
   --------------------------------------------------------------------- */
function activarFiltroJuegos({ buscadorId, contenedorId, botonesId }) {
    const buscador = document.getElementById(buscadorId);
    const contenedor = document.getElementById(contenedorId);
    const botones = document.getElementById(botonesId);
    let plataforma = '';

    function aplicar() {
        const texto = buscador.value.trim().toLowerCase();
        for (const item of contenedor.querySelectorAll('.sf-chip-item')) {
            const plataformas = item.dataset.plataformas.split(',');
            let coincidePlataforma = true;
            if (plataforma === 'MARCADOS') coincidePlataforma = item.querySelector('input').checked;
            else if (plataforma === 'CONSOLA') coincidePlataforma = plataformas.some((p) => ['PlayStation', 'Xbox', 'Switch'].includes(p));
            else if (plataforma) coincidePlataforma = plataformas.includes(plataforma);
            item.classList.toggle('d-none', !(item.dataset.texto.includes(texto) && coincidePlataforma));
        }
    }

    buscador.addEventListener('input', aplicar);
    botones.addEventListener('click', (e) => {
        const boton = e.target.closest('[data-filtro-plataforma]');
        if (!boton) return;
        plataforma = boton.dataset.filtroPlataforma;
        botones.querySelectorAll('[data-filtro-plataforma]').forEach((b) => b.classList.toggle('active', b === boton));
        aplicar();
    });
}

/* ---------------------------------------------------------------------
   Ventana para sugerir un juego que no está en la lista (CREATE game_request)
   --------------------------------------------------------------------- */
// alEnviar(datos): si se pasa, la sugerencia no se envía y se le entrega a la página
// (en el onboarding se envía después de crear el perfil, porque antes no existe el usuario).
function abrirSugerenciaJuego({ alEnviar = null } = {}) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.tabIndex = -1;
    modal.setAttribute('aria-labelledby', 'sf-sugerir-titulo');
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <form class="modal-content sf-modal" novalidate>
                <div class="modal-header border-0">
                    <h2 class="modal-title h5" id="sf-sugerir-titulo">${esc(t('ui.sugerir.titulo'))}</h2>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="${esc(t('comun.cerrar'))}"></button>
                </div>
                <div class="modal-body pt-0">
                    <p class="small text-secondary">${esc(t('ui.sugerir.ayuda'))}</p>
                    <label class="form-label" for="sf-sugerir-nombre">${esc(t('ui.sugerir.nombre'))}</label>
                    <input type="text" class="form-control" id="sf-sugerir-nombre" maxlength="100" placeholder="${esc(t('ui.sugerir.nombreEjemplo'))}">
                    <div class="invalid-feedback" data-error-nombre></div>
                    <label class="form-label mt-3" for="sf-sugerir-plataformas">${esc(t('ui.sugerir.plataformas'))} <span class="text-secondary">${esc(t('ui.sugerir.opcional'))}</span></label>
                    <input type="text" class="form-control" id="sf-sugerir-plataformas" maxlength="100" placeholder="${esc(t('ui.sugerir.plataformasEjemplo'))}">
                </div>
                <div class="modal-footer border-0">
                    <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">${esc(t('comun.cancelar'))}</button>
                    <button type="submit" class="btn btn-primary">${esc(t('ui.sugerir.enviar'))}</button>
                </div>
            </form>
        </div>`;
    document.body.appendChild(modal);
    const instancia = new bootstrap.Modal(modal);
    const nombre = modal.querySelector('#sf-sugerir-nombre');
    const error = modal.querySelector('[data-error-nombre]');
    const boton = modal.querySelector('button[type="submit"]');

    function marcarError(mensaje) {
        error.textContent = mensaje;
        nombre.classList.toggle('is-invalid', Boolean(mensaje));
    }

    modal.querySelector('form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const texto = nombre.value.trim();
        const datos = { game_name: texto, platforms_note: modal.querySelector('#sf-sugerir-plataformas').value.trim() || null };
        if (texto.length < 2) return marcarError(t('ui.sugerir.falta'));
        const { juegos } = await catalogo();
        if (juegos.some((j) => j.name.toLowerCase() === texto.toLowerCase())) {
            return marcarError(t('ui.sugerir.existe'));
        }
        marcarError('');

        if (alEnviar) {
            alEnviar(datos);
        } else {
            boton.disabled = true;
            try {
                await api('/catalog/game-requests', { method: 'POST', body: datos });
            } catch (err) {
                boton.disabled = false;
                if (['GAME_EXISTS', 'REQUEST_PENDING', 'VALIDATION_ERROR'].includes(err.code)) return marcarError(err.message);
                return avisarError(err);
            }
        }
        instancia.hide();
        mostrarToast(t('ui.sugerir.gracias', { juego: texto }));
    });

    modal.addEventListener('hidden.bs.modal', () => modal.remove());
    instancia.show();
}

/* ---------------------------------------------------------------------
   Ventana para reportar a un jugador (CREATE user_report)
   alEnviar(reporte) se llama cuando el reporte es válido.
   --------------------------------------------------------------------- */
function abrirReporte({ usuarioId, username, postId = null, alEnviar = () => {} }) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.tabIndex = -1;
    modal.setAttribute('aria-labelledby', 'sf-reporte-titulo');
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <form class="modal-content sf-modal" novalidate>
                <div class="modal-header border-0">
                    <h2 class="modal-title h5" id="sf-reporte-titulo">${esc(t('ui.reporte.titulo', { usuario: username }))}</h2>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="${esc(t('comun.cerrar'))}"></button>
                </div>
                <div class="modal-body pt-0">
                    <p class="small text-secondary">${esc(t('ui.reporte.ayuda'))}</p>
                    <fieldset class="mb-3">
                        <legend class="form-label fs-6">${esc(t('ui.reporte.quePaso'))}</legend>
                        <div class="d-grid gap-2">
                            ${Object.entries(MOTIVOS_REPORTE).map(([valor, m]) => `
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="motivo" id="motivo-${valor}" value="${valor}">
                                    <label class="form-check-label" for="motivo-${valor}">${m.icono} ${esc(m.texto)}</label>
                                </div>`).join('')}
                        </div>
                        <div class="text-danger small mt-1 d-none" data-error-motivo role="alert">${esc(t('ui.reporte.elegirMotivo'))}</div>
                    </fieldset>
                    <label class="form-label" for="sf-reporte-comentario">${esc(t('ui.reporte.cuentale'))}</label>
                    <textarea class="form-control" id="sf-reporte-comentario" rows="3" maxlength="500"
                        placeholder="${esc(t('ui.reporte.ejemplo'))}"></textarea>
                    <div class="invalid-feedback" data-error-comentario></div>
                    <div class="form-text text-end"><span data-contador>0</span>/500</div>
                    <div class="alert alert-warning small mt-3 mb-0">
                        ${esc(t('ui.reporte.evidencia'))}
                    </div>
                </div>
                <div class="modal-footer border-0">
                    <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">${esc(t('comun.cancelar'))}</button>
                    <button type="submit" class="btn btn-danger">${esc(t('ui.reporte.enviar'))}</button>
                </div>
            </form>
        </div>`;
    document.body.appendChild(modal);
    const instancia = new bootstrap.Modal(modal);
    const form = modal.querySelector('form');
    const comentario = form.querySelector('textarea');
    const errorComentario = form.querySelector('[data-error-comentario]');

    comentario.addEventListener('input', () => {
        form.querySelector('[data-contador]').textContent = comentario.value.length;
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const motivo = form.querySelector('input[name="motivo"]:checked')?.value;
        const texto = comentario.value.trim();
        form.querySelector('[data-error-motivo]').classList.toggle('d-none', Boolean(motivo));
        errorComentario.textContent = t('ui.reporte.minimo');
        comentario.classList.toggle('is-invalid', texto.length < 10);
        if (!motivo || texto.length < 10) return;

        const boton = e.submitter ?? e.target.querySelector('button[type="submit"]');
        boton.disabled = true;
        try {
            await api('/reports', {
                method: 'POST',
                body: { reported_user_id: usuarioId, post_id: postId, reason: motivo, comment: texto },
            });
        } catch (err) {
            boton.disabled = false;
            // El servidor valida que ambos hayan jugado juntos y que no se reporte dos veces
            if (err.code === 'ALREADY_REPORTED') alEnviar();
            instancia.hide();
            return avisarError(err, t('ui.reporte.error'));
        }
        alEnviar();
        instancia.hide();
        mostrarToast(t('ui.reporte.enviado', { usuario: username }));
    });

    modal.addEventListener('hidden.bs.modal', () => modal.remove());
    instancia.show();
}

// Lee ?id=123 de la dirección de la página
function idDeUrl(valorPorDefecto = null) {
    const id = Number(new URLSearchParams(location.search).get('id'));
    return Number.isInteger(id) && id > 0 ? id : valorPorDefecto;
}

// Activa la validación visual de Bootstrap en un formulario.
// alEnviar(form) solo se llama si todos los campos son válidos.
function validarFormulario(form, alEnviar) {
    form.setAttribute('novalidate', '');
    form.addEventListener('submit', (evento) => {
        evento.preventDefault();
        const valido = form.checkValidity();
        form.classList.add('was-validated');
        if (valido) alEnviar(form);
    });
}

/* ---------------------------------------------------------------------
   Barra de navegación y arranque de cada página con sesión
   --------------------------------------------------------------------- */
// Pone la foto (o el avatar) del usuario en el menú superior
function pintarAvatarNavbar(usuario = _yo) {
    const actual = document.getElementById('nav-avatar');
    if (!actual) return;
    const plantilla = document.createElement('template');
    plantilla.innerHTML = avatar(usuario.username, 'sf-avatar-sm', usuario.avatar_url);
    const nuevo = plantilla.content.firstElementChild;
    nuevo.id = 'nav-avatar';
    actual.replaceWith(nuevo);
}

// Aviso dentro de la página cuando no se puede cargar (por ejemplo, la API está apagada)
function mostrarErrorPagina(mensaje) {
    document.getElementById('contenido')?.insertAdjacentHTML('afterbegin', `
        <div class="alert alert-danger mt-3" role="alert">
            <strong>${esc(t('ui.errorPagina'))}</strong> ${esc(mensaje)}
            <button type="button" class="btn btn-sm btn-outline-light ms-2" data-sf-reintentar>${esc(t('ui.reintentar'))}</button>
        </div>`);
    document.querySelector('[data-sf-reintentar]')?.addEventListener('click', () => location.reload());
}

// Opción del menú de usuario para alternar español / inglés (se guarda en el perfil)
function agregarBotonIdioma() {
    const salir = document.getElementById('btn-logout').closest('li');
    salir.previousElementSibling.insertAdjacentHTML('beforebegin',
        '<li><button class="dropdown-item" id="btn-idioma" type="button"></button></li>');
    const boton = document.getElementById('btn-idioma');
    boton.textContent = t('comun.idiomaBoton');
    boton.setAttribute('aria-label', t('comun.idiomaEtiqueta'));
    boton.addEventListener('click', async () => {
        const otro = i18next.language === 'es' ? 'en' : 'es';
        try {
            await api('/users/me', { method: 'PUT', body: { ui_language: otro } });
        } catch { /* si falla, igual se cambia en este navegador */ }
        await cambiarIdioma(otro);
    });
}

async function iniciarNavbar() {
    const nombre = document.getElementById('nav-username');
    if (!nombre) return null;
    await i18nListo;
    document.getElementById('btn-logout').addEventListener('click', async () => {
        const ok = await confirmar({ titulo: t('nav.salirTitulo'), mensaje: t('nav.salirMensaje'), textoBoton: t('nav.salir'), peligro: false });
        if (ok) await cerrarSesion();
    });

    let yo;
    try {
        yo = await usuarioActual();
    } catch (e) {
        if (e.code === 'NETWORK_ERROR') mostrarErrorPagina(e.message);
        return null;
    }
    // El idioma del perfil manda: si es distinto al de este navegador, se cambia y se recarga
    if (IDIOMAS_UI.includes(yo.ui_language) && yo.ui_language !== i18next.language) {
        await cambiarIdioma(yo.ui_language);
        return null;
    }
    nombre.textContent = yo.username;
    pintarAvatarNavbar(yo);
    agregarBotonIdioma();
    document.getElementById('nav-perfil-publico').href = `usuario.html?id=${yo.id}`;

    // Solo los administradores ven el panel de moderación
    if (yo.role === 'ADMIN') {
        const pendientes = (await api('/admin/reports', { params: { status: 'PENDING' } }).catch(() => [])).length;
        const enPagina = location.pathname.endsWith('admin_reportes.html');
        document.getElementById('btn-logout').closest('li').previousElementSibling.insertAdjacentHTML('beforebegin', `
            <li><a class="dropdown-item d-flex justify-content-between align-items-center gap-3 ${enPagina ? 'active' : ''}"
                   href="admin_reportes.html" ${enPagina ? 'aria-current="page"' : ''}>
                🛡️ ${esc(t('nav.moderacion'))} ${pendientes ? `<span class="badge text-bg-danger">${pendientes}</span>` : ''}</a></li>`);
    }
    return yo;
}

const _navbarLista = new Promise((listo) => {
    document.addEventListener('DOMContentLoaded', () => listo(iniciarNavbar()));
});

// Cada página con sesión empieza con: const yo = await iniciarPagina();
// Si no hay sesión, api() ya redirigió al login y la página no sigue.
async function iniciarPagina() {
    const yo = await _navbarLista;
    if (!yo) throw new Error(t('ui.sinSesion'));
    return yo;
}
