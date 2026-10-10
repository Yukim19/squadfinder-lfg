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
    preferred_language_speak    CHAR(2)      NOT NULL DEFAULT 'es'
                                CHECK (preferred_language_speak IN ('es', 'en')),
    preferred_language_write    CHAR(2)      NOT NULL DEFAULT 'es'
                                CHECK (preferred_language_write IN ('es', 'en')),
    toxicity_filter_level       VARCHAR(6)   NOT NULL DEFAULT 'MEDIUM'
                                CHECK (toxicity_filter_level IN ('OFF', 'MEDIUM', 'STRICT')),
    -- Región de juego; se pide en el onboarding (NULL hasta completarlo)
    region                      VARCHAR(11)
                                CHECK (region IN ('NA_EAST', 'NA_WEST', 'LATAM_NORTH', 'LATAM_SOUTH',
                                                  'BRAZIL', 'EUROPE', 'ASIA', 'OCEANIA')),
    -- Promedio de user_reviews.rating; lo mantiene el trigger trg_reviews_honor
    honor_score                 NUMERIC(3,2) NOT NULL DEFAULT 0
                                CHECK (honor_score BETWEEN 0 AND 5),
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

-- Recalcula users.honor_score cada vez que cambia una reseña
CREATE OR REPLACE FUNCTION refresh_honor_score()
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
           SET honor_score = COALESCE(
                   (SELECT ROUND(AVG(rating), 2) FROM user_reviews WHERE target_user_id = target), 0)
         WHERE id = target;
    END LOOP;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_reviews_honor
    AFTER INSERT OR UPDATE OR DELETE ON user_reviews
    FOR EACH ROW EXECUTE FUNCTION refresh_honor_score();

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
-- descartarlo, suspender la cuenta unos días o eliminarla (BANNED).
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
                        CHECK (status IN ('PENDING', 'DISMISSED', 'SUSPENDED', 'BANNED')),
    -- Administrador que resolvió el reporte y su nota
    resolved_by         INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    admin_notes         VARCHAR(500),
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CHECK (reporter_id <> reported_user_id),
    CHECK ((status = 'PENDING') = (resolved_at IS NULL))
);

-- Un jugador no puede reportar dos veces a la misma persona por la misma partida
CREATE UNIQUE INDEX uq_user_reports_once ON user_reports (reporter_id, reported_user_id, post_id);
CREATE INDEX idx_user_reports_status ON user_reports (status, created_at);
CREATE INDEX idx_user_reports_reported ON user_reports (reported_user_id);

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
       u.honor_score AS host_honor_score,
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
SELECT p.id AS post_id, u.id AS user_id, u.username, u.region, u.honor_score,
       'HOST' AS role, p.created_at AS joined_at
FROM lfg_posts p
JOIN users u ON u.id = p.host_id
UNION ALL
SELECT a.post_id, u.id, u.username, u.region, u.honor_score,
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
       mate.honor_score AS teammate_honor_score,
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
       tgt.honor_score     AS reported_honor_score,
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
