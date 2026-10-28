# Guía de despliegue (todo gratis)

Esta guía publica SquadFinder LFG en internet para que cualquier persona pueda entrar con un enlace.

| Pieza | Servicio gratis | Qué publica |
|---|---|---|
| Base de datos | **Neon** (PostgreSQL) | Usuarios, salas, mensajes… |
| Backend | **Render** | `squadfinder-api` (API) y `squadfinder-chat` (chat en vivo) |
| Frontend | **Netlify** | Las 11 páginas |
| Inicio de sesión | **Auth0** | Ya está configurado |

> **Regla de oro:** la cadena de conexión de Neon es una **contraseña**. Se pega solo en los paneles de
> Render y en tu terminal. Nunca en un archivo del proyecto, en GitHub ni en un chat.

## Orden de los pasos

```
0. Subir el código a GitHub
1. Neon: crear la base de datos          → obtienes la cadena de conexión
2. Crear las tablas en Neon              → desde tu computadora
3. Render: publicar la API y el chat     → obtienes 2 direcciones
4. Poner esas 2 direcciones en el código → subir a GitHub
5. Netlify: publicar el frontend         → obtienes la dirección de la página
6. Auth0: permitir la dirección nueva
7. Render: permitir la dirección de la página (CORS)
8. Convertirte en administrador
9. Probar
```

---

## 0. Subir el código a GitHub

Render y Netlify publican lo que está en GitHub. Desde la carpeta del proyecto:

```bash
git status
```

Si hay cambios sin guardar, haz commit (ver comandos que te dio Claude) y luego:

```bash
git push
```

---

## 1. Neon: la base de datos

1. Entra a <https://console.neon.tech> con tu cuenta.
2. **Create project** → nombre `squadfinder`, región la más cercana (por ejemplo *US East*).
3. En el panel del proyecto, botón **Connect** (o *Connection Details*).
4. Elige la rama `main` y la base `neondb` (o la que aparezca) y activa **Pooled connection**.
5. **Copia la cadena** que empieza con `postgresql://...` y termina con `?sslmode=require`.
   Guárdala en un lugar privado (por ejemplo, un archivo fuera del proyecto): la usarás 3 veces.

## 2. Crear las tablas en Neon

El script `backend/database/crear_bd.py` crea las tablas y carga el catálogo de juegos y géneros.
**No** uses `--demo` ni `--reset`: no quieres usuarios de prueba en producción.

En PowerShell, desde la carpeta del proyecto (cambia la cadena por la tuya):

```powershell
$env:DATABASE_URL = "pega-aquí-tu-cadena-de-neon"
& "C:\Users\cardo\.venvs\squadfinder-api\Scripts\python.exe" backend\database\crear_bd.py
Remove-Item Env:\DATABASE_URL
```

Debe mostrar `Conectando a: ep-xxxx...neon.tech` (**revisa que sea Neon y no `localhost`**) y luego
`OK schema.sql`, `OK seed.sql` y `Listo: 35 juegos, 0 usuarios, 0 salas.`

La última línea (`Remove-Item`) borra la cadena de la memoria de esa terminal.

## 3. Render: publicar el backend

1. Entra a <https://dashboard.render.com> con tu cuenta de GitHub.
2. **New +** → **Blueprint**.
3. Conecta tu repositorio `Yukim19/squadfinder-lfg` (te pedirá permiso para leerlo).
4. Render lee el archivo `render.yaml` y muestra dos servicios: `squadfinder-api` y `squadfinder-chat`.
5. Te pide los valores secretos. Para **cada servicio**:
   - `DATABASE_URL`: pega la cadena de Neon del paso 1.
   - `CORS_ORIGINS`: por ahora escribe `["http://localhost:5501"]` (lo cambiamos en el paso 7).
6. **Apply** / **Deploy Blueprint**. Tarda unos minutos en construir.
7. Al terminar, cada servicio tiene una dirección como `https://squadfinder-api.onrender.com`.
   Si el nombre ya estaba ocupado, Render le agrega letras: **anota las dos direcciones exactas**.
8. Comprueba que viven abriendo en el navegador:
   - `https://TU-API.onrender.com/api/v1/health` → debe mostrar `"status":"ok"` y `"database":"ok"`.
   - `https://TU-CHAT.onrender.com/api/v1/health` → igual.

> La primera visita puede tardar cerca de **1 minuto**: el plan gratis apaga el servicio tras
> 15 minutos sin uso y tarda en despertar. Es normal.

## 4. Poner las direcciones en el código

En `frontend/js/api.js`, en el bloque `CONFIG`, las direcciones de producción deben ser las tuyas:

```js
API_URL:  ... : 'https://TU-API.onrender.com/api/v1',
CHAT_URL: ... : 'wss://TU-CHAT.onrender.com/ws/chat',
DM_URL:   ... : 'wss://TU-CHAT.onrender.com/ws/dm',
CHAT_API: ... : 'https://TU-CHAT.onrender.com/api/v1',
```

(El chat usa `wss://`, la versión segura de WebSocket.) Después haz commit y `git push`.
Claude puede hacer este cambio por ti si le das las dos direcciones.

## 5. Netlify: publicar el frontend

1. Entra a <https://app.netlify.com> con tu cuenta de GitHub.
2. **Add new site** → **Import an existing project** → **GitHub** → elige `squadfinder-lfg`.
3. La configuración sale sola de `netlify.toml` (carpeta a publicar: `frontend`, sin comando de compilación).
   Si pregunta, déjalos así.
4. **Deploy**. En menos de un minuto tienes una dirección como `https://nombre-raro-123.netlify.app`.
5. (Opcional) **Site configuration → Change site name** para elegir uno bonito, por ejemplo
   `squadfinder-lfg` → `https://squadfinder-lfg.netlify.app`.
6. **Anota la dirección final.**

## 6. Auth0: permitir la dirección nueva

En <https://manage.auth0.com> → **Applications** → **SquadFinder Web** → **Settings**.
Agrega (sin borrar las de `localhost`) y presiona **Save Changes** al final:

| Campo | Valor a agregar |
|---|---|
| Allowed Callback URLs | `https://TU-SITIO.netlify.app/login.html` |
| Allowed Logout URLs | `https://TU-SITIO.netlify.app/login.html` |
| Allowed Web Origins | `https://TU-SITIO.netlify.app` (sin `/login.html`) |

Recomendado: en **Applications → APIs → SquadFinder API → Settings** activa **Allow Offline Access**.

## 7. Render: permitir la página (CORS)

En Render, para **cada uno** de los dos servicios: **Environment** → edita `CORS_ORIGINS` y pon:

```
["https://TU-SITIO.netlify.app"]
```

Guarda: el servicio se reinicia solo. Mientras desarrollas en tu computadora, puedes dejar también los
de `localhost`: `["https://TU-SITIO.netlify.app","http://localhost:5501"]`.

## 8. Convertirte en administrador

1. Entra a tu sitio, regístrate con tu correo (o Google) y completa el onboarding.
2. En Neon: **SQL Editor**, pega y ejecuta (cambia el nombre por tu usuario):

```sql
UPDATE users SET role = 'ADMIN' WHERE username = 'tu_nombre_de_usuario';
```

3. Cierra sesión y vuelve a entrar: aparece **🛡️ Moderación** en el menú.

## 9. Lista de pruebas

- [ ] La página abre y el login muestra los botones de Auth0.
- [ ] Puedes crear una cuenta, completar el onboarding y ver las salas.
- [ ] Creas una sala y otra persona (otro navegador o un amigo) se une.
- [ ] El chat de la sala funciona en vivo.
- [ ] Agregas a otra persona como amigo y se escriben por mensaje privado.
- [ ] Un insulto llega oculto a quien tiene el filtro en *Estricto*.
- [ ] Cambias el idioma a inglés y se mantiene.
- [ ] Como administrador ves el panel de moderación.

## Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| "No se pudo conectar con el servidor" | La API está dormida o `API_URL` está mal | Espera 1 minuto y recarga; revisa el paso 4 |
| Error de CORS en la consola (F12) | Falta tu dirección de Netlify en `CORS_ORIGINS` | Paso 7 (con `https://`, sin `/` al final) |
| Auth0: "Callback URL mismatch" | Falta la dirección en Auth0 | Paso 6 y **Save Changes** |
| El chat no conecta | `DM_URL`/`CHAT_URL` sin `wss://` o servicio dormido | Paso 4 y espera 1 minuto |
| Sigues viendo la versión vieja | Copia guardada en el navegador | `Ctrl+Shift+R` |
| Render falla al construir | Versión de Python o dependencias | Mira el *Log* del servicio y envíaselo a Claude |

## Límites del plan gratis (para la presentación)

- **Render:** 750 horas al mes en total para el workspace. Cada servicio se apaga tras 15 minutos
  sin uso y tarda cerca de 1 minuto en despertar. **Abre el sitio unos minutos antes de presentar.**
- **Neon:** la base se "duerme" sin uso y despierta sola en un segundo.
- **Auth0 (plan gratis):** hasta 25 000 usuarios activos al mes; no uses funciones de pago como MFA.
- El chat de las salas guarda el estado de "quién está conectado" en memoria: con una sola instancia
  (el caso del plan gratis) funciona; los mensajes siempre quedan guardados en la base de datos.
