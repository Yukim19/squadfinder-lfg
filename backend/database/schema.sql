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
    genre_id    SMALLINT NOT NULL REFERENCES genres(id) ON DELETE RESTRICT
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
    -- Promedio de user_reviews.rating; lo mantiene el trigger trg_reviews_honor
    honor_score                 NUMERIC(3,2) NOT NULL DEFAULT 0
                                CHECK (honor_score BETWEEN 0 AND 5),
    is_onboarding_completed     BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
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
    platform            VARCHAR(12)  NOT NULL
                        CHECK (platform IN ('PC', 'PlayStation', 'Xbox', 'Switch', 'Mobile')),
    max_players         SMALLINT     NOT NULL CHECK (max_players BETWEEN 2 AND 10),
    rank_required       VARCHAR(50),
    mic_required        BOOLEAN      NOT NULL DEFAULT FALSE,
    required_language   CHAR(2)      NOT NULL DEFAULT 'es'
                        CHECK (required_language IN ('es', 'en')),
    status              VARCHAR(11)  NOT NULL DEFAULT 'OPEN'
                        CHECK (status IN ('OPEN', 'FULL', 'IN_PROGRESS', 'CLOSED', 'CANCELLED')),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMPTZ
);

CREATE INDEX idx_lfg_posts_status_game ON lfg_posts (status, game_id);
CREATE INDEX idx_lfg_posts_host ON lfg_posts (host_id);

CREATE TRIGGER trg_lfg_posts_updated_at
    BEFORE UPDATE ON lfg_posts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

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
-- Vista: salas con el número actual de jugadores
-- current_players se calcula (anfitrión + solicitudes aceptadas) en vez de
-- guardarse, para evitar datos duplicados que se desincronicen.
-- ---------------------------------------------------------------------
CREATE VIEW v_lfg_posts AS
SELECT p.*,
       g.name     AS game_name,
       u.username AS host_username,
       u.honor_score AS host_honor_score,
       1 + COUNT(a.id) FILTER (WHERE a.status = 'ACCEPTED') AS current_players
FROM lfg_posts p
JOIN games g ON g.id = p.game_id
JOIN users u ON u.id = p.host_id
LEFT JOIN applications a ON a.post_id = p.id
GROUP BY p.id, g.name, u.username, u.honor_score;
