-- =====================================================================
-- SquadFinder LFG - Script de creación de la base de datos
-- Motor: PostgreSQL 15+ (Neon)
-- Ejecutar completo en una base de datos vacía.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Función común: mantiene actualizado el campo updated_at
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- Catálogos
-- ---------------------------------------------------------------------
CREATE TABLE genres (
    id          SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE games (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    genre_id    SMALLINT NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
    -- TRUE si jugadores de distintas plataformas pueden jugar juntos
    crossplay   BOOLEAN  NOT NULL DEFAULT FALSE
);

-- Plataformas en las que existe cada juego (M:N)
CREATE TABLE game_platforms (
    game_id     INTEGER     NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    platform    VARCHAR(12) NOT NULL
                CHECK (platform IN ('PC', 'PlayStation', 'Xbox', 'Switch', 'Mobile')),
    PRIMARY KEY (game_id, platform)
);

-- ---------------------------------------------------------------------
-- Usuarios
-- ---------------------------------------------------------------------
CREATE TABLE users (
    id                          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    auth0_id                    VARCHAR(128) NOT NULL UNIQUE,
    username                    VARCHAR(30)  NOT NULL UNIQUE
                                CHECK (username ~ '^[A-Za-z0-9_]{3,30}$'),
    ui_language                 CHAR(2)      NOT NULL DEFAULT 'es'
                                CHECK (ui_language IN ('es', 'en')),
    -- 'both' = habla (o escribe) español e inglés
    preferred_language_speak    VARCHAR(4)   NOT NULL DEFAULT 'es'
                                CHECK (preferred_language_speak IN ('es', 'en', 'both')),
    preferred_language_write    VARCHAR(4)   NOT NULL DEFAULT 'es'
                                CHECK (preferred_language_write IN ('es', 'en', 'both')),
    -- Foto de perfil: URL de la imagen subida o 'preset:<emoji>' para un avatar prediseñado
    avatar_url                  VARCHAR(500),
    toxicity_filter_level       VARCHAR(6)   NOT NULL DEFAULT 'MEDIUM'
                                CHECK (toxicity_filter_level IN ('OFF', 'MEDIUM', 'STRICT')),
    -- Región de juego; se pide en el onboarding (NULL hasta completarlo)
    region                      VARCHAR(11)
                                CHECK (region IN ('NA_EAST', 'NA_WEST', 'LATAM_NORTH', 'LATAM_SOUTH',
                                                  'BRAZIL', 'EUROPE', 'ASIA', 'OCEANIA')),
    -- Sistema de niveles de honor (1 a 10; 0 = Rookie). Ver level_from_xp().
    -- xp = XP ganada por reseñas - penalty_xp. level y xp los mantienen los triggers.
    xp                          INTEGER      NOT NULL DEFAULT 0,
    level                       SMALLINT     NOT NULL DEFAULT 1 CHECK (level BETWEEN 0 AND 10),
    -- XP descontada por sanciones (100 XP = 1 nivel)
    penalty_xp                  INTEGER      NOT NULL DEFAULT 0 CHECK (penalty_xp >= 0),
    -- Advertencias acumuladas; al llegar al límite de moderation_settings se sanciona sola
    warnings_count              SMALLINT     NOT NULL DEFAULT 0 CHECK (warnings_count >= 0),
    is_onboarding_completed     BOOLEAN      NOT NULL DEFAULT FALSE,
    -- USER = jugador normal; ADMIN = puede revisar reportes y sancionar cuentas
    role                        VARCHAR(5)   NOT NULL DEFAULT 'USER'
                                CHECK (role IN ('USER', 'ADMIN')),
    -- BANNED = cuenta eliminada por un administrador; no puede volver a entrar
    account_status              VARCHAR(9)   NOT NULL DEFAULT 'ACTIVE'
                                CHECK (account_status IN ('ACTIVE', 'SUSPENDED', 'BANNED')),
    suspended_until             TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CHECK (account_status <> 'SUSPENDED' OR suspended_until IS NOT NULL)
);

-- "Ana_GG" y "ana_gg" se consideran el mismo nombre de usuario
CREATE UNIQUE INDEX uq_users_username_lower ON users (LOWER(username));

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Cuentas externas vinculadas (Discord, Steam, Twitch, Kick)
CREATE TABLE linked_accounts (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id             INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider            VARCHAR(10)  NOT NULL
                        CHECK (provider IN ('discord', 'steam', 'twitch', 'kick')),
    external_username   VARCHAR(100) NOT NULL,
    -- ID numérico de Discord, necesario para que el bot envíe mensajes directos
    external_id         VARCHAR(64),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, provider)
);

-- Preferencias del usuario (relaciones M:N)
-- user_games = juegos en los que busca compañeros (se eligen en el onboarding y
-- se editan en el perfil). La API solo permite crear salas de estos juegos.
CREATE TABLE user_genres (
    user_id     INTEGER  NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    genre_id    SMALLINT NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, genre_id)
);

CREATE TABLE user_games (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_id     INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, game_id)
);

-- ---------------------------------------------------------------------
-- Publicaciones LFG (salas)
-- ---------------------------------------------------------------------
CREATE TABLE lfg_posts (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    host_id             INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_id             INTEGER      NOT NULL REFERENCES games(id) ON DELETE RESTRICT,
    title               VARCHAR(100) NOT NULL CHECK (char_length(title) >= 3),
    description         VARCHAR(500),
    max_players         SMALLINT     NOT NULL CHECK (max_players BETWEEN 2 AND 10),
    -- CASUAL = sin requisito de rango; COMPETITIVE = puede exigir un rango mínimo
    play_mode           VARCHAR(11)  NOT NULL DEFAULT 'CASUAL'
                        CHECK (play_mode IN ('CASUAL', 'COMPETITIVE')),
    rank_required       VARCHAR(50),
    mic_required        BOOLEAN      NOT NULL DEFAULT FALSE,
    -- 'any' = la sala acepta jugadores de cualquier idioma
    required_language   VARCHAR(3)   NOT NULL DEFAULT 'es'
                        CHECK (required_language IN ('es', 'en', 'any')),
    status              VARCHAR(11)  NOT NULL DEFAULT 'OPEN'
                        CHECK (status IN ('OPEN', 'FULL', 'IN_PROGRESS', 'CLOSED', 'CANCELLED')),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMPTZ,
    -- Solo las salas competitivas pueden pedir rango
    CHECK (play_mode = 'COMPETITIVE' OR rank_required IS NULL)
);

CREATE INDEX idx_lfg_posts_status_game ON lfg_posts (status, game_id);
CREATE INDEX idx_lfg_posts_host ON lfg_posts (host_id);

CREATE TRIGGER trg_lfg_posts_updated_at
    BEFORE UPDATE ON lfg_posts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Plataformas desde las que se puede entrar a una sala (M:N).
-- Varias plataformas solo si el juego tiene crossplay.
CREATE TABLE post_platforms (
    post_id     INTEGER     NOT NULL REFERENCES lfg_posts(id) ON DELETE CASCADE,
    platform    VARCHAR(12) NOT NULL
                CHECK (platform IN ('PC', 'PlayStation', 'Xbox', 'Switch', 'Mobile')),
    PRIMARY KEY (post_id, platform)
);

-- Valida que la plataforma exista para el juego de la sala y que, si el
-- juego no tiene crossplay, la sala tenga una sola plataforma.
CREATE OR REPLACE FUNCTION check_post_platform()
RETURNS TRIGGER AS $$
DECLARE
    v_game_id   INTEGER;
    v_crossplay BOOLEAN;
BEGIN
    SELECT p.game_id, g.crossplay INTO v_game_id, v_crossplay
    FROM lfg_posts p JOIN games g ON g.id = p.game_id
    WHERE p.id = NEW.post_id;

    IF NOT EXISTS (SELECT 1 FROM game_platforms
                   WHERE game_id = v_game_id AND platform = NEW.platform) THEN
        RAISE EXCEPTION 'El juego de la sala no está disponible en %', NEW.platform;
    END IF;

    IF NOT v_crossplay AND EXISTS (SELECT 1 FROM post_platforms
                                   WHERE post_id = NEW.post_id AND platform <> NEW.platform) THEN
        RAISE EXCEPTION 'Este juego no tiene crossplay: la sala solo puede tener una plataforma';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_post_platforms_check
    BEFORE INSERT OR UPDATE ON post_platforms
    FOR EACH ROW EXECUTE FUNCTION check_post_platform();

-- Solicitudes para unirse a una sala
CREATE TABLE applications (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    post_id         INTEGER     NOT NULL REFERENCES lfg_posts(id) ON DELETE CASCADE,
    applicant_id    INTEGER     NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    status          VARCHAR(9)  NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'WITHDRAWN')),
    message         VARCHAR(200),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (post_id, applicant_id)
);

CREATE INDEX idx_applications_applicant ON applications (applicant_id);

CREATE TRIGGER trg_applications_updated_at
    BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------
-- Reputación (Honor Score)
-- ---------------------------------------------------------------------
CREATE TABLE user_reviews (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    post_id         INTEGER     NOT NULL REFERENCES lfg_posts(id) ON DELETE CASCADE,
    reviewer_id     INTEGER     NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    target_user_id  INTEGER     NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    rating          SMALLINT    NOT NULL CHECK (rating BETWEEN 1 AND 5),
    tag             VARCHAR(20)
                    CHECK (tag IN ('GREAT_LEADER', 'FRIENDLY', 'GOOD_COMMS', 'SKILLED', 'TEAM_PLAYER')),
    comment         VARCHAR(300),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (reviewer_id <> target_user_id),
    UNIQUE (post_id, reviewer_id, target_user_id)
);

CREATE INDEX idx_user_reviews_target ON user_reviews (target_user_id);

CREATE TRIGGER trg_user_reviews_updated_at
    BEFORE UPDATE ON user_reviews
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------
-- Sistema de niveles de honor
--   * Todas las cuentas empiezan en nivel 1 con 0 XP.
--   * Cada reseña recibida da XP: 5★ = 30, 4★ = 20, 3★ = 10, 1-2★ = 0.
--   * Anti-abuso: de un mismo compañero solo cuentan sus primeras 3 reseñas.
--   * Cada 100 XP se sube un nivel, hasta el 10 (900 XP).
--   * Las sanciones suman penalty_xp (100 XP por nivel quitado).
--   * Si la XP neta queda negativa, el nivel es 0: la cuenta es "Rookie".
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION level_from_xp(p_xp INTEGER)
RETURNS SMALLINT AS $$
    SELECT CASE WHEN p_xp < 0 THEN 0 ELSE LEAST(10, 1 + p_xp / 100) END::SMALLINT;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION review_xp(p_user INTEGER)
RETURNS INTEGER AS $$
    SELECT COALESCE(SUM(puntos), 0)::INTEGER
    FROM (
        SELECT CASE rating WHEN 5 THEN 30 WHEN 4 THEN 20 WHEN 3 THEN 10 ELSE 0 END AS puntos,
               ROW_NUMBER() OVER (PARTITION BY reviewer_id ORDER BY created_at, id) AS n
        FROM user_reviews
        WHERE target_user_id = p_user
    ) r
    WHERE n <= 3;
$$ LANGUAGE sql STABLE;

-- Recalcula xp y level de los usuarios afectados cuando cambia una reseña
CREATE OR REPLACE FUNCTION refresh_level_from_reviews()
RETURNS TRIGGER AS $$
DECLARE
    target INTEGER;
BEGIN
    FOR target IN
        SELECT DISTINCT t FROM (VALUES
            (CASE WHEN TG_OP <> 'INSERT' THEN OLD.target_user_id END),
            (CASE WHEN TG_OP <> 'DELETE' THEN NEW.target_user_id END)
        ) AS v(t)
        WHERE t IS NOT NULL
    LOOP
        UPDATE users
           SET xp    = review_xp(id) - penalty_xp,
               level = level_from_xp(review_xp(id) - penalty_xp)
         WHERE id = target;
    END LOOP;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reviews_level
    AFTER INSERT OR UPDATE OR DELETE ON user_reviews
    FOR EACH ROW EXECUTE FUNCTION refresh_level_from_reviews();

-- Recalcula xp y level cuando un administrador aplica una sanción (penalty_xp)
CREATE OR REPLACE FUNCTION refresh_level_from_penalty()
RETURNS TRIGGER AS $$
BEGIN
    NEW.xp    := review_xp(NEW.id) - NEW.penalty_xp;
    NEW.level := level_from_xp(NEW.xp);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_penalty
    BEFORE UPDATE OF penalty_xp ON users
    FOR EACH ROW EXECUTE FUNCTION refresh_level_from_penalty();

-- ---------------------------------------------------------------------
-- Chat
-- ---------------------------------------------------------------------
CREATE TABLE chat_messages (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    post_id         INTEGER      NOT NULL REFERENCES lfg_posts(id) ON DELETE CASCADE,
    sender_id       INTEGER      NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
    message         VARCHAR(500) NOT NULL CHECK (char_length(trim(message)) > 0),
    -- Resultado del filtro PNL: NONE = limpio, MILD = ofensivo leve, SEVERE = insulto fuerte.
    -- Cada receptor ve el mensaje censurado según su toxicity_filter_level.
    toxicity_level  VARCHAR(6)   NOT NULL DEFAULT 'NONE'
                    CHECK (toxicity_level IN ('NONE', 'MILD', 'SEVERE')),
    sent_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_post_sent ON chat_messages (post_id, sent_at);

-- ---------------------------------------------------------------------
-- Moderación: reportes de jugadores tóxicos
-- Un jugador reporta a un compañero de partida; un ADMIN lo revisa y decide:
-- descartarlo, advertir, suspender (días a elección), eliminar la cuenta
-- (BANNED) y cuántos niveles descontar.
-- ---------------------------------------------------------------------
CREATE TABLE user_reports (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reporter_id         INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reported_user_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Partida donde ocurrió (para revisar el chat como evidencia)
    post_id             INTEGER      REFERENCES lfg_posts(id) ON DELETE SET NULL,
    reason              VARCHAR(15)  NOT NULL
                        CHECK (reason IN ('TOXIC_CHAT', 'HARASSMENT', 'AFK_GRIEFING', 'CHEATING', 'OTHER')),
    comment             VARCHAR(500) NOT NULL CHECK (char_length(trim(comment)) >= 10),
    status              VARCHAR(9)   NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING', 'DISMISSED', 'WARNED', 'SUSPENDED', 'BANNED')),
    -- Sanción aplicada (la decide el administrador o la regla automática)
    suspension_days     SMALLINT     CHECK (suspension_days BETWEEN 1 AND 365),
    levels_removed      SMALLINT     NOT NULL DEFAULT 0 CHECK (levels_removed BETWEEN 0 AND 10),
    -- TRUE si la sanción la aplicó la regla de "N advertencias"
    is_automatic        BOOLEAN      NOT NULL DEFAULT FALSE,
    -- Administrador que resolvió el reporte y su nota
    resolved_by         INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    admin_notes         VARCHAR(500),
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CHECK (reporter_id <> reported_user_id),
    CHECK ((status = 'PENDING') = (resolved_at IS NULL)),
    CHECK ((status = 'SUSPENDED') = (suspension_days IS NOT NULL))
);

-- Un jugador no puede reportar dos veces a la misma persona por la misma partida
CREATE UNIQUE INDEX uq_user_reports_once ON user_reports (reporter_id, reported_user_id, post_id);
CREATE INDEX idx_user_reports_status ON user_reports (status, created_at);
CREATE INDEX idx_user_reports_reported ON user_reports (reported_user_id);

-- Reglas de moderación configurables por el administrador (una sola fila)
CREATE TABLE moderation_settings (
    id                          SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    -- Al llegar a este número de advertencias se aplica auto_action
    warnings_limit              SMALLINT    NOT NULL DEFAULT 3 CHECK (warnings_limit BETWEEN 1 AND 10),
    auto_action                 VARCHAR(7)  NOT NULL DEFAULT 'BAN' CHECK (auto_action IN ('SUSPEND', 'BAN')),
    auto_suspension_days        SMALLINT    NOT NULL DEFAULT 30 CHECK (auto_suspension_days BETWEEN 1 AND 365),
    -- Niveles que se descuentan por defecto en cada tipo de sanción
    warning_levels_removed      SMALLINT    NOT NULL DEFAULT 1 CHECK (warning_levels_removed BETWEEN 0 AND 10),
    suspension_levels_removed   SMALLINT    NOT NULL DEFAULT 2 CHECK (suspension_levels_removed BETWEEN 0 AND 10),
    updated_by                  INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO moderation_settings DEFAULT VALUES;

CREATE TRIGGER trg_moderation_settings_updated_at
    BEFORE UPDATE ON moderation_settings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------
-- Lista negra personal: el usuario deja de ver las salas de quien bloquea.
-- No es una sanción: solo afecta lo que ve quien creó la lista.
-- ---------------------------------------------------------------------
CREATE TABLE user_blocks (
    blocker_id  INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id  INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason      VARCHAR(200),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (blocker_id, blocked_id),
    CHECK (blocker_id <> blocked_id)
);

-- ---------------------------------------------------------------------
-- Juegos sugeridos por los usuarios (desde el onboarding o el perfil).
-- Si el administrador lo aprueba, se crea en games y aparece para todos.
-- ---------------------------------------------------------------------
CREATE TABLE game_requests (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_name       VARCHAR(100) NOT NULL CHECK (char_length(trim(game_name)) >= 2),
    platforms_note  VARCHAR(100),
    status          VARCHAR(8)   NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    -- Juego creado al aprobar la sugerencia
    game_id         INTEGER      REFERENCES games(id) ON DELETE SET NULL,
    reviewed_by     INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CHECK (status <> 'APPROVED' OR game_id IS NOT NULL)
);

-- La misma persona no puede sugerir dos veces el mismo juego mientras esté pendiente
CREATE UNIQUE INDEX uq_game_requests_pending
    ON game_requests (user_id, LOWER(game_name)) WHERE status = 'PENDING';

-- ---------------------------------------------------------------------
-- Vista: salas con plataformas y número actual de jugadores
-- current_players se calcula (anfitrión + solicitudes aceptadas) en vez de
-- guardarse, para evitar datos duplicados que se desincronicen.
-- ---------------------------------------------------------------------
CREATE VIEW v_lfg_posts AS
SELECT p.*,
       g.name        AS game_name,
       g.crossplay   AS game_crossplay,
       u.username    AS host_username,
       u.level       AS host_level,
       u.avatar_url  AS host_avatar_url,
       u.region      AS host_region,
       (SELECT ARRAY_AGG(pp.platform ORDER BY pp.platform)
          FROM post_platforms pp WHERE pp.post_id = p.id) AS platforms,
       1 + (SELECT COUNT(*) FROM applications a
             WHERE a.post_id = p.id AND a.status = 'ACCEPTED') AS current_players
FROM lfg_posts p
JOIN games g ON g.id = p.game_id
JOIN users u ON u.id = p.host_id;

-- ---------------------------------------------------------------------
-- Vista: miembros de cada sala (anfitrión + solicitudes aceptadas)
-- Se usa en detalle_post (integrantes) y en historial_partidas (compañeros).
-- ---------------------------------------------------------------------
CREATE VIEW v_post_members AS
SELECT p.id AS post_id, u.id AS user_id, u.username, u.region, u.level, u.avatar_url,
       'HOST' AS role, p.created_at AS joined_at
FROM lfg_posts p
JOIN users u ON u.id = p.host_id
UNION ALL
SELECT a.post_id, u.id, u.username, u.region, u.level, u.avatar_url,
       'MEMBER', a.created_at
FROM applications a
JOIN users u ON u.id = a.applicant_id
WHERE a.status = 'ACCEPTED';

-- ---------------------------------------------------------------------
-- Vista: historial de partidas con los compañeros de cada una
-- Una fila por (usuario, partida terminada, compañero). already_reviewed
-- indica si el usuario ya calificó a ese compañero en esa partida.
-- Consulta típica: SELECT * FROM v_match_history WHERE user_id = :yo;
-- ---------------------------------------------------------------------
CREATE VIEW v_match_history AS
SELECT me.user_id,
       p.id          AS post_id,
       p.title,
       g.name        AS game_name,
       (SELECT ARRAY_AGG(pp.platform ORDER BY pp.platform)
          FROM post_platforms pp WHERE pp.post_id = p.id) AS platforms,
       p.closed_at,
       mate.user_id  AS teammate_id,
       mate.username AS teammate_username,
       mate.region   AS teammate_region,
       mate.level    AS teammate_level,
       EXISTS (SELECT 1 FROM user_blocks b
               WHERE b.blocker_id = me.user_id
                 AND b.blocked_id = mate.user_id) AS is_blocked,
       EXISTS (SELECT 1 FROM user_reviews r
               WHERE r.post_id = p.id
                 AND r.reviewer_id = me.user_id
                 AND r.target_user_id = mate.user_id) AS already_reviewed,
       EXISTS (SELECT 1 FROM user_reports rp
               WHERE rp.post_id = p.id
                 AND rp.reporter_id = me.user_id
                 AND rp.reported_user_id = mate.user_id) AS already_reported
FROM v_post_members me
JOIN v_post_members mate ON mate.post_id = me.post_id AND mate.user_id <> me.user_id
JOIN lfg_posts p ON p.id = me.post_id
JOIN games g ON g.id = p.game_id
WHERE p.status = 'CLOSED';

-- ---------------------------------------------------------------------
-- Vista: reportes para el panel de moderación, con la evidencia del chat
-- (mensajes del reportado en esa partida que el filtro PNL marcó como tóxicos)
-- y cuántas veces ha sido reportado en total.
-- ---------------------------------------------------------------------
CREATE VIEW v_reports_admin AS
SELECT r.*,
       rep.username        AS reporter_username,
       tgt.username        AS reported_username,
       tgt.level           AS reported_level,
       tgt.warnings_count  AS reported_warnings,
       tgt.account_status  AS reported_account_status,
       p.title             AS post_title,
       (SELECT COUNT(*) FROM user_reports x
         WHERE x.reported_user_id = r.reported_user_id) AS total_reports,
       (SELECT COUNT(*) FROM chat_messages m
         WHERE m.post_id = r.post_id
           AND m.sender_id = r.reported_user_id
           AND m.toxicity_level <> 'NONE') AS flagged_messages
FROM user_reports r
JOIN users rep ON rep.id = r.reporter_id
JOIN users tgt ON tgt.id = r.reported_user_id
LEFT JOIN lfg_posts p ON p.id = r.post_id;

-- ---------------------------------------------------------------------
-- Resuelve un reporte aplicando la decisión del administrador.
--   p_action: DISMISSED | WARNED | SUSPENDED | BANNED
--   p_days / p_levels: NULL = usar los valores de moderation_settings
-- Regla automática: si con una advertencia el usuario llega a
-- warnings_limit, se aplica auto_action (suspensión o eliminación).
-- Devuelve el estado final del reporte.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION resolve_report(
    p_report INTEGER, p_admin INTEGER, p_action VARCHAR,
    p_days SMALLINT DEFAULT NULL, p_levels SMALLINT DEFAULT NULL, p_notes VARCHAR DEFAULT NULL)
RETURNS VARCHAR AS $$
DECLARE
    s           moderation_settings%ROWTYPE;
    r           user_reports%ROWTYPE;
    v_status    VARCHAR := p_action;
    v_days      SMALLINT;
    v_levels    SMALLINT := 0;
    v_auto      BOOLEAN := FALSE;
    v_warnings  SMALLINT;
BEGIN
    SELECT * INTO s FROM moderation_settings WHERE id = 1;
    SELECT * INTO r FROM user_reports WHERE id = p_report FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'El reporte % no existe', p_report;
    END IF;
    IF r.status <> 'PENDING' THEN
        RAISE EXCEPTION 'El reporte % ya fue resuelto', p_report;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_admin AND role = 'ADMIN') THEN
        RAISE EXCEPTION 'Solo un administrador puede resolver reportes';
    END IF;

    IF p_action = 'WARNED' THEN
        v_levels := COALESCE(p_levels, s.warning_levels_removed);
        UPDATE users
           SET warnings_count = warnings_count + 1,
               penalty_xp = penalty_xp + v_levels * 100
         WHERE id = r.reported_user_id
        RETURNING warnings_count INTO v_warnings;

        IF v_warnings >= s.warnings_limit THEN
            v_auto := TRUE;
            v_status := CASE s.auto_action WHEN 'BAN' THEN 'BANNED' ELSE 'SUSPENDED' END;
            p_days := s.auto_suspension_days;
        END IF;
    END IF;

    IF v_status = 'SUSPENDED' THEN
        v_days := COALESCE(p_days, 7);
        IF p_action = 'SUSPENDED' THEN
            v_levels := COALESCE(p_levels, s.suspension_levels_removed);
        END IF;
        UPDATE users
           SET account_status = 'SUSPENDED',
               suspended_until = NOW() + make_interval(days => v_days),
               penalty_xp = penalty_xp + CASE WHEN v_auto THEN s.suspension_levels_removed ELSE v_levels END * 100,
               -- Tras una suspensión automática el contador vuelve a empezar
               warnings_count = CASE WHEN v_auto THEN 0 ELSE warnings_count END
         WHERE id = r.reported_user_id;
        IF v_auto THEN
            v_levels := v_levels + s.suspension_levels_removed;
        END IF;
    ELSIF v_status = 'BANNED' THEN
        UPDATE users SET account_status = 'BANNED' WHERE id = r.reported_user_id;
        -- Sus salas abiertas se cancelan
        UPDATE lfg_posts SET status = 'CANCELLED'
         WHERE host_id = r.reported_user_id AND status IN ('OPEN', 'FULL', 'IN_PROGRESS');
    END IF;

    UPDATE user_reports
       SET status = v_status,
           suspension_days = CASE WHEN v_status = 'SUSPENDED' THEN v_days END,
           levels_removed = LEAST(v_levels, 10),
           is_automatic = v_auto,
           resolved_by = p_admin,
           admin_notes = p_notes,
           resolved_at = NOW()
     WHERE id = p_report;

    RETURN v_status;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- Feed de salas para un usuario: salas abiertas, sin las de anfitriones
-- que el usuario tiene en su lista negra (ni las de cuentas sancionadas).
-- Uso: SELECT * FROM feed_for_user(:yo) WHERE game_id = ...;
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION feed_for_user(p_user INTEGER)
RETURNS SETOF v_lfg_posts AS $$
    SELECT v.*
    FROM v_lfg_posts v
    JOIN users h ON h.id = v.host_id
    WHERE v.status IN ('OPEN', 'FULL')
      AND h.account_status = 'ACTIVE'
      AND NOT EXISTS (SELECT 1 FROM user_blocks b
                      WHERE b.blocker_id = p_user AND b.blocked_id = v.host_id)
    ORDER BY v.created_at DESC;
$$ LANGUAGE sql STABLE;

-- ---------------------------------------------------------------------
-- Amigos y mensajes privados (también en migracion_amigos.sql para bases existentes)
-- ---------------------------------------------------------------------
-- Amigos: una persona envía una solicitud y la otra la acepta.
-- Si la rechaza, la fila se borra (no queda registro).
CREATE TABLE friendships (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    requester_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    addressee_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status          VARCHAR(8)   NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'ACCEPTED')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    responded_at    TIMESTAMPTZ,
    CHECK (requester_id <> addressee_id),
    CHECK ((status = 'PENDING') = (responded_at IS NULL))
);

-- Solo puede existir UNA fila por pareja, sin importar quién envió la solicitud
CREATE UNIQUE INDEX uq_friendships_pair
    ON friendships (LEAST(requester_id, addressee_id), GREATEST(requester_id, addressee_id));
CREATE INDEX idx_friendships_addressee ON friendships (addressee_id, status);
CREATE INDEX idx_friendships_requester ON friendships (requester_id, status);

-- Mensajes privados entre amigos. toxicity_level lo calcula el filtro anti-toxicidad
-- y cada receptor ve el mensaje según su propio toxicity_filter_level.
CREATE TABLE direct_messages (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sender_id       INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message         VARCHAR(500) NOT NULL CHECK (char_length(trim(message)) > 0),
    toxicity_level  VARCHAR(6)   NOT NULL DEFAULT 'NONE'
                    CHECK (toxicity_level IN ('NONE', 'MILD', 'SEVERE')),
    sent_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    read_at         TIMESTAMPTZ,
    CHECK (sender_id <> recipient_id)
);

-- Conversación entre dos personas, en orden
CREATE INDEX idx_direct_messages_pair
    ON direct_messages (LEAST(sender_id, recipient_id), GREATEST(sender_id, recipient_id), id);
-- Mensajes sin leer de cada persona (para el contador de la campanita)
CREATE INDEX idx_direct_messages_unread
    ON direct_messages (recipient_id) WHERE read_at IS NULL;
