-- =====================================================================
-- SquadFinder LFG - Datos de DEMOSTRACIÓN (solo desarrollo y pruebas)
-- Ejecutar después de schema.sql y seed.sql. NO usar en producción.
-- Los auth0_id son ficticios; los usuarios reales se crean al iniciar sesión.
-- =====================================================================

-- ana_gg es ADMIN para poder probar el panel de moderación
INSERT INTO users (auth0_id, username, ui_language, preferred_language_speak,
                   preferred_language_write, toxicity_filter_level, region, is_onboarding_completed, role)
VALUES
    ('demo|ana',    'ana_gg',      'es', 'es', 'es', 'STRICT', 'NA_EAST',     TRUE, 'ADMIN'),
    ('demo|bruno',  'bruno_tank',  'es', 'es', 'en', 'MEDIUM', 'LATAM_NORTH', TRUE, 'USER'),
    ('demo|carla',  'carla_heals', 'en', 'en', 'en', 'OFF',    'NA_WEST',     TRUE, 'USER'),
    ('demo|diego',  'diego_entry', 'es', 'es', 'es', 'MEDIUM', 'LATAM_SOUTH', TRUE, 'USER');

INSERT INTO linked_accounts (user_id, provider, external_username) VALUES
    ((SELECT id FROM users WHERE username = 'ana_gg'),     'discord', 'ana_gg'),
    ((SELECT id FROM users WHERE username = 'ana_gg'),     'twitch',  'ana_gg_live'),
    ((SELECT id FROM users WHERE username = 'bruno_tank'), 'steam',   'brunotank');

INSERT INTO user_genres (user_id, genre_id)
SELECT u.id, g.id FROM users u JOIN genres g ON
    (u.username = 'ana_gg'      AND g.name IN ('Shooter', 'Battle Royale')) OR
    (u.username = 'bruno_tank'  AND g.name IN ('Shooter', 'MOBA')) OR
    (u.username = 'carla_heals' AND g.name IN ('MOBA', 'RPG')) OR
    (u.username = 'diego_entry' AND g.name IN ('Shooter'));

INSERT INTO user_games (user_id, game_id)
SELECT u.id, g.id FROM users u JOIN games g ON
    (u.username = 'ana_gg'      AND g.name IN ('Valorant', 'Fortnite')) OR
    (u.username = 'bruno_tank'  AND g.name IN ('Valorant', 'League of Legends')) OR
    (u.username = 'carla_heals' AND g.name IN ('League of Legends', 'Diablo IV')) OR
    (u.username = 'diego_entry' AND g.name IN ('Valorant', 'Counter-Strike 2', 'Fortnite'));

INSERT INTO lfg_posts (host_id, game_id, title, description, max_players, play_mode,
                       rank_required, mic_required, required_language, status)
VALUES
    ((SELECT id FROM users WHERE username = 'ana_gg'),
     (SELECT id FROM games WHERE name = 'Valorant'),
     'Ranked tranqui esta noche', 'Buscamos dúo/trío para subir a Platino.',
     5, 'COMPETITIVE', 'Oro', TRUE, 'es', 'OPEN'),
    ((SELECT id FROM users WHERE username = 'carla_heals'),
     (SELECT id FROM games WHERE name = 'League of Legends'),
     'Flex queue, chill vibes', NULL,
     5, 'CASUAL', NULL, FALSE, 'en', 'OPEN'),
    ((SELECT id FROM users WHERE username = 'bruno_tank'),
     (SELECT id FROM games WHERE name = 'Valorant'),
     'Partida de ayer', 'Sala ya terminada (para probar historial y reseñas).',
     3, 'COMPETITIVE', NULL, TRUE, 'es', 'CLOSED'),
    ((SELECT id FROM users WHERE username = 'diego_entry'),
     (SELECT id FROM games WHERE name = 'Fortnite'),
     'Dúos cross-plataforma', 'Cualquier plataforma e idioma, solo buena onda.',
     4, 'CASUAL', NULL, FALSE, 'any', 'OPEN');

-- Valorant y LoL no tienen crossplay (una plataforma); Fortnite sí (varias)
INSERT INTO post_platforms (post_id, platform)
SELECT p.id, v.platform
FROM (VALUES
    ('Ranked tranqui esta noche', 'PC'),
    ('Flex queue, chill vibes', 'PC'),
    ('Partida de ayer', 'PC'),
    ('Dúos cross-plataforma', 'PC'),
    ('Dúos cross-plataforma', 'PlayStation'),
    ('Dúos cross-plataforma', 'Switch')
) AS v(title, platform)
JOIN lfg_posts p ON p.title = v.title;

INSERT INTO applications (post_id, applicant_id, status, message) VALUES
    ((SELECT id FROM lfg_posts WHERE title = 'Ranked tranqui esta noche'),
     (SELECT id FROM users WHERE username = 'bruno_tank'), 'ACCEPTED', 'Juego de iniciador'),
    ((SELECT id FROM lfg_posts WHERE title = 'Ranked tranqui esta noche'),
     (SELECT id FROM users WHERE username = 'diego_entry'), 'PENDING', NULL),
    ((SELECT id FROM lfg_posts WHERE title = 'Partida de ayer'),
     (SELECT id FROM users WHERE username = 'ana_gg'), 'ACCEPTED', NULL),
    ((SELECT id FROM lfg_posts WHERE title = 'Partida de ayer'),
     (SELECT id FROM users WHERE username = 'diego_entry'), 'ACCEPTED', NULL);

UPDATE lfg_posts SET closed_at = NOW() - INTERVAL '1 day' WHERE title = 'Partida de ayer';

INSERT INTO user_reviews (post_id, reviewer_id, target_user_id, rating, tag, comment) VALUES
    ((SELECT id FROM lfg_posts WHERE title = 'Partida de ayer'),
     (SELECT id FROM users WHERE username = 'ana_gg'),
     (SELECT id FROM users WHERE username = 'bruno_tank'), 5, 'GREAT_LEADER', 'Muy buen shotcalling'),
    ((SELECT id FROM lfg_posts WHERE title = 'Partida de ayer'),
     (SELECT id FROM users WHERE username = 'diego_entry'),
     (SELECT id FROM users WHERE username = 'bruno_tank'), 4, 'FRIENDLY', NULL),
    ((SELECT id FROM lfg_posts WHERE title = 'Partida de ayer'),
     (SELECT id FROM users WHERE username = 'bruno_tank'),
     (SELECT id FROM users WHERE username = 'ana_gg'), 5, 'SKILLED', 'Clutch increíble');

INSERT INTO chat_messages (post_id, sender_id, message, toxicity_level) VALUES
    ((SELECT id FROM lfg_posts WHERE title = 'Ranked tranqui esta noche'),
     (SELECT id FROM users WHERE username = 'ana_gg'), '¡Hola! Entramos en 10 min', 'NONE'),
    ((SELECT id FROM lfg_posts WHERE title = 'Ranked tranqui esta noche'),
     (SELECT id FROM users WHERE username = 'bruno_tank'), 'Listo, ya estoy conectado', 'NONE'),
    ((SELECT id FROM lfg_posts WHERE title = 'Ranked tranqui esta noche'),
     (SELECT id FROM users WHERE username = 'bruno_tank'), 'El de la otra sala es malísimo, que desinstale', 'MILD'),
    ((SELECT id FROM lfg_posts WHERE title = 'Partida de ayer'),
     (SELECT id FROM users WHERE username = 'bruno_tank'), 'Diego eres un inútil, nos hiciste perder', 'SEVERE');

-- Reportes de moderación: uno pendiente y uno ya resuelto (descartado)
INSERT INTO user_reports (reporter_id, reported_user_id, post_id, reason, comment) VALUES
    ((SELECT id FROM users WHERE username = 'diego_entry'),
     (SELECT id FROM users WHERE username = 'bruno_tank'),
     (SELECT id FROM lfg_posts WHERE title = 'Partida de ayer'),
     'TOXIC_CHAT', 'Me insultó en el chat cuando perdimos la ronda y siguió burlándose.');

INSERT INTO user_reports (reporter_id, reported_user_id, post_id, reason, comment,
                          status, resolved_by, admin_notes, resolved_at) VALUES
    ((SELECT id FROM users WHERE username = 'bruno_tank'),
     (SELECT id FROM users WHERE username = 'diego_entry'),
     (SELECT id FROM lfg_posts WHERE title = 'Partida de ayer'),
     'AFK_GRIEFING', 'Se quedó quieto dos rondas sin jugar.',
     'DISMISSED', (SELECT id FROM users WHERE username = 'ana_gg'),
     'Tuvo problemas de conexión; no fue intencional.', NOW() - INTERVAL '12 hours');
