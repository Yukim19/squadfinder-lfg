# SquadFinder LFG

Plataforma web para que jugadores encuentren compañeros de equipo ("Looking For Group"). Incluye salas con filtros, % de compatibilidad, chat en tiempo real con filtro anti-toxicidad, reputación (Honor Score), interfaz en español e inglés, notificaciones por Discord y estado "EN VIVO" de Twitch.

Proyecto final del curso COMP2053 Integrat Web Dev (Full-Stack).

## Estructura

```
/frontend            8 páginas HTML + CSS/JS (Bootstrap 5, i18next)
/backend
  /database          schema.sql, seed.sql, seed_demo.sql
/docs                Documentación de las fases del proyecto
README.md
```

## Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5, i18next |
| Backend | Python, FastAPI (2 microservicios: `api-service` y `realtime-service`), Pydantic |
| Base de datos | PostgreSQL (Neon), Redis (Upstash) |
| Autenticación | Auth0 (JWT) |
| Despliegue | Netlify (frontend), Render (backend) |

## Documentación

- [Fase 1: Planificación y diseño](docs/fase1_planificacion.md)
- [Fase 2: Diseño de la base de datos](docs/fase2_base_de_datos.md)

## Base de datos: instalación

En el editor SQL de Neon (o en VS Code con SQLTools), ejecutar en orden:

1. `backend/database/schema.sql`
2. `backend/database/seed.sql`
3. `backend/database/seed_demo.sql` (solo para desarrollo)

## Autor

Juan M. Cardona Montañez
