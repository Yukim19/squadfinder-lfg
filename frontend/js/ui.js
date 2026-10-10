/* =====================================================================
   SquadFinder LFG - Componentes de interfaz compartidos
   Requiere: Bootstrap (bundle) y js/catalogo.js cargados antes.
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
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button>
        </div>`;
    zona.appendChild(toast);
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
    bootstrap.Toast.getOrCreateInstance(toast, { delay: 3500 }).show();
}

/* ---------------------------------------------------------------------
   Ventana de confirmación para acciones que no se pueden deshacer.
   Devuelve una Promesa: true si el usuario confirma, false si cancela.
   --------------------------------------------------------------------- */
function confirmar({ titulo, mensaje, textoBoton = 'Confirmar', peligro = true }) {
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
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
                    </div>
                    <div class="modal-body pt-0 text-secondary">${esc(mensaje)}</div>
                    <div class="modal-footer border-0">
                        <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Cancelar</button>
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

function avatar(username, tamano = '') {
    return `<span class="sf-avatar ${tamano}" aria-hidden="true">${esc(String(username)[0] ?? '?')}</span>`;
}

function badgeHonor(score) {
    return `<span class="badge sf-badge-honor">Honor ${Number(score).toFixed(1)}</span>`;
}

function estrellas(rating) {
    const n = Math.round(Number(rating));
    return `<span class="sf-stars" aria-label="${n} de 5 estrellas">${'★'.repeat(n)}<span class="sf-stars-off">${'★'.repeat(5 - n)}</span></span>`;
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
function calcularCompatibilidad(sala, usuario = USUARIO_DEMO) {
    let puntos = 0;
    if (usuario.juegos.includes(sala.game_id)) puntos += 40;
    if (sala.required_language === 'any' || sala.required_language === usuario.preferred_language_speak) puntos += 30;
    if (sala.host_region === usuario.region) puntos += 30;
    return puntos;
}

/* ---------------------------------------------------------------------
   Ventana para reportar a un jugador (CREATE user_report)
   alEnviar(reporte) se llama cuando el reporte es válido.
   --------------------------------------------------------------------- */
function abrirReporte({ usuarioId, username, postId = null, alEnviar = () => {} }) {
    const evidencia = postId ? evidenciaChat(postId, usuarioId) : [];
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.tabIndex = -1;
    modal.setAttribute('aria-labelledby', 'sf-reporte-titulo');
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <form class="modal-content sf-modal" novalidate>
                <div class="modal-header border-0">
                    <h2 class="modal-title h5" id="sf-reporte-titulo">🚩 Reportar a ${esc(username)}</h2>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
                </div>
                <div class="modal-body pt-0">
                    <p class="small text-secondary">Un administrador revisará el reporte. Si se confirma, la cuenta puede ser suspendida o eliminada. Tu identidad no se le muestra a la persona reportada.</p>
                    <fieldset class="mb-3">
                        <legend class="form-label fs-6">¿Qué pasó?</legend>
                        <div class="d-grid gap-2">
                            ${Object.entries(MOTIVOS_REPORTE).map(([valor, m]) => `
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="motivo" id="motivo-${valor}" value="${valor}">
                                    <label class="form-check-label" for="motivo-${valor}">${m.icono} ${esc(m.texto)}</label>
                                </div>`).join('')}
                        </div>
                        <div class="text-danger small mt-1 d-none" data-error-motivo role="alert">Elige un motivo.</div>
                    </fieldset>
                    <label class="form-label" for="sf-reporte-comentario">Cuéntale al administrador qué ocurrió</label>
                    <textarea class="form-control" id="sf-reporte-comentario" rows="3" maxlength="500"
                        placeholder="Ej.: Me insultó en el chat después de perder la ronda."></textarea>
                    <div class="invalid-feedback" data-error-comentario></div>
                    <div class="form-text text-end"><span data-contador>0</span>/500</div>
                    ${evidencia.length ? `
                        <div class="alert alert-warning small mt-3 mb-0">
                            🛡️ El filtro anti-toxicidad marcó <strong>${evidencia.length}</strong> mensaje(s) de esta persona en esa partida.
                            Se adjuntarán al reporte como evidencia.
                        </div>` : ''}
                </div>
                <div class="modal-footer border-0">
                    <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-danger">Enviar reporte</button>
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

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const motivo = form.querySelector('input[name="motivo"]:checked')?.value;
        const texto = comentario.value.trim();
        form.querySelector('[data-error-motivo]').classList.toggle('d-none', Boolean(motivo));
        errorComentario.textContent = 'Escribe al menos 10 caracteres para que el administrador entienda qué pasó.';
        comentario.classList.toggle('is-invalid', texto.length < 10);
        if (!motivo || texto.length < 10) return;

        // Semana 3: POST /api/v1/reports
        alEnviar({ reported_user_id: usuarioId, post_id: postId, reason: motivo, comment: texto });
        instancia.hide();
        mostrarToast(`Reporte enviado. Un administrador revisará el caso de ${username}.`);
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
   Barra de navegación: datos del usuario y cerrar sesión
   --------------------------------------------------------------------- */
function iniciarNavbar() {
    const nombre = document.getElementById('nav-username');
    if (!nombre) return;
    nombre.textContent = USUARIO_DEMO.username;
    document.getElementById('nav-avatar').textContent = USUARIO_DEMO.username[0];
    document.getElementById('nav-perfil-publico').href = `usuario.html?id=${USUARIO_DEMO.id}`;

    // Solo los administradores ven el panel de moderación
    if (USUARIO_DEMO.role === 'ADMIN') {
        const pendientes = REPORTES_DEMO.filter((r) => r.status === 'PENDING').length;
        const enPagina = location.pathname.endsWith('admin_reportes.html');
        document.getElementById('btn-logout').closest('li').previousElementSibling.insertAdjacentHTML('beforebegin', `
            <li><a class="dropdown-item d-flex justify-content-between align-items-center gap-3 ${enPagina ? 'active' : ''}"
                   href="admin_reportes.html" ${enPagina ? 'aria-current="page"' : ''}>
                🛡️ Moderación ${pendientes ? `<span class="badge text-bg-danger">${pendientes}</span>` : ''}</a></li>`);
    }
    document.getElementById('btn-logout').addEventListener('click', async () => {
        const ok = await confirmar({ titulo: 'Cerrar sesión', mensaje: '¿Seguro que quieres salir de tu cuenta?', textoBoton: 'Cerrar sesión', peligro: false });
        if (ok) location.href = 'login.html'; // Semana 2: auth0.logout()
    });
}

document.addEventListener('DOMContentLoaded', iniciarNavbar);
