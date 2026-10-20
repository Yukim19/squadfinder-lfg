-- =====================================================================
-- Migración: amigos y mensajes privados
-- Para bases de datos que YA existen (por ejemplo tu PostgreSQL local).
-- Es seguro ejecutarla más de una vez. Las bases nuevas ya la incluyen en schema.sql.
--   python backend/database/crear_bd.py --migrar-amigos
-- =====================================================================

-- Amigos: una persona envía una solicitud y la otra la acepta.
-- Si la rechaza, la fila se borra (no queda registro).
CREATE TABLE IF NOT EXISTS friendships (
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
CREATE UNIQUE INDEX IF NOT EXISTS uq_friendships_pair
    ON friendships (LEAST(requester_id, addressee_id), GREATEST(requester_id, addressee_id));
CREATE INDEX IF NOT EXISTS idx_friendships_addressee ON friendships (addressee_id, status);
CREATE INDEX IF NOT EXISTS idx_friendships_requester ON friendships (requester_id, status);

-- Mensajes privados entre amigos. toxicity_level lo calcula el filtro anti-toxicidad
-- y cada receptor ve el mensaje según su propio toxicity_filter_level.
CREATE TABLE IF NOT EXISTS direct_messages (
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
CREATE INDEX IF NOT EXISTS idx_direct_messages_pair
    ON direct_messages (LEAST(sender_id, recipient_id), GREATEST(sender_id, recipient_id), id);
-- Mensajes sin leer de cada persona (para el contador de la campanita)
CREATE INDEX IF NOT EXISTS idx_direct_messages_unread
    ON direct_messages (recipient_id) WHERE read_at IS NULL;
