-- =====================================================================
-- SquadFinder LFG - Datos de DEMOSTRACIÓN (solo desarrollo y pruebas)
-- Ejecutar después de schema.sql y seed.sql. NO usar en producción.
-- Los auth0_id son ficticios; los usuarios reales se crean al iniciar sesión.
-- =====================================================================

INSERT INTO users (auth0_id, username, ui_language, preferred_language_speak,
                   preferred_language_write, toxicity_filter_level, is_onboarding_completed)
VALUES
    ('demo|ana',    'ana_gg',      'es', 'es', 'es', 'STRICT', TRUE),
    ('demo|bruno',  'bruno_tank',  'es', 'es', 'en', 'MEDIUM', TRUE),
    ('demo|carla',  'carla_heals', 'en', 'en', 'en', 'OFF',    TRUE),
    ('demo|diego',  'diego_entry', 'es', 'es', 'es', 'MEDIUM', TRUE);

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
    (u.username = 'diego_entry' AND g.name IN ('Valorant', 'Counter-Strike 2'));

INSERT INTO lfg_posts (host_id, game_id, title, description, platform, max_players,
                       rank_required, mic_required, required_language, status)
VALUES
    ((SELECT id FROM users WHERE username = 'ana_gg'),
     (SELECT id FROM games WHERE name = 'Valorant'),
     'Ranked tranqui esta noche', 'Buscamos dúo/trío para subir a Platino.',
     'PC', 5, 'Oro', TRUE, 'es', 'OPEN'),
    ((SELECT id FROM users WHERE username = 'carla_heals'),
     (SELECT id FROM games WHERE name = 'League of Legends'),
     'Flex queue, chill vibes', NULL,
     'PC', 5, NULL, FALSE, 'en', 'OPEN'),
    ((SELECT id FROM users WHERE username = 'bruno_tank'),
     (SELECT id FROM games WHERE name = 'Valorant'),
     'Partida de ayer', 'Sala ya terminada (para probar historial y reseñas).',
     'PC', 3, NULL, TRUE, 'es', 'CLOSED');

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
     (SELECT id FROM users WHERE username = 'bruno_tank'), 'Listo, ya estoy conectado', 'NONE');
