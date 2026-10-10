-- =====================================================================
-- SquadFinder LFG - Datos iniciales de catálogo (géneros, juegos, plataformas)
-- Ejecutar después de schema.sql. Necesario también en producción.
-- Plataformas y crossplay simplificados para el proyecto (octubre 2026).
-- =====================================================================

INSERT INTO genres (name) VALUES
    ('Shooter'),
    ('MOBA'),
    ('Battle Royale'),
    ('RPG'),
    ('Deportes'),
    ('Estrategia'),
    ('Lucha'),
    ('Supervivencia');

INSERT INTO games (name, genre_id, crossplay) VALUES
    ('Valorant',                (SELECT id FROM genres WHERE name = 'Shooter'),       FALSE),
    ('Counter-Strike 2',        (SELECT id FROM genres WHERE name = 'Shooter'),       FALSE),
    ('Overwatch 2',             (SELECT id FROM genres WHERE name = 'Shooter'),       TRUE),
    ('Marvel Rivals',           (SELECT id FROM genres WHERE name = 'Shooter'),       TRUE),
    ('League of Legends',       (SELECT id FROM genres WHERE name = 'MOBA'),          FALSE),
    ('Dota 2',                  (SELECT id FROM genres WHERE name = 'MOBA'),          FALSE),
    ('Fortnite',                (SELECT id FROM genres WHERE name = 'Battle Royale'), TRUE),
    ('Apex Legends',            (SELECT id FROM genres WHERE name = 'Battle Royale'), TRUE),
    ('Call of Duty: Warzone',   (SELECT id FROM genres WHERE name = 'Battle Royale'), TRUE),
    ('Diablo IV',               (SELECT id FROM genres WHERE name = 'RPG'),           TRUE),
    ('Destiny 2',               (SELECT id FROM genres WHERE name = 'RPG'),           TRUE),
    ('Rocket League',           (SELECT id FROM genres WHERE name = 'Deportes'),      TRUE),
    ('EA Sports FC',            (SELECT id FROM genres WHERE name = 'Deportes'),      TRUE),
    ('Age of Empires IV',       (SELECT id FROM genres WHERE name = 'Estrategia'),    TRUE),
    ('Street Fighter 6',        (SELECT id FROM genres WHERE name = 'Lucha'),         TRUE),
    ('Minecraft',               (SELECT id FROM genres WHERE name = 'Supervivencia'), TRUE);

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
    ('Minecraft', 'PC'), ('Minecraft', 'PlayStation'), ('Minecraft', 'Xbox'), ('Minecraft', 'Switch'), ('Minecraft', 'Mobile')
) AS v(game, platform)
JOIN games g ON g.name = v.game;
