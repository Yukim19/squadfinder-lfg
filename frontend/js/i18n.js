/* =====================================================================
   SquadFinder LFG - Idiomas de la interfaz con i18next
   Requiere (en este orden): i18next (CDN), locales.js y luego este archivo.

   Cómo se usa:
     - Texto fijo en el HTML:  <span data-i18n="nav.salas">Salas</span>
       También: data-i18n-html (permite etiquetas), data-i18n-placeholder,
       data-i18n-aria-label y data-i18n-title.
     - Texto armado en JavaScript:  t('login.errorEntrar')  o  t('x', { fecha })
   El idioma se guarda en localStorage ('sf-idioma') y, con sesión iniciada,
   también en el perfil (users.ui_language).
   ===================================================================== */
const IDIOMAS_UI = ['es', 'en'];
const CLAVE_IDIOMA = 'sf-idioma';

function idiomaInicial() {
    try {
        const guardado = localStorage.getItem(CLAVE_IDIOMA);
        if (IDIOMAS_UI.includes(guardado)) return guardado;
    } catch { /* sin almacenamiento */ }
    // La plataforma es hispanohablante: el español es el idioma por defecto, sin importar el idioma
    // del navegador. Quien prefiera inglés lo elige en el menú (se guarda en su perfil).
    return 'es';
}

const t = (clave, opciones) => i18next.t(clave, opciones);

// Reemplaza los textos marcados con data-i18n* dentro de `raiz`
function aplicarTraducciones(raiz = document) {
    document.documentElement.lang = i18next.language;
    raiz.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
    // Solo con textos propios del proyecto (nunca con datos de usuarios)
    raiz.querySelectorAll('[data-i18n-html]').forEach((el) => { el.innerHTML = t(el.dataset.i18nHtml); });
    for (const [atributo, dataset] of [['placeholder', 'i18nPlaceholder'], ['aria-label', 'i18nAriaLabel'], ['title', 'i18nTitle']]) {
        raiz.querySelectorAll(`[data-i18n-${atributo}]`).forEach((el) => { el.setAttribute(atributo, t(el.dataset[dataset])); });
    }
    const titulo = document.querySelector('title[data-i18n]');
    if (titulo) document.title = t(titulo.dataset.i18n);
}

const i18nListo = i18next
    .init({ lng: idiomaInicial(), fallbackLng: 'es', resources: TRADUCCIONES, interpolation: { escapeValue: false } })
    .then(() => {
        const aplicar = () => aplicarTraducciones();
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', aplicar);
        else aplicar();
    });

// Cambia el idioma, lo recuerda y recarga la página para volver a pintar todo
async function cambiarIdioma(idioma, { recargar = true } = {}) {
    if (!IDIOMAS_UI.includes(idioma) || idioma === i18next.language) return;
    let recordado = false;
    try {
        localStorage.setItem(CLAVE_IDIOMA, idioma);
        recordado = localStorage.getItem(CLAVE_IDIOMA) === idioma;
    } catch { /* sin almacenamiento (modo privado) */ }
    await i18next.changeLanguage(idioma);
    // Si el navegador no puede recordar la elección, recargar lo devolvería al idioma anterior
    // y se repetiría sin fin: en ese caso solo se cambia el idioma de este momento.
    if (recargar && recordado) location.reload();
}
