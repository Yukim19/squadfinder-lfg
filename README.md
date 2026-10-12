# SquadFinder LFG

Plataforma web para que jugadores encuentren compañeros de equipo ("Looking For Group") en juegos de PC, consola y móvil.

Proyecto final del curso COMP2053 Integrat Web Dev (Full-Stack).

## Funciones principales

- **Salas LFG:** casuales o competitivas (con rango mínimo), una o varias plataformas según el crossplay del juego, e idioma español, inglés o todos.
- **Feed con filtros:** juego, plataforma, región, idioma y tipo de partida, con % de compatibilidad.
- **Chat en tiempo real** con filtro anti-toxicidad que cada usuario ajusta (Estricto, Medio o Apagado).
- **Niveles de honor del 1 al 10:** las buenas reseñas dan XP; las sanciones quitan niveles; en el nivel 0 la cuenta es 🐣 *Rookie*.
- **Moderación:** reportes con evidencia del chat; el administrador advierte, personaliza la sanción o elimina la cuenta, con una regla automática configurable (por defecto, 3 advertencias eliminan la cuenta).
- **Lista negra personal:** dejas de ver las salas de quien bloqueas, sin castigarlo.
- **Perfil:** foto o avatar, juegos y géneros favoritos, idiomas (incluye "ambos") y cuentas vinculadas de Discord, Steam, Twitch y Kick.
- **Catálogo:** 35 juegos y 16 géneros; los usuarios pueden sugerir juegos nuevos y el administrador los aprueba.
- Interfaz en español e inglés, avisos por Discord y estado "EN VIVO" de Twitch.

## Páginas (11)

| Página | Función |
|---|---|
| `index.html` | Feed de salas con filtros |
| `login.html` | Iniciar sesión o crear cuenta |
| `onboarding.html` | Configuración inicial |
| `perfil_config.html` | Editar mi perfil y foto |
| `crear_post.html` | Crear sala con vista previa |
| `detalle_post.html` | Ver y gestionar una sala |
| `chat_sala.html` | Chat de la sala |
| `historial_partidas.html` | Partidas, reseñas, reportes y lista negra |
| `usuario.html` | Perfil público de un jugador |
| `admin_reportes.html` | Moderación y juegos sugeridos (solo administradores) |
| `404.html` | Página no encontrada, con la mascota Squaddy |

## Estructura

```
/frontend            11 páginas HTML
  /css/theme.css     Tema visual (paleta neón morado/cian)
  /js/catalogo.js    Catálogo y datos de prueba (se reemplazan por la API)
  /js/ui.js          Componentes compartidos: avisos, confirmaciones, menú, niveles, reportes
/backend
  /database          schema.sql, seed.sql, seed_demo.sql
/docs                Documentación de las fases del proyecto
README.md
```

## Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5, Bootstrap Icons, i18next |
| Backend | Python, FastAPI (2 microservicios: `api-service` y `realtime-service`), Pydantic, NLTK |
| Base de datos | PostgreSQL (Neon), Redis (Upstash) |
| Autenticación | Auth0 (JWT) |
| Archivos | Cloudinary (fotos de perfil) |
| Integraciones | API de Discord, API de Twitch |
| Despliegue | Netlify (frontend), Render (backend) |

## Documentación

- [Fase 1: Planificación y diseño](docs/fase1_planificacion.md)
- [Fase 2: Diseño de la base de datos](docs/fase2_base_de_datos.md)

## Probar el frontend en local

1. Abrir la carpeta del proyecto en VS Code.
2. Clic derecho en `frontend/index.html` → **Open with Live Server**.
3. Ir a http://127.0.0.1:5500/index.html

Mientras no exista el backend, las páginas usan los datos de prueba de `frontend/js/catalogo.js`, y los cambios se guardan en el navegador (`localStorage`). El usuario de prueba `ana_gg` es administrador, para poder ver el panel de moderación.

## Base de datos: instalación

En el editor SQL de Neon (o en VS Code con SQLTools), ejecutar en orden:

1. `backend/database/schema.sql`: tablas, restricciones, triggers, vistas y funciones.
2. `backend/database/seed.sql`: géneros, juegos y plataformas (obligatorio).
3. `backend/database/seed_demo.sql`: usuarios, salas, reseñas y reportes de prueba (solo para desarrollo).

## Autor

Juan M. Cardona Montañez
