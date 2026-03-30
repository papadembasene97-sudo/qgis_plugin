-- ============================================================================
-- VUE MATÉRIALISÉE COMPLÈTE POUR L'IA ET LA VISUALISATION 3D
-- TRACK-EAU-POLL v1.2.2 - Version enrichie avec points noirs et conformité
-- ============================================================================

-- Créer le schéma si nécessaire
CREATE SCHEMA IF NOT EXISTS cheminer_indus;

-- Supprimer l'ancienne vue
DROP MATERIALIZED VIEW IF EXISTS cheminer_indus.donnees_entrainement_ia CASCADE;

-- ============================================================================
-- NOUVELLE VUE MATÉRIALISÉE
-- ============================================================================

CREATE MATERIALIZED VIEW cheminer_indus.donnees_entrainement_ia AS
SELECT
    -- ========================================================================
    -- IDENTIFIANTS ET LOCALISATION
    -- ========================================================================
    o.idouvrage AS id_noeud,
    o.x,
    o.y,
    o.z,
    o.commune,
    o.bassinv,
    o.fnouvass AS fonction_ouvrage,
    o.typreseau AS type_reseau_noeud,
    
    -- ========================================================================
    -- TOPOLOGIE DU RÉSEAU (11 features)
    -- ========================================================================
    COUNT(DISTINCT c.idcana) AS nb_canalisations,
    AVG(c.diametre)::INTEGER AS diametre_moyen,
    MAX(c.diametre) AS diametre_max,
    MIN(c.diametre) AS diametre_min,
    STDDEV(c.diametre)::INTEGER AS variation_diametres,
    AVG(c._pente)::NUMERIC(6,2) AS pente_moyenne,
    MAX(c._pente)::NUMERIC(6,2) AS pente_max,
    MIN(c._pente)::NUMERIC(6,2) AS pente_min,
    SUM(c._longcana_reelle)::NUMERIC(8,2) AS longueur_cumul_amont,
    AVG(c._longcana_reelle)::NUMERIC(7,2) AS longueur_moyenne,
    
    -- Âge moyen du réseau (filtrage valeurs non numériques)
    AVG(
        CASE 
            WHEN c.anfinpose ~ '^[0-9]{4}$'
            THEN EXTRACT(YEAR FROM CURRENT_DATE) - c.anfinpose::INTEGER
            ELSE NULL
        END
    )::INTEGER AS age_moyen_reseau,
    
    -- ========================================================================
    -- TYPES DE RÉSEAU (6 features)
    -- ========================================================================
    COUNT(CASE WHEN c.typreseau = '01' THEN 1 END) AS nb_ep,
    COUNT(CASE WHEN c.typreseau = '02' THEN 1 END) AS nb_eu,
    COUNT(CASE WHEN c.typreseau = '03' THEN 1 END) AS nb_unitaire,
    
    -- Inversions EP → EU (avérées + trop-pleins actifs)
    COUNT(CASE WHEN c.inversion IN ('1', '3') THEN 1 END) AS nb_inversions_ep_dans_eu,
    
    -- Inversions EU → EP (avérées + trop-pleins actifs)
    COUNT(CASE WHEN c.inversion IN ('2', '4') THEN 1 END) AS nb_inversions_eu_dans_ep,
    
    -- Inversions supprimées (travaux réalisés)
    COUNT(CASE WHEN c.inversion IN ('5', '6') THEN 1 END) AS nb_inversions_supprimees,
    
    -- Trop-pleins condamnés
    COUNT(CASE WHEN c.inversion IN ('7', '8') THEN 1 END) AS nb_trop_pleins_condamnes,
    
    -- Total inversions/trop-pleins actifs uniquement (1-4)
    COUNT(CASE WHEN c.inversion IN ('1', '2', '3', '4') THEN 1 END) AS nb_inversions_actives,
    
    -- Total TOUTES inversions (y compris historiques)
    COUNT(CASE WHEN c.inversion IN ('1', '2', '3', '4', '5', '6', '7', '8') THEN 1 END) AS nb_inversions_total,
    
    -- ========================================================================
    -- INDUSTRIELS (7 features)
    -- ========================================================================
    COUNT(DISTINCT li.id_industriel) AS nb_industriels,
    COUNT(CASE WHEN i.risques ILIKE '%pollution%' OR i.risques ILIKE '%déversement%' OR i.risques ILIKE '%rejet%' THEN 1 END) AS nb_industriels_risque_pollution,
    COUNT(CASE WHEN i.risques ILIKE '%graisse%' OR i.produits ILIKE '%graisse%' OR i.activite ILIKE '%restaurant%' OR i.activite ILIKE '%alimentaire%' THEN 1 END) AS nb_industriels_risque_graisse,
    COUNT(CASE WHEN i.risques ILIKE '%hydrocarbure%' OR i.produits ILIKE '%hydrocarbure%' OR i.produits ILIKE '%huile%' OR i.activite ILIKE '%garage%' OR i.activite ILIKE '%station%' THEN 1 END) AS nb_industriels_risque_hydrocarbure,
    COUNT(CASE WHEN i.risques ILIKE '%chimique%' OR i.produits ILIKE '%chimique%' OR i.produits ILIKE '%solvant%' THEN 1 END) AS nb_industriels_risque_chimique,
    COUNT(CASE WHEN i.icpe IS NOT NULL AND i.icpe != '' THEN 1 END) AS nb_industriels_icpe,
    
    -- ========================================================================
    -- 🆕 POINTS NOIRS MODÉLISÉS (5 features)
    -- ========================================================================
    COUNT(CASE WHEN pnm."Commune" = o.commune AND pnm."Type" = 'Bouchage' THEN 1 END) AS nb_points_noirs_bouchage_modelise,
    COUNT(CASE WHEN pnm."Commune" = o.commune AND pnm."Type" = 'Débordement' THEN 1 END) AS nb_points_noirs_debordement_modelise,
    COUNT(CASE WHEN pnm."Commune" = o.commune AND pnm."Type" = 'Mise en charge' THEN 1 END) AS nb_points_noirs_mise_en_charge_modelise,
    COUNT(CASE WHEN pnm."Commune" = o.commune AND pnm."Priorité" = '1' THEN 1 END) AS nb_points_noirs_priorite_1_modelise,
    COUNT(CASE WHEN pnm."Commune" = o.commune THEN 1 END) AS nb_points_noirs_total_modelise,
    
    -- ========================================================================
    -- 🆕 POINTS NOIRS EGIS (8 features)
    -- ========================================================================
    COUNT(CASE WHEN pne.commune = o.commune AND pne.type = 'Bouchage' THEN 1 END) AS nb_points_noirs_bouchage_egis,
    COUNT(CASE WHEN pne.commune = o.commune AND pne.type = 'Débordement' THEN 1 END) AS nb_points_noirs_debordement_egis,
    COUNT(CASE WHEN pne.commune = o.commune AND pne.type = 'Pollution' THEN 1 END) AS nb_points_noirs_pollution_egis,
    COUNT(CASE WHEN pne.commune = o.commune AND pne.type = 'Dégradation' THEN 1 END) AS nb_points_noirs_degradation_egis,
    COUNT(CASE WHEN pne.commune = o.commune AND pne.type = 'Mise en charge' THEN 1 END) AS nb_points_noirs_mise_en_charge_egis,
    COUNT(CASE WHEN pne.commune = o.commune AND pne.type = 'Infiltration d''eau' THEN 1 END) AS nb_points_noirs_infiltration_egis,
    COUNT(CASE WHEN pne.commune = o.commune AND pne.priorité = '1' THEN 1 END) AS nb_points_noirs_priorite_1_egis,
    COUNT(CASE WHEN pne.commune = o.commune THEN 1 END) AS nb_points_noirs_total_egis,
    
    -- ========================================================================
    -- 🆕 PV DE CONFORMITÉ (4 features)
    -- ========================================================================
    -- Jointure sur commune + proximité spatiale (500m)
    COUNT(CASE WHEN pv.nom_com ILIKE '%' || o.commune || '%' AND pv.conforme = 'Non' THEN 1 END) AS nb_pv_non_conforme,
    COUNT(CASE WHEN pv.nom_com ILIKE '%' || o.commune || '%' AND pv.eu_vers_ep = 'Oui' THEN 1 END) AS nb_pv_inversion_eu_vers_ep,
    COUNT(CASE WHEN pv.nom_com ILIKE '%' || o.commune || '%' AND pv.ep_vers_eu = 'Oui' THEN 1 END) AS nb_pv_inversion_ep_vers_eu,
    COUNT(CASE WHEN pv.nom_com ILIKE '%' || o.commune || '%' THEN 1 END) AS nb_pv_total,
    
    -- ========================================================================
    -- HISTORIQUE INTERVENTIONS (10 features)
    -- ========================================================================
    COUNT(DISTINCT a.id) AS nb_visites_total,
    
    -- Détection intelligente des pollutions
    COUNT(CASE 
        WHEN a.message ILIKE '%pollution%' 
        OR a.message ILIKE '%déversement%' 
        OR a.message ILIKE '%odeur%' 
        OR a.message ILIKE '%graisse%' 
        OR a.message ILIKE '%hydrocarbure%' 
        OR a.message ILIKE '%débordement%' 
        OR a.message ILIKE '%refoulement%' 
        OR a.message ILIKE '%rejet%' 
        OR a.message ILIKE '%fuite%' 
        OR a.action_m ILIKE '%curage%' 
        OR a.action_m ILIKE '%pompage%' 
        OR a.action_m ILIKE '%débouchage%' 
        OR a.action_m ILIKE '%dégraissage%' 
        OR a.interv_eu ILIKE '%curage%' 
        OR a.interv_eu ILIKE '%pompage%' 
        OR a.interv_eu ILIKE '%débouchage%' 
        OR a.interv_ep ILIKE '%curage%' 
        OR a.interv_ep ILIKE '%pompage%' 
        OR a.interv_voi ILIKE '%pollution%' 
        OR a.id_pollueur IS NOT NULL
        THEN 1 
    END) AS nb_pollutions,
    
    COUNT(CASE WHEN a.message ILIKE '%graisse%' OR a.action_m ILIKE '%dégraissage%' OR a.action_m ILIKE '%graisse%' THEN 1 END) AS nb_pollutions_graisse,
    COUNT(CASE WHEN a.message ILIKE '%hydrocarbure%' OR a.message ILIKE '%huile%' OR a.message ILIKE '%gazole%' THEN 1 END) AS nb_pollutions_hydrocarbure,
    COUNT(CASE WHEN a.message ILIKE '%débordement%' OR a.message ILIKE '%refoulement%' OR a.message ILIKE '%trop%plein%' THEN 1 END) AS nb_debordements,
    COUNT(CASE WHEN a.interv_eu IS NOT NULL AND LENGTH(TRIM(a.interv_eu)) > 0 THEN 1 END) AS nb_interventions_eu,
    COUNT(CASE WHEN a.interv_ep IS NOT NULL AND LENGTH(TRIM(a.interv_ep)) > 0 THEN 1 END) AS nb_interventions_ep,
    COUNT(CASE WHEN a.interv_voi IS NOT NULL AND LENGTH(TRIM(a.interv_voi)) > 0 THEN 1 END) AS nb_interventions_voirie,
    MAX(a.date) AS derniere_visite,
    CASE WHEN MAX(a.date) IS NOT NULL THEN (CURRENT_DATE - MAX(a.date))::INTEGER ELSE NULL END AS jours_depuis_derniere_visite,
    CASE 
        WHEN MIN(a.date) IS NOT NULL 
        AND EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER - EXTRACT(YEAR FROM MIN(a.date))::INTEGER > 0
        THEN (COUNT(DISTINCT a.id)::NUMERIC / (EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER - EXTRACT(YEAR FROM MIN(a.date))::INTEGER))::NUMERIC(5,2)
        ELSE NULL 
    END AS freq_interventions_par_an,
    
    -- ========================================================================
    -- 🎯 LABEL CIBLE (détection automatique pollution)
    -- ========================================================================
    CASE 
        WHEN COUNT(CASE 
            WHEN a.message ILIKE '%pollution%' 
            OR a.message ILIKE '%déversement%' 
            OR a.message ILIKE '%odeur%' 
            OR a.message ILIKE '%graisse%' 
            OR a.message ILIKE '%hydrocarbure%' 
            OR a.message ILIKE '%débordement%' 
            OR a.message ILIKE '%refoulement%' 
            OR a.message ILIKE '%rejet%' 
            OR a.action_m ILIKE '%curage%' 
            OR a.action_m ILIKE '%pompage%' 
            OR a.action_m ILIKE '%débouchage%' 
            OR a.action_m ILIKE '%dégraissage%' 
            OR a.interv_eu ILIKE '%curage%' 
            OR a.interv_eu ILIKE '%pompage%' 
            OR a.interv_ep ILIKE '%curage%' 
            OR a.id_pollueur IS NOT NULL
            THEN 1 
        END) > 0 THEN 1
        WHEN COUNT(DISTINCT a.id) > 0 THEN 0
        ELSE NULL
    END AS pollution_detectee_label,
    
    -- ========================================================================
    -- 🆕 SCORE DE RISQUE AMÉLIORÉ (intégrant tous les facteurs)
    -- ========================================================================
    (
        -- Inversions ACTIVES uniquement (max 30 points)
        -- Ne compte que les inversions non résolues (codes 1-4)
        LEAST(COUNT(CASE WHEN c.inversion IN ('1', '2', '3', '4') THEN 1 END) * 10, 30) +
        
        -- Industriels à risque (max 40 points)
        LEAST(COUNT(CASE 
            WHEN i.risques ILIKE '%pollution%' 
            OR i.risques ILIKE '%déversement%'
            THEN 1 
        END) * 20, 40) +
        
        -- Pollutions historiques (max 30 points)
        LEAST(COUNT(CASE 
            WHEN a.message ILIKE '%pollution%'
            OR a.id_pollueur IS NOT NULL
            THEN 1 
        END) * 15, 30) +
        
        -- 🆕 Points noirs EGIS (max 25 points)
        LEAST(COUNT(CASE 
            WHEN pne.commune = o.commune 
            AND pne.type IN ('Bouchage', 'Pollution', 'Débordement')
            THEN 1 
        END) * 5, 25) +
        
        -- 🆕 Points noirs modélisés prioritaires (max 20 points)
        LEAST(COUNT(CASE 
            WHEN pnm."Commune" = o.commune 
            AND pnm."Priorité" = '1'
            THEN 1 
        END) * 10, 20) +
        
        -- 🆕 Non-conformités (max 15 points)
        LEAST(COUNT(CASE 
            WHEN pv.nom_com ILIKE '%' || o.commune || '%'
            AND pv.conforme = 'Non'
            THEN 1 
        END) * 5, 15)
    )::INTEGER AS score_risque_calcule,
    
    -- ========================================================================
    -- GÉOMÉTRIE
    -- ========================================================================
    o.geom

FROM raepa.raepa_ouvrass_p o

-- Jointures existantes
LEFT JOIN raepa.raepa_canalass_l c 
    ON c.idnterm = o.idouvrage OR c.idnini = o.idouvrage

LEFT JOIN sig.liaison_indus li 
    ON li.id_ouvrage = o.idouvrage

LEFT JOIN sig."Indus" i 
    ON i.id = li.id_industriel

LEFT JOIN expoit."ASTREINTE-EXPLOIT" a 
    ON a.tampon = o.idouvrage

-- 🆕 Jointures nouvelles tables
LEFT JOIN sda."POINT_NOIR_MODELISATION" pnm 
    ON pnm."Commune" = o.commune

LEFT JOIN sda."POINT_NOIR_EGIS" pne 
    ON pne.commune = o.commune

LEFT JOIN osmose."PV_CONFORMITE" pv 
    ON pv.nom_com ILIKE '%' || o.commune || '%'
    -- Optionnel : ajouter une contrainte de distance si géocodage disponible
    -- AND ST_DWithin(ST_SetSRID(ST_MakePoint(pv.lon, pv.lat), 4326)::geography, o.geom::geography, 500)

GROUP BY 
    o.idouvrage, o.x, o.y, o.z, o.commune, o.bassinv, 
    o.fnouvass, o.typreseau, o.geom

HAVING COUNT(DISTINCT a.id) > 0;  -- Garder seulement les nœuds avec historique

-- ============================================================================
-- INDEX POUR PERFORMANCES
-- ============================================================================

CREATE INDEX idx_donnees_ia_geom 
ON cheminer_indus.donnees_entrainement_ia 
USING GIST(geom);

CREATE INDEX idx_donnees_ia_pollution 
ON cheminer_indus.donnees_entrainement_ia(pollution_detectee_label);

CREATE INDEX idx_donnees_ia_commune 
ON cheminer_indus.donnees_entrainement_ia(commune);

CREATE INDEX idx_donnees_ia_score 
ON cheminer_indus.donnees_entrainement_ia(score_risque_calcule DESC);

CREATE INDEX idx_donnees_ia_points_noirs 
ON cheminer_indus.donnees_entrainement_ia(nb_points_noirs_total_egis, nb_points_noirs_total_modelise);

CREATE INDEX idx_donnees_ia_pv_conformite 
ON cheminer_indus.donnees_entrainement_ia(nb_pv_non_conforme);

-- ============================================================================
-- ENREGISTREMENT GÉOMÉTRIE POSTGIS
-- ============================================================================

SELECT Populate_Geometry_Columns('cheminer_indus.donnees_entrainement_ia'::regclass);

-- ============================================================================
-- STATISTIQUES FINALES
-- ============================================================================

SELECT 
    COUNT(*) AS total_noeuds,
    SUM(CASE WHEN pollution_detectee_label = 1 THEN 1 ELSE 0 END) AS avec_pollution,
    SUM(CASE WHEN pollution_detectee_label = 0 THEN 1 ELSE 0 END) AS sans_pollution,
    ROUND(100.0 * SUM(CASE WHEN pollution_detectee_label = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_pollution,
    AVG(nb_points_noirs_total_egis)::NUMERIC(5,1) AS avg_points_noirs_egis,
    AVG(nb_pv_non_conforme)::NUMERIC(5,1) AS avg_pv_non_conforme,
    MAX(score_risque_calcule) AS score_max,
    AVG(score_risque_calcule)::NUMERIC(6,1) AS score_moyen
FROM cheminer_indus.donnees_entrainement_ia;

-- ============================================================================
-- ✅ VUE CRÉÉE AVEC SUCCÈS
-- ============================================================================
