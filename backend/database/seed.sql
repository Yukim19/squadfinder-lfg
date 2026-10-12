-- =====================================================================
-- SquadFinder LFG - Datos iniciales de catálogo (géneros, juegos, plataformas)
-- Ejecutar después de schema.sql. Necesario también en producción.
-- Plataformas y crossplay simplificados para el proyecto (octubre 2026).
-- El orden de los INSERT define los id (deben coincidir con frontend/js/catalogo.js).
-- =====================================================================

INSERT INTO genres (name) VALUES
    ('Shooter'),
    ('MOBA'),
    ('Battle Royale'),
    ('RPG'),
    ('Deportes'),
    ('Estrategia'),
    ('Lucha'),
    ('Supervivencia'),
    ('Acción'),
    ('Aventura'),
    ('Carreras'),
    ('Simulación'),
    ('Cartas'),
    ('Terror'),
    ('MMO'),
    ('Party');

INSERT INTO games (name, genre_id, crossplay)
SELECT v.name, g.id, v.crossplay
FROM (VALUES
    -- PC y consolas
    (1,  'Valorant',                     'Shooter',       FALSE),
    (2,  'Counter-Strike 2',             'Shooter',       FALSE),
    (3,  'Overwatch 2',                  'Shooter',       TRUE),
    (4,  'Marvel Rivals',                'Shooter',       TRUE),
    (5,  'League of Legends',            'MOBA',          FALSE),
    (6,  'Dota 2',                       'MOBA',          FALSE),
    (7,  'Fortnite',                     'Battle Royale', TRUE),
    (8,  'Apex Legends',                 'Battle Royale', TRUE),
    (9,  'Call of Duty: Warzone',        'Battle Royale', TRUE),
    (10, 'Diablo IV',                    'RPG',           TRUE),
    (11, 'Destiny 2',                    'RPG',           TRUE),
    (12, 'Rocket League',                'Deportes',      TRUE),
    (13, 'EA Sports FC',                 'Deportes',      TRUE),
    (14, 'Age of Empires IV',            'Estrategia',    TRUE),
    (15, 'Street Fighter 6',             'Lucha',         TRUE),
    (16, 'Minecraft',                    'Supervivencia', TRUE),
    -- Móviles
    (17, 'Clash Royale',                 'Estrategia',    FALSE),
    (18, 'Brawl Stars',                  'Acción',        FALSE),
    (19, 'PUBG Mobile',                  'Battle Royale', FALSE),
    (20, 'Free Fire',                    'Battle Royale', FALSE),
    (21, 'Call of Duty: Mobile',         'Shooter',       FALSE),
    (22, 'Mobile Legends: Bang Bang',    'MOBA',          FALSE),
    (23, 'League of Legends: Wild Rift', 'MOBA',          FALSE),
    (24, 'Clash of Clans',               'Estrategia',    FALSE),
    (25, 'Pokémon Unite',                'MOBA',          TRUE),
    (26, 'Genshin Impact',               'Aventura',      TRUE),
    (27, 'Among Us',                     'Party',         TRUE),
    (28, 'Roblox',                       'Party',         TRUE),
    (29, 'Marvel Snap',                  'Cartas',        TRUE),
    -- Otros géneros
    (30, 'Mario Kart 8 Deluxe',          'Carreras',      FALSE),
    (31, 'Phasmophobia',                 'Terror',        TRUE),
    (32, 'World of Warcraft',            'MMO',           FALSE),
    (33, 'Stardew Valley',               'Simulación',    FALSE),
    (34, 'Hearthstone',                  'Cartas',        TRUE),
    (35, 'It Takes Two',                 'Aventura',      FALSE)
) AS v(orden, name, genre, crossplay)
JOIN genres g ON g.name = v.genre
ORDER BY v.orden;

INSERT INTO game_platforms (game_id, platform)
SELECT g.id, v.platform
FROM (VALUES
    ('Valorant', 'PC'), ('Valorant', 'PlayStation'), ('Valorant', 'Xbox'),
    ('Counter-Strike 2', 'PC'),
    ('Overwatch 2', 'PC'), ('Overwatch 2', 'PlayStation'), ('Overwatch 2', 'Xbox'), ('Overwatch 2', 'Switch'),
    ('Marvel Rivals', 'PC'), ('Marvel Rivals', 'PlayStation'), ('Marvel Rivals', 'Xbox'),
    ('League of Legends', 'PC'),
    ('Dota 2', 'PC'),
    ('Fortnite', 'PC'), ('Fortnite', 'PlayStation'), ('Fortnite', 'Xbox'), ('Fortnite', 'Switch'), ('Fortnite', 'Mobile'),
    ('Apex Legends', 'PC'), ('Apex Legends', 'PlayStation'), ('Apex Legends', 'Xbox'), ('Apex Legends', 'Switch'),
    ('Call of Duty: Warzone', 'PC'), ('Call of Duty: Warzone', 'PlayStation'), ('Call of Duty: Warzone', 'Xbox'),
    ('Diablo IV', 'PC'), ('Diablo IV', 'PlayStation'), ('Diablo IV', 'Xbox'),
    ('Destiny 2', 'PC'), ('Destiny 2', 'PlayStation'), ('Destiny 2', 'Xbox'),
    ('Rocket League', 'PC'), ('Rocket League', 'PlayStation'), ('Rocket League', 'Xbox'), ('Rocket League', 'Switch'),
    ('EA Sports FC', 'PC'), ('EA Sports FC', 'PlayStation'), ('EA Sports FC', 'Xbox'), ('EA Sports FC', 'Switch'),
    ('Age of Empires IV', 'PC'), ('Age of Empires IV', 'PlayStation'), ('Age of Empires IV', 'Xbox'),
    ('Street Fighter 6', 'PC'), ('Street Fighter 6', 'PlayStation'), ('Street Fighter 6', 'Xbox'),
    ('Minecraft', 'PC'), ('Minecraft', 'PlayStation'), ('Minecraft', 'Xbox'), ('Minecraft', 'Switch'), ('Minecraft', 'Mobile'),
    ('Clash Royale', 'Mobile'),
    ('Brawl Stars', 'Mobile'),
    ('PUBG Mobile', 'Mobile'),
    ('Free Fire', 'Mobile'),
    ('Call of Duty: Mobile', 'Mobile'),
    ('Mobile Legends: Bang Bang', 'Mobile'),
    ('League of Legends: Wild Rift', 'Mobile'),
    ('Clash of Clans', 'Mobile'),
    ('Pokémon Unite', 'Switch'), ('Pokémon Unite', 'Mobile'),
    ('Genshin Impact', 'PC'), ('Genshin Impact', 'PlayStation'), ('Genshin Impact', 'Mobile'),
    ('Among Us', 'PC'), ('Among Us', 'PlayStation'), ('Among Us', 'Xbox'), ('Among Us', 'Switch'), ('Among Us', 'Mobile'),
    ('Roblox', 'PC'), ('Roblox', 'PlayStation'), ('Roblox', 'Xbox'), ('Roblox', 'Mobile'),
    ('Marvel Snap', 'PC'), ('Marvel Snap', 'Mobile'),
    ('Mario Kart 8 Deluxe', 'Switch'),
    ('Phasmophobia', 'PC'), ('Phasmophobia', 'PlayStation'), ('Phasmophobia', 'Xbox'),
    ('World of Warcraft', 'PC'),
    ('Stardew Valley', 'PC'), ('Stardew Valley', 'PlayStation'), ('Stardew Valley', 'Xbox'), ('Stardew Valley', 'Switch'), ('Stardew Valley', 'Mobile'),
    ('Hearthstone', 'PC'), ('Hearthstone', 'Mobile'),
    ('It Takes Two', 'PC'), ('It Takes Two', 'PlayStation'), ('It Takes Two', 'Xbox')
) AS v(game, platform)
JOIN games g ON g.name = v.game;
