-- =====================================================================
-- SquadFinder LFG - Datos iniciales de catálogo (géneros y juegos)
-- Ejecutar después de schema.sql. Necesario también en producción.
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

INSERT INTO games (name, genre_id) VALUES
    ('Valorant',                (SELECT id FROM genres WHERE name = 'Shooter')),
    ('Counter-Strike 2',        (SELECT id FROM genres WHERE name = 'Shooter')),
    ('Overwatch 2',             (SELECT id FROM genres WHERE name = 'Shooter')),
    ('Marvel Rivals',           (SELECT id FROM genres WHERE name = 'Shooter')),
    ('League of Legends',       (SELECT id FROM genres WHERE name = 'MOBA')),
    ('Dota 2',                  (SELECT id FROM genres WHERE name = 'MOBA')),
    ('Fortnite',                (SELECT id FROM genres WHERE name = 'Battle Royale')),
    ('Apex Legends',            (SELECT id FROM genres WHERE name = 'Battle Royale')),
    ('Call of Duty: Warzone',   (SELECT id FROM genres WHERE name = 'Battle Royale')),
    ('Diablo IV',               (SELECT id FROM genres WHERE name = 'RPG')),
    ('Destiny 2',               (SELECT id FROM genres WHERE name = 'RPG')),
    ('Rocket League',           (SELECT id FROM genres WHERE name = 'Deportes')),
    ('EA Sports FC',            (SELECT id FROM genres WHERE name = 'Deportes')),
    ('Age of Empires IV',       (SELECT id FROM genres WHERE name = 'Estrategia')),
    ('Street Fighter 6',        (SELECT id FROM genres WHERE name = 'Lucha')),
    ('Minecraft',               (SELECT id FROM genres WHERE name = 'Supervivencia'));
