# Fase 1: Planificación y Diseño

**Proyecto:** SquadFinder LFG
**Estudiante:** Juan M. Cardona Montañez
**Curso:** COMP2053 Integrat Web Dev (Full-Stack)
**Profesora:** Milagros Donato Cintron

---

## 1. Descripción del proyecto

SquadFinder LFG ("Looking For Group") es una plataforma web donde jugadores de videojuegos publican y buscan salas para formar equipos. Cada sala indica el juego, la plataforma, los cupos, el rango, el idioma y si se requiere micrófono. Los jugadores solicitan unirse, el anfitrión acepta o rechaza, y los miembros conversan en un chat en tiempo real con un filtro anti-toxicidad que cada usuario ajusta a su gusto. Al terminar la partida, los compañeros se califican entre sí y generan un puntaje de reputación (Honor Score).

## 2. Objetivo general

Desarrollar una aplicación web Full-Stack de 8 páginas, con un backend en microservicios, que permita a los jugadores crear, buscar, gestionar y unirse a publicaciones LFG. Incluye autenticación con JWT, reputación comunitaria, chat moderado en tiempo real, soporte en español e inglés, notificaciones por Discord e integración con Twitch.

## 3. Justificación

Los jugadores de juegos multijugador tienen problemas para encontrar compañeros con el mismo nivel, horario, idioma y estilo de juego. Además, la toxicidad en los chats y la barrera del idioma arruinan la experiencia. SquadFinder resuelve esto con:

- filtros de búsqueda y un porcentaje de compatibilidad;
- un filtro de chat que cada usuario configura;
- una interfaz bilingüe;
- un sistema de reputación que premia el buen comportamiento.

## 4. Alcance del sistema

### Incluye

| Módulo | Funciones |
|---|---|
| Autenticación | Inicio de sesión con Auth0 (correo o Google), tokens JWT, protección de rutas en el frontend y en el backend |
| Perfil | Onboarding inicial donde el usuario elige su región y **los juegos en los que busca compañeros**; edición posterior de esas preferencias (juegos, géneros, región, idiomas, nivel del filtro); vinculación y desvinculación de Discord, Steam, Twitch y Kick; eliminación de la cuenta |
| Salas LFG | CRUD completo de publicaciones (solo de los juegos elegidos en el perfil), con tipo de partida (casual o competitiva con rango mínimo), una o varias plataformas según el crossplay del juego, e idioma español, inglés o todos; feed con la región del anfitrión, búsqueda con filtros y % de compatibilidad |
| Historial | Partidas terminadas con la lista de compañeros (usuario, región, Honor Score) y las opciones de calificar o **reportar** a cada uno |
| Moderación | Reportes de jugadores tóxicos con motivo y comentario; evidencia automática con los mensajes que marcó el filtro; panel de administrador para descartar el reporte, suspender la cuenta 7 días o eliminarla |
| Solicitudes | CRUD completo: solicitar unirse, ver solicitudes, aceptar o rechazar, retirar la solicitud |
| Reputación | Reseñas post-partida (crear, ver, editar, eliminar) y Honor Score promedio |
| Chat | Mensajes en tiempo real por WebSocket con filtro anti-toxicidad (OFF, MEDIUM, STRICT) e historial |
| Notificaciones | Mensaje directo por el bot de Discord al solicitar unirse o ser aceptado |
| Streaming | Badge "EN VIVO" para usuarios con su canal de Twitch vinculado |
| Idiomas | Interfaz completa en español e inglés (i18next) |

### No incluye (trabajo futuro)

- Inicio de sesión directo con Steam o Discord (se vinculan desde el perfil).
- Aplicación móvil nativa (la web es responsiva).
- Chat de voz.
- Pagos o suscripciones.
- Modelos de IA pesados de moderación (por ejemplo, Detoxify).

## 5. Tecnologías seleccionadas

| Capa | Tecnología | Uso |
|---|---|---|
| Frontend | HTML5, CSS3, JavaScript | 8 páginas independientes |
| Frontend | Bootstrap 5.3 | Diseño responsivo y componentes |
| Frontend | i18next | Traducción en tiempo real ES/EN |
| Backend | Python 3 y FastAPI | API REST y WebSockets |
| Backend | Pydantic | Validación de datos de entrada y salida |
| Backend | SQLAlchemy y psycopg | Conexión con PostgreSQL |
| Backend | NLTK y listas de palabras ES/EN | Filtro anti-toxicidad (PNL) |
| Base de datos | PostgreSQL (Neon) | Base de datos relacional principal, conexión con `sslmode=require` |
| Caché | Redis (Upstash) | Caché de compatibilidad y estado de Twitch, límite de mensajes |
| Autenticación | Auth0 | Inicio de sesión y emisión de JWT (OAuth 2.0) |
| Integraciones | API de Discord y API de Twitch (Helix) | Notificaciones y estado "EN VIVO" |
| Despliegue | Netlify (frontend) y Render (backend) | Publicación gratuita con HTTPS |
| Herramientas | VS Code, Git y GitHub | Desarrollo y control de versiones |

## 6. Diagrama de arquitectura

El backend se divide en **2 microservicios**:

- **api-service:** operaciones REST de corta duración.
- **realtime-service:** conexiones persistentes (WebSocket) y procesamiento de texto.

Si el chat falla o se satura, el resto de la aplicación sigue funcionando.

```mermaid
flowchart LR
    U["Usuario<br/>(navegador)"]

    subgraph Netlify
        FE["Frontend<br/>8 páginas HTML/CSS/JS<br/>Bootstrap + i18next"]
    end

    A0["Auth0<br/>login + JWT"]

    subgraph Render
        API["api-service<br/>FastAPI REST<br/>usuarios · salas · solicitudes<br/>reputación · compatibilidad"]
        RT["realtime-service<br/>FastAPI WebSocket<br/>chat · filtro PNL<br/>bot Discord · Twitch"]
    end

    DB[("PostgreSQL<br/>Neon")]
    RD[("Redis<br/>Upstash")]
    DC["API de Discord"]
    TW["API de Twitch"]

    U --> FE
    FE -- "1. inicio de sesión" --> A0
    A0 -- "2. JWT" --> FE
    FE -- "HTTPS + JWT" --> API
    FE -- "WSS + JWT" --> RT
    API -- "SSL" --> DB
    RT -- "SSL" --> DB
    RT --> RD
    API --> RD
    RT --> DC
    RT --> TW
```

**Flujo de autenticación:**

1. El usuario inicia sesión en Auth0 desde `login.html`.
2. Auth0 devuelve un JWT firmado (RS256).
3. El frontend envía ese JWT en el encabezado `Authorization: Bearer <token>` de cada petición.
4. Cada microservicio verifica la firma del token con las llaves públicas de Auth0 (JWKS) antes de responder.
5. Si el token falta o no es válido, la respuesta es `401 Unauthorized`.

## 7. Diagrama general de navegación

```mermaid
flowchart TD
    LOGIN["login.html<br/>Iniciar sesión"]
    ONB["onboarding.html<br/>Configuración inicial"]
    INDEX["index.html<br/>Feed de salas"]
    CREAR["crear_post.html<br/>Crear sala"]
    DET["detalle_post.html<br/>Detalle de sala"]
    CHAT["chat_sala.html<br/>Chat de la sala"]
    PERFIL["perfil_config.html<br/>Configurar perfil"]
    HIST["historial_partidas.html<br/>Historial y reseñas"]
    USR["usuario.html<br/>Perfil público"]
    E404["404.html<br/>Página no encontrada"]
    ADMIN["admin_reportes.html<br/>Moderación (solo ADMIN)"]

    LOGIN -- "primer inicio" --> ONB
    LOGIN -- "usuario existente" --> INDEX
    ONB --> INDEX
    INDEX --> CREAR
    INDEX -- "ver sala" --> DET
    CREAR -- "publicar" --> DET
    DET -- "miembro aceptado" --> CHAT
    CHAT --> DET
    INDEX --> PERFIL
    INDEX --> HIST
    HIST -- "calificar compañeros" --> HIST
    DET -- "clic en un jugador" --> USR
    HIST -- "clic en un jugador" --> USR
    CHAT -- "clic en un jugador" --> USR
    PERFIL -- "ver mi perfil público" --> USR
    PERFIL -- "cerrar sesión / eliminar cuenta" --> LOGIN
    DET -. "sala inexistente" .-> E404
    HIST -- "reportar jugador" --> ADMIN
    USR -- "reportar jugador" --> ADMIN
    ADMIN -- "ver perfil del reportado" --> USR
```

Todas las páginas, excepto `login.html` y `404.html`, son **rutas protegidas**: si no hay una sesión válida, el usuario es redirigido a `login.html`. `admin_reportes.html` además exige `role = 'ADMIN'`; el backend responde `403 Forbidden` a cualquier otro usuario.

La barra de navegación de todas las páginas tiene:

- enlaces a Salas, Crear búsqueda e Historial;
- un menú de usuario con Configurar perfil, Ver mi perfil público, Historial y Cerrar sesión;
- para administradores, la opción **Moderación**, con el número de reportes pendientes.

### Páginas adicionales a la propuesta

Además de las 8 páginas de la propuesta, se agregaron 3:

| Página | Motivo |
|---|---|
| `usuario.html` | Perfil público de cada jugador: Honor Score, reseñas recibidas, etiquetas destacadas, juegos y cuentas vinculadas. Permite decidir con quién jugar antes de aceptar una solicitud. Usa `GET /api/v1/users/{id}` y `GET /api/v1/reputation/users/{id}` |
| `404.html` | Página de error para salas eliminadas o direcciones mal escritas. Netlify la muestra automáticamente |
| `admin_reportes.html` | Panel de moderación: reportes pendientes y resueltos, evidencia del chat marcada por el filtro y acciones de sanción. Usa `GET /api/v1/admin/reports` y `PUT /api/v1/admin/reports/{id}` |

### Operaciones CRUD por página

| Página | Create | Read | Update | Delete |
|---|---|---|---|---|
| onboarding.html | Perfil inicial | — | — | — |
| perfil_config.html | Vincular cuenta | Mis datos | Preferencias, juegos, región | Desvincular cuenta, eliminar cuenta |
| crear_post.html | Sala | Mis juegos | — | — |
| index.html | — | Salas activas con filtros | — | — |
| detalle_post.html | Solicitud para unirse | Sala, integrantes, solicitudes | Editar sala, aceptar o rechazar solicitud, terminar partida | Eliminar sala, retirar solicitud, salir de la sala |
| chat_sala.html | Mensaje | Historial del chat | — | — |
| historial_partidas.html | Reseña, reporte | Partidas y compañeros | Editar reseña | Borrar reseña, eliminar sala |
| usuario.html | Reporte | Perfil público y reseñas | — | — |
| admin_reportes.html | — | Reportes y evidencia | Resolver reporte: descartar, suspender o eliminar la cuenta | — |
