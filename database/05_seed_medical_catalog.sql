
/* =========================================================
   VETMATE - MEDICAL CATALOG SEED
   File: database/05_seed_medical_catalog.sql

   Prerequisite:
   - 04_medical_pet.sql

   Safe to rerun:
   - Species: ON CONFLICT(name)
   - Breeds: ON CONFLICT(speciesID, name)
   ========================================================= */

BEGIN;

/* 1. SPECIES */

INSERT INTO medical.species ("name", "isActive")
VALUES
    ('Chó', TRUE),
    ('Mèo', TRUE),
    ('Thỏ', TRUE),
    ('Chim', TRUE),
    ('Hamster', TRUE),
    ('Bò sát', TRUE)
ON CONFLICT ("name") DO NOTHING;


/* 2. BREEDS */

WITH breed_seed ("speciesName", "breedName") AS (
    VALUES
        ('Chó', 'Poodle'),
        ('Chó', 'Chihuahua'),
        ('Chó', 'Corgi'),
        ('Chó', 'Golden Retriever'),
        ('Chó', 'Labrador Retriever'),
        ('Chó', 'Husky'),
        ('Chó', 'Shiba Inu'),
        ('Chó', 'Phốc sóc'),
        ('Chó', 'Chó ta'),
        ('Chó', 'Chó lai'),

        ('Mèo', 'Mèo Anh lông ngắn'),
        ('Mèo', 'Mèo Anh lông dài'),
        ('Mèo', 'Mèo Ba Tư'),
        ('Mèo', 'Mèo Xiêm'),
        ('Mèo', 'Maine Coon'),
        ('Mèo', 'Ragdoll'),
        ('Mèo', 'Mèo ta'),
        ('Mèo', 'Mèo lai'),

        ('Thỏ', 'Holland Lop'),
        ('Thỏ', 'Netherland Dwarf'),
        ('Thỏ', 'Mini Rex'),
        ('Thỏ', 'Thỏ lai'),

        ('Chim', 'Yến phụng'),
        ('Chim', 'Vẹt Lovebird'),
        ('Chim', 'Cockatiel'),
        ('Chim', 'Chim lai'),

        ('Hamster', 'Syrian'),
        ('Hamster', 'Winter White'),
        ('Hamster', 'Campbell'),
        ('Hamster', 'Roborovski'),

        ('Bò sát', 'Rồng Úc'),
        ('Bò sát', 'Tắc kè báo'),
        ('Bò sát', 'Rùa tai đỏ')
)
INSERT INTO medical.breeds (
    "speciesID",
    "name",
    "isActive"
)
SELECT
    s."speciesID",
    b."breedName",
    TRUE
FROM breed_seed b
JOIN medical.species s
    ON s."name" = b."speciesName"
ON CONFLICT ("speciesID", "name") DO NOTHING;

COMMIT;
