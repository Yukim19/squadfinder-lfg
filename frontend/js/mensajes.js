/* =====================================================================
   SquadFinder LFG - Amigos y mensajes privados (estilo Discord)
   Requiere: i18n.js, api.js, catalogo.js y ui.js (en ese orden).

   Qué hace:
     - Botón 💬 en la barra con el total de mensajes sin leer y solicitudes pendientes.
     - Panel lateral con tres pestañas: Chats (tus amigos), Solicitudes y Agregar (buscador).
     - Conversación en vivo por WebSocket con el servicio de chat (/ws/dm).
     - htmlMensajesDiscord(): pinta mensajes agrupados con separadores de día; lo usa también
       el chat de las salas, para que todo se vea igual.
   ===================================================================== */

/* ---------------------------------------------------------------------
   Mensajes estilo Discord (compartido con chat_sala.html)
   --------------------------------------------------------------------- */
const colorNombre = (id) => `hsl(${(Number(id) * 47 + 20) % 360} 80% 72%)`;
const horaCorta = (fecha) => fecha.toLocaleTimeString(i18next.language, { hour: '2-digit', minute: '2-digit' });

function etiquetaDia(fecha) {
    const hoy = new Date();
    const ayer = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1);
    if (fecha.toDateString() === hoy.toDateString()) return t('amigos.hoy');
    if (fecha.toDateString() === ayer.toDateString()) return t('amigos.ayer');
    return fecha.toLocaleDateString(i18next.language, { day: 'numeric', month: 'long', year: 'numeric' });
}

// mensajes: lista de { sender_id, message, hidden, sent_at }
// opciones.quien(m) devuelve { username, avatar_url }; opciones.nivel es el filtro del lector
function htmlMensajesDiscord(mensajes, { nivel, quien }) {
    let html = '';
    let previo = null;
    for (const m of mensajes) {
        const fecha = new Date(m.sent_at);
        const dia = fecha.toDateString();
        const nuevoDia = !previo || previo.dia !== dia;
        if (nuevoDia) html += `<div class="sf-dc-dia"><span>${esc(etiquetaDia(fecha))}</span></div>`;
        // Mensajes seguidos de la misma persona (menos de 5 minutos) se agrupan sin repetir el nombre
        const agrupado = !nuevoDia && previo.sender_id === m.sender_id && fecha - previo.fecha < 5 * 60 * 1000;
        const texto = m.hidden
            ? `<span class="sf-msg-oculto">${esc(t('amigos.oculto', { nivel: NIVELES_FILTRO[nivel] }))}</span>`
            : esc(m.message);
        const hora = horaCorta(fecha);
        if (agrupado) {
            html += `<div class="sf-dc-msg sf-dc-agrupado"><span class="sf-dc-hora-lado">${esc(hora)}</span>
                <div class="sf-dc-texto">${texto}</div></div>`;
        } else {
            const u = quien(m);
            html += `<div class="sf-dc-msg"><div class="sf-dc-lado">${avatar(u.username, '', u.avatar_url)}</div>
                <div><div class="sf-dc-cabecera"><span class="sf-dc-nombre" style="color: ${colorNombre(m.sender_id)}">${esc(u.username)}</span>
                <time datetime="${esc(m.sent_at)}">${esc(hora)}</time></div>
                <div class="sf-dc-texto">${texto}</div></div></div>`;
        }
        previo = { dia, sender_id: m.sender_id, fecha };
    }
    return html;
}

/* ---------------------------------------------------------------------
   Estado del panel de mensajes
   --------------------------------------------------------------------- */
const DM = {
    yo: null,
    ws: null,
    intentos: 0,
    amigos: [],                 // { user_id, username, avatar_url, level, unread, last_message_at }
    enLinea: new Set(),         // ids de amigos conectados ahora
    solicitudes: { incoming: [], outgoing: [] },
    abierto: null,              // id del amigo con quien se está chateando
    cache: new Map(),           // id del amigo -> mensajes ya cargados
    pestana: 'chats',
    panel: null,
    offcanvas: null,
    visible: false,
    busqueda: 0,                // para ignorar respuestas viejas del buscador
};

const amigoPorId = (id) => DM.amigos.find((a) => a.user_id === Number(id));
const sinLeer = () => DM.amigos.reduce((suma, a) => suma + a.unread, 0);

/* ---------------------------------------------------------------------
   Datos desde la API
   --------------------------------------------------------------------- */
async function cargarAmigos() {
    DM.amigos = await api('/friends');
    pintarLista();
    pintarInsignia();
}

async function cargarSolicitudes() {
    DM.solicitudes = await api('/friends/requests');
    pintarSolicitudes();
    pintarInsignia();
}

async function refrescarTodo() {
    try {
        await Promise.all([cargarAmigos(), cargarSolicitudes()]);
    } catch { /* si la API no responde, se reintenta en el próximo ciclo */ }
}

function pintarInsignia() {
    const total = sinLeer() + DM.solicitudes.incoming.length;
    const insignia = document.querySelector('#btn-mensajes .sf-dm-insignia');
    if (!insignia) return;
    insignia.textContent = total > 99 ? '99+' : total;
    insignia.classList.toggle('d-none', total === 0);
}

/* ---------------------------------------------------------------------
   WebSocket
   --------------------------------------------------------------------- */
async function conectarDM() {
    let token;
    try { token = await tokenChat(); } catch { return; }
    DM.ws = new WebSocket(CONFIG.DM_URL);
    DM.ws.onopen = () => DM.ws.send(JSON.stringify({ type: 'auth', token }));
    DM.ws.onmessage = (evento) => recibirDM(JSON.parse(evento.data));
    DM.ws.onclose = (evento) => {
        DM.enLinea.clear();
        pintarLista();
        pintarCabecera();
        // 4401/4403: sesión inválida o sin permiso; no tiene sentido reintentar
        if ([4401, 4403].includes(evento.code)) return;
        DM.intentos += 1;
        setTimeout(conectarDM, Math.min(15000, 1000 * 2 ** (DM.intentos - 1)));
    };
}

function recibirDM(d) {
    if (d.type === 'ready') {
        DM.intentos = 0;
        DM.enLinea = new Set(d.online);
        refrescarTodo();
        pintarCabecera();
    } else if (d.type === 'presence') {
        if (d.online) DM.enLinea.add(d.user_id); else DM.enLinea.delete(d.user_id);
        pintarLista();
        pintarCabecera();
    } else if (d.type === 'message') {
        const mio = d.sender_id === DM.yo.id;
        const otroId = mio ? d.recipient_id : d.sender_id;
        const amigo = amigoPorId(otroId);
        if (!amigo) return void refrescarTodo();
        if (DM.cache.has(otroId)) DM.cache.get(otroId).push(d);
        amigo.last_message_at = d.sent_at;
        DM.amigos = [amigo, ...DM.amigos.filter((a) => a !== amigo)];
        const leyendo = DM.visible && DM.abierto === otroId;
        if (!mio) {
            if (leyendo) marcarLeido(otroId);
            else {
                amigo.unread += 1;
                mostrarToast(d.hidden ? t('amigos.nuevoMensajeOculto', { usuario: amigo.username })
                    : t('amigos.nuevoMensaje', { usuario: amigo.username, texto: d.message.slice(0, 80) }), 'info');
            }
        }
        pintarLista();
        pintarInsignia();
        if (DM.abierto === otroId) pintarMensajes();
    } else if (d.type === 'read') {
        const amigo = amigoPorId(d.with);
        if (amigo) amigo.unread = 0;
        pintarLista();
        pintarInsignia();
    } else if (d.type === 'error') {
        mostrarToast(i18next.exists(`errores.${d.code}`) ? t(`errores.${d.code}`) : d.message, 'danger');
    }
}

function marcarLeido(id) {
    const amigo = amigoPorId(id);
    if (amigo) amigo.unread = 0;
    if (DM.ws?.readyState === 1) DM.ws.send(JSON.stringify({ type: 'read', with: id }));
    else api(`/dm/${id}/read`, { method: 'POST', base: CONFIG.CHAT_API }).catch(() => {});
    pintarLista();
    pintarInsignia();
}

/* ---------------------------------------------------------------------
   Pintar el panel
   --------------------------------------------------------------------- */
function filaAmigo(a) {
    const activa = DM.abierto === a.user_id ? 'activa' : '';
    return `<button type="button" class="sf-dm-fila ${activa}" data-amigo="${a.user_id}">
        <span class="sf-av-wrap">${avatar(a.username, 'sf-avatar-sm', a.avatar_url)}
            <span class="sf-punto ${DM.enLinea.has(a.user_id) ? 'en-linea' : ''}"></span></span>
        <span class="sf-dm-nombre">${esc(a.username)}</span>
        ${a.unread ? `<span class="sf-dm-insignia">${a.unread}</span>` : ''}</button>`;
}

function pintarLista() {
    const cont = document.getElementById('sf-dm-chats');
    if (!cont) return;
    cont.innerHTML = DM.amigos.length
        ? DM.amigos.map(filaAmigo).join('')
        : `<p class="sf-dm-vacio">${esc(t('amigos.sinAmigos'))}</p>`;
}

function pintarSolicitudes() {
    const cont = document.getElementById('sf-dm-solicitudes');
    if (!cont) return;
    const fila = (s, botones) => `<div class="sf-dm-fila">
        <span class="sf-av-wrap">${avatar(s.username, 'sf-avatar-sm', s.avatar_url)}</span>
        <span class="sf-dm-nombre">${esc(s.username)}</span>${botones}</div>`;
    const { incoming, outgoing } = DM.solicitudes;
    if (!incoming.length && !outgoing.length) {
        cont.innerHTML = `<p class="sf-dm-vacio">${esc(t('amigos.sinSolicitudes'))}</p>`;
        return;
    }
    cont.innerHTML = (incoming.length ? `<h3 class="h6 text-secondary px-2 mt-2">${esc(t('amigos.recibidas'))}</h3>` : '')
        + incoming.map((s) => fila(s, `<button class="btn btn-sm btn-success" data-aceptar="${s.id}" data-usuario="${esc(s.username)}">${esc(t('amigos.aceptar'))}</button>
            <button class="btn btn-sm btn-outline-light" data-rechazar="${s.id}">${esc(t('amigos.rechazar'))}</button>`)).join('')
        + (outgoing.length ? `<h3 class="h6 text-secondary px-2 mt-3">${esc(t('amigos.enviadas'))}</h3>` : '')
        + outgoing.map((s) => fila(s, `<button class="btn btn-sm btn-outline-light" data-cancelar="${s.user_id}">${esc(t('amigos.cancelar'))}</button>`)).join('');
}

function pintarCabecera() {
    const cab = document.getElementById('sf-dm-cab');
    const amigo = amigoPorId(DM.abierto);
    document.getElementById('sf-dm-vacio').classList.toggle('d-none', Boolean(amigo));
    document.getElementById('sf-dm-hilo').classList.toggle('d-none', !amigo);
    if (!amigo) return;
    const conectado = DM.enLinea.has(amigo.user_id);
    cab.innerHTML = `<button type="button" class="btn btn-sm btn-outline-light sf-dm-atras" data-atras aria-label="${esc(t('amigos.atras'))}">←</button>
        <span class="sf-av-wrap">${avatar(amigo.username, '', amigo.avatar_url)}<span class="sf-punto ${conectado ? 'en-linea' : ''}"></span></span>
        <div class="flex-grow-1"><div class="fw-semibold" style="color: ${colorNombre(amigo.user_id)}">${esc(amigo.username)}</div>
            <small class="text-secondary">${esc(conectado ? t('amigos.enLinea') : t('amigos.desconectado'))}</small></div>
        <a class="btn btn-sm btn-outline-light" href="usuario.html?id=${amigo.user_id}">${esc(t('amigos.verPerfil'))}</a>
        <button type="button" class="btn btn-sm btn-outline-danger" data-quitar="${amigo.user_id}">${esc(t('amigos.quitarAmigo'))}</button>`;
    document.getElementById('sf-dm-texto').placeholder = t('amigos.escribeA', { usuario: amigo.username });
}

function pintarMensajes() {
    const caja = document.getElementById('sf-dm-msgs');
    const amigo = amigoPorId(DM.abierto);
    const mensajes = DM.cache.get(DM.abierto) ?? [];
    caja.innerHTML = mensajes.length
        ? htmlMensajesDiscord(mensajes, {
            nivel: DM.yo.toxicity_filter_level,
            quien: (m) => (m.sender_id === DM.yo.id ? DM.yo : amigo),
        })
        : `<p class="sf-dc-vacio">${esc(t('amigos.sinMensajes', { usuario: amigo?.username ?? '' }))}</p>`;
    caja.scrollTop = caja.scrollHeight;
}

async function abrirConversacion(id) {
    DM.abierto = Number(id);
    DM.panel.classList.add('con-conversacion');
    pintarLista();
    pintarCabecera();
    if (!DM.cache.has(DM.abierto)) {
        document.getElementById('sf-dm-msgs').innerHTML = '';
        try {
            DM.cache.set(DM.abierto, await api(`/dm/${DM.abierto}/history`, { base: CONFIG.CHAT_API, params: { limit: 50 } }));
        } catch (e) {
            return avisarError(e);
        }
    }
    pintarMensajes();
    if (amigoPorId(DM.abierto)?.unread) marcarLeido(DM.abierto);
    document.getElementById('sf-dm-texto').focus();
}

/* ---------------------------------------------------------------------
   Buscador y acciones de amistad
   --------------------------------------------------------------------- */
function botonResultado(j) {
    if (j.friendship === 'FRIENDS') return `<button class="btn btn-sm btn-outline-light" data-mensaje="${j.id}">${esc(t('amigos.mensaje'))}</button>`;
    if (j.friendship === 'REQUEST_SENT') return `<span class="badge text-bg-secondary">${esc(t('amigos.enviada'))}</span>`;
    if (j.friendship === 'REQUEST_RECEIVED') return `<button class="btn btn-sm btn-success" data-aceptar-usuario="${j.id}" data-usuario="${esc(j.username)}">${esc(t('amigos.aceptar'))}</button>`;
    return `<button class="btn btn-sm btn-primary" data-agregar="${j.id}" data-usuario="${esc(j.username)}">${esc(t('amigos.agregar'))}</button>`;
}

async function buscarJugadores(texto) {
    const cont = document.getElementById('sf-dm-resultados');
    const numero = ++DM.busqueda;
    if (texto.trim().length < 2) {
        cont.innerHTML = `<p class="sf-dm-vacio">${esc(t('amigos.buscarAyuda'))}</p>`;
        return;
    }
    let jugadores;
    try {
        jugadores = await api('/users/search', { params: { q: texto.trim() } });
    } catch (e) {
        return avisarError(e);
    }
    if (numero !== DM.busqueda) return; // llegó una respuesta de una búsqueda anterior
    cont.innerHTML = jugadores.length
        ? jugadores.map((j) => `<div class="sf-dm-fila"><span class="sf-av-wrap">${avatar(j.username, 'sf-avatar-sm', j.avatar_url)}</span>
            <a class="sf-dm-nombre text-reset text-decoration-none" href="usuario.html?id=${j.id}">${esc(j.username)}</a>${botonResultado(j)}</div>`).join('')
        : `<p class="sf-dm-vacio">${esc(t('amigos.sinResultados'))}</p>`;
}

// Acciones reutilizables (también las usa el botón del perfil)
async function agregarAmigo(userId, username) {
    const r = await api('/friends/requests', { method: 'POST', body: { user_id: Number(userId) } });
    mostrarToast(t(r.status === 'ACCEPTED' ? 'amigos.ahoraAmigos' : 'amigos.solicitudEnviada', { usuario: username }));
    await refrescarTodo();
    return r.status;
}

async function responderSolicitud(requestId, aceptar, username = '') {
    await api(`/friends/requests/${requestId}`, { method: 'PUT', body: { status: aceptar ? 'ACCEPTED' : 'REJECTED' } });
    mostrarToast(aceptar ? t('amigos.aceptada', { usuario: username }) : t('amigos.rechazada'), aceptar ? undefined : 'info');
    await refrescarTodo();
}

async function aceptarSolicitudDe(userId, username) {
    await cargarSolicitudes();
    const solicitud = DM.solicitudes.incoming.find((s) => s.user_id === Number(userId));
    if (solicitud) await responderSolicitud(solicitud.id, true, username);
}

async function eliminarAmistad(userId) {
    await api(`/friends/${userId}`, { method: 'DELETE' });
    DM.cache.delete(Number(userId));
    await refrescarTodo();
}

function abrirMensajes(userId = null) {
    if (!DM.offcanvas) return;
    DM.offcanvas.show();
    if (userId) {
        cambiarPestana('chats');
        abrirConversacion(userId);
    }
}

function cambiarPestana(nombre) {
    DM.pestana = nombre;
    for (const boton of DM.panel.querySelectorAll('[data-pestana]')) {
        boton.setAttribute('aria-selected', boton.dataset.pestana === nombre);
        document.getElementById(`sf-dm-p-${boton.dataset.pestana}`).hidden = boton.dataset.pestana !== nombre;
    }
    if (nombre === 'solicitudes') cargarSolicitudes().catch(() => {});
    if (nombre === 'agregar') document.getElementById('sf-dm-buscar').focus();
}

/* ---------------------------------------------------------------------
   Construcción del panel y arranque
   --------------------------------------------------------------------- */
function construirPanel() {
    const panel = document.createElement('div');
    panel.className = 'offcanvas offcanvas-end sf-dm';
    panel.id = 'sf-dm';
    panel.tabIndex = -1;
    panel.setAttribute('aria-labelledby', 'sf-dm-titulo');
    panel.innerHTML = `
        <div class="offcanvas-header">
            <h2 class="offcanvas-title h5" id="sf-dm-titulo">${esc(t('amigos.titulo'))}</h2>
            <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="${esc(t('comun.cerrar'))}"></button>
        </div>
        <div class="offcanvas-body">
            <aside class="sf-dm-lista">
                <div class="sf-dm-pestanas" role="tablist">
                    <button type="button" role="tab" data-pestana="chats" aria-selected="true">${esc(t('amigos.pestanaChats'))}</button>
                    <button type="button" role="tab" data-pestana="solicitudes" aria-selected="false">${esc(t('amigos.pestanaSolicitudes'))}</button>
                    <button type="button" role="tab" data-pestana="agregar" aria-selected="false">${esc(t('amigos.pestanaAgregar'))}</button>
                </div>
                <div class="sf-dm-contenido">
                    <div id="sf-dm-p-chats"><div id="sf-dm-chats"></div></div>
                    <div id="sf-dm-p-solicitudes" hidden><div id="sf-dm-solicitudes"></div></div>
                    <div id="sf-dm-p-agregar" hidden>
                        <input type="search" class="form-control my-2" id="sf-dm-buscar" autocomplete="off"
                            placeholder="${esc(t('amigos.buscar'))}" aria-label="${esc(t('amigos.buscar'))}">
                        <div id="sf-dm-resultados"><p class="sf-dm-vacio">${esc(t('amigos.buscarAyuda'))}</p></div>
                    </div>
                </div>
            </aside>
            <section class="sf-dm-conv">
                <p class="sf-dm-vacio" id="sf-dm-vacio">${esc(t('amigos.elegirChat'))}</p>
                <div class="d-none d-flex flex-column flex-grow-1" id="sf-dm-hilo" style="min-height: 0">
                    <div class="sf-dm-conv-cabecera" id="sf-dm-cab"></div>
                    <div class="sf-dc" id="sf-dm-msgs" role="log" aria-live="polite" tabindex="0"></div>
                    <form id="sf-dm-form">
                        <div class="sf-dc-compositor">
                            <textarea id="sf-dm-texto" rows="1" maxlength="500" required></textarea>
                            <button class="btn btn-primary" type="submit">${esc(t('amigos.enviar'))}</button>
                        </div>
                    </form>
                </div>
            </section>
        </div>`;
    document.body.appendChild(panel);
    return panel;
}

function conectarEventosDelPanel() {
    const panel = DM.panel;
    panel.addEventListener('shown.bs.offcanvas', () => { DM.visible = true; if (DM.abierto) marcarLeido(DM.abierto); });
    panel.addEventListener('hidden.bs.offcanvas', () => { DM.visible = false; });

    panel.addEventListener('click', async (e) => {
        const b = e.target.closest('button');
        if (!b) return;
        try {
            if (b.dataset.pestana) cambiarPestana(b.dataset.pestana);
            if (b.dataset.amigo) abrirConversacion(b.dataset.amigo);
            if (b.dataset.mensaje) { cambiarPestana('chats'); abrirConversacion(b.dataset.mensaje); }
            if (b.hasAttribute('data-atras')) { DM.abierto = null; panel.classList.remove('con-conversacion'); pintarLista(); pintarCabecera(); }
            if (b.dataset.agregar) { await agregarAmigo(b.dataset.agregar, b.dataset.usuario); buscarJugadores(document.getElementById('sf-dm-buscar').value); }
            if (b.dataset.aceptar) await responderSolicitud(b.dataset.aceptar, true, b.dataset.usuario);
            if (b.dataset.aceptarUsuario) { await aceptarSolicitudDe(b.dataset.aceptarUsuario, b.dataset.usuario); buscarJugadores(document.getElementById('sf-dm-buscar').value); }
            if (b.dataset.rechazar) await responderSolicitud(b.dataset.rechazar, false);
            if (b.dataset.cancelar) { await eliminarAmistad(b.dataset.cancelar); mostrarToast(t('amigos.cancelada'), 'info'); }
            if (b.dataset.quitar) {
                const amigo = amigoPorId(b.dataset.quitar);
                const ok = await confirmar({ titulo: t('amigos.quitarTitulo'), mensaje: t('amigos.quitarMensaje', { usuario: amigo.username }), textoBoton: t('amigos.quitarBoton') });
                if (ok) {
                    await eliminarAmistad(amigo.user_id);
                    DM.abierto = null;
                    panel.classList.remove('con-conversacion');
                    pintarCabecera();
                    mostrarToast(t('amigos.quitado', { usuario: amigo.username }), 'info');
                }
            }
        } catch (err) {
            avisarError(err);
        }
    });

    let espera;
    document.getElementById('sf-dm-buscar').addEventListener('input', (e) => {
        clearTimeout(espera);
        espera = setTimeout(() => buscarJugadores(e.target.value), 300);
    });

    // Enter envía; Shift+Enter agrega una línea (como en Discord)
    const texto = document.getElementById('sf-dm-texto');
    texto.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.getElementById('sf-dm-form').requestSubmit();
        }
    });
    texto.addEventListener('input', () => {
        texto.style.height = 'auto';
        texto.style.height = `${Math.min(texto.scrollHeight, 128)}px`;
    });
    document.getElementById('sf-dm-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const mensaje = texto.value.trim();
        if (!mensaje || !DM.abierto) return;
        if (DM.ws?.readyState !== 1) return mostrarToast(t('amigos.conexionPerdida'), 'danger');
        // El mensaje aparece cuando el servidor lo confirma (eco), así lo que ves es lo que se guardó
        DM.ws.send(JSON.stringify({ type: 'message', to: DM.abierto, message: mensaje }));
        texto.value = '';
        texto.style.height = 'auto';
    });
}

async function iniciarMensajes(yo) {
    if (DM.panel) return;
    DM.yo = yo;
    // Botón 💬 en la barra, antes del menú de usuario
    const menuUsuario = document.querySelector('.sf-navbar .navbar-nav .dropdown');
    if (!menuUsuario) return;
    menuUsuario.insertAdjacentHTML('beforebegin', `
        <button type="button" class="nav-link btn btn-link" id="btn-mensajes" aria-label="${esc(t('amigos.boton'))}">
            💬 <span class="d-lg-none">${esc(t('amigos.boton'))}</span><span class="sf-dm-insignia d-none">0</span></button>`);
    DM.panel = construirPanel();
    DM.offcanvas = new bootstrap.Offcanvas(DM.panel);
    document.getElementById('btn-mensajes').addEventListener('click', () => abrirMensajes());
    conectarEventosDelPanel();
    await refrescarTodo();
    conectarDM();
    setInterval(refrescarTodo, 60000); // por si algo cambió mientras no había conexión
}
