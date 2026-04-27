# Module d'analyse comportementale — Synthèse pour soutenance (v1)

## 1. En une phrase
Ce module transforme des événements d'usage smartphone en deux scores complémentaires (risque de dépendance et bien-être numérique), puis génère des recommandations parentales explicables, validées sur 15 archétypes cliniques avec une couverture de règles de 9/9.

## 2. Ce que fait le module
- Le moteur calcule deux scores globaux entre 0 et 1: un score de risque de dépendance et un score de bien-être numérique.
- Chaque score est décomposé en 5 sous-signaux explicables (10 au total) pour rendre chaque résultat interprétable par un parent et défendable techniquement.
- Une couche de recommandations règle-par-règle applique 9 règles structurées (sévérités high, medium, low, positive) avec traçabilité du sous-score déclencheur.
- Le système impose une formulation parentale non stigmatisante dans les messages (contrôles automatisés sur le vocabulaire sensible).
- L'ensemble est déterministe et reproductible: mêmes profils, mêmes seeds, mêmes sorties.

## 3. Ancrage clinique

| Seuil ou concept clinique | Source académique |
|---|---|
| Limites de temps d'écran quotidiennes par âge | AAP, *Media and Young Minds* (2016) |
| Sédentarité, sommeil et usage écran chez l'enfant | WHO Guidelines (2019) |
| Fenêtre nocturne et impact sommeil adolescent | AASM Pediatric Sleep Recommendations (2014) |
| Compulsivité et usage problématique smartphone | Panova & Carbonell (2018) |
| Escalade hebdomadaire de l'usage (slope) | Kwon et al., Smartphone Addiction Scale (2013) |

## 4. Évaluation reproductible

| Métrique | Valeur |
|---|---|
| Profils synthétiques | 15 |
| Couverture des règles | 9/9 |
| Scores dans la plage attendue | 15/15 |
| Recommandations requises présentes | 15/15 |
| Recommandations interdites absentes | 15/15 |
| Temps d'exécution du benchmark | < 5 secondes |
| Tests unitaires total | 229 |
| Couverture de code (module comportemental) | 99% |

Reproductible à partir des seeds fixes 101-115 via la commande documentée dans le rapport baseline.

```powershell
.\.venv\Scripts\python.exe -m evaluation.behavioral.scripts.run_behavioral_benchmark --profiles evaluation/behavioral/datasets/behavioral_profiles_v1.json --report-name behavioral_baseline_v1.md --assert-ranges --export-actuals evaluation/behavioral/reports/behavioral_baseline_v1.json
```

## 5. Ce que distingue ce module
Le module ne réduit pas l'analyse à un score unique: il modélise une dimension de risque et une dimension de qualité d'équilibre. Sur les extrêmes, la cohérence est forte: `pure_educational_7yo` obtient l'addiction minimale (0.056) et le bien-être maximal (0.925), alors que `sleep_deprived_10yo` obtient l'addiction maximale (0.468) et le bien-être minimal (0.295). Dans la zone modérée, les dimensions divergent de façon informative: `rising_concern_9yo` (0.340 / 0.596) et `compulsive_user_10yo` (0.344 / 0.563) montrent un risque non négligeable sans effondrement complet du bien-être. Cette divergence est précisément utile pour la décision parentale, car elle évite la redondance et améliore la granularité de l'intervention.

## 6. Couverture des 15 archétypes cliniques

| Archétype | Âge | Score addiction | Score bien-être | Catégorie |
|---|---:|---:|---:|---|
| sleep_deprived_10yo | 10 | 0.468 | 0.295 | élevé |
| social_media_heavy_14yo | 14 | 0.451 | 0.336 | élevé |
| nocturnal_teen_15yo | 15 | 0.425 | 0.326 | élevé |
| heavy_escalating_12yo | 12 | 0.404 | 0.477 | élevé |
| compulsive_user_10yo | 10 | 0.344 | 0.563 | modéré |
| rising_concern_9yo | 9 | 0.340 | 0.596 | modéré |
| post_intervention_recovering_13yo | 13 | 0.187 | 0.661 | faible |
| low_engagement_8yo | 8 | 0.178 | 0.443 | faible |
| weekend_spike_11yo | 11 | 0.161 | 0.670 | faible |
| educational_focused_9yo | 9 | 0.152 | 0.791 | faible |
| edge_case_zero_usage | 10 | 0.150 | 0.400 | faible |
| balanced_teen_16yo | 16 | 0.143 | 0.747 | faible |
| moderate_family_7yo | 7 | 0.103 | 0.841 | faible |
| balanced_child_8yo | 8 | 0.093 | 0.842 | faible |
| pure_educational_7yo | 7 | 0.056 | 0.925 | faible |

## 7. Couverture des 9 règles de recommandation

| Règle | Sévérité | Déclenchée sur |
|---|---|---|
| screen_curfew | high | nocturnal_teen_15yo, sleep_deprived_10yo |
| weekly_escalation_alert | high | heavy_escalating_12yo, rising_concern_9yo |
| daily_limit_reminder | medium | social_media_heavy_14yo, sleep_deprived_10yo |
| session_break | medium | compulsive_user_10yo, social_media_heavy_14yo |
| imbalance_warning | medium | heavy_escalating_12yo, nocturnal_teen_15yo, social_media_heavy_14yo, sleep_deprived_10yo, low_engagement_8yo, edge_case_zero_usage |
| real_activity_prompt | medium | social_media_heavy_14yo, low_engagement_8yo, edge_case_zero_usage |
| educational_boost | low | heavy_escalating_12yo, nocturnal_teen_15yo, compulsive_user_10yo, social_media_heavy_14yo, sleep_deprived_10yo |
| family_time_suggestion | low | edge_case_zero_usage |
| balance_celebration | positive | balanced_child_8yo, educational_focused_9yo, moderate_family_7yo, balanced_teen_16yo, pure_educational_7yo |

## 8. Limites honnêtement reconnues
- Les profils d'évaluation sont synthétiques; ils ne remplacent pas une validation sur données terrain longitudinales.
- Le scoring est actuellement rule-based; il n'intègre pas encore de couche ML supervisée apprenant des retours parents.
- Les motifs circadiens sont simplifiés (notamment l'effet week-end via multiplicateur).
- Les seuils cliniques proviennent de la littérature internationale et ne sont pas encore recalibrés sur une cohorte tunisienne dédiée.

## 9. Travaux futurs
- Lancer un pilote contrôlé sur données réelles anonymisées pour valider stabilité et acceptabilité parentale.
- Ajouter une couche ML supervisée entraînée sur des labels parents (concordance score machine versus perception humaine).
- Raffiner la détection temporelle (rythmes veille-sommeil, variabilité intra-semaine, pics contextuels).
- Évaluer l'impact réel des recommandations par A/B testing (adhérence, diminution nocturne, amélioration bien-être).

## 10. Questions anticipées du jury + réponses courtes
**Q1. Pourquoi du rule-based et pas du ML?**  
Le choix est volontairement pragmatique: en phase PFE, la priorité est l'explicabilité clinique, la reproductibilité et la traçabilité de chaque décision. Le rule-based permet de lier explicitement chaque recommandation à un signal mesuré. Une couche ML est prévue en extension, pas en substitution.

**Q2. Vos seuils cliniques sont-ils défendables sur le terrain tunisien?**  
Ils sont défendables comme baseline internationale, car adossés à des sources reconnues (AAP, WHO, AASM, SAS). Nous ne prétendons pas qu'ils soient optimaux localement. Le plan de phase suivante prévoit un recalibrage empirique sur données locales anonymisées.

**Q3. Pourquoi deux scores au lieu d'un seul?**  
Un score unique écrase l'information. Ici, le risque et le bien-être convergent aux extrêmes mais divergent dans les profils intermédiaires, ce qui améliore la qualité de la décision parentale. Cette non-redondance est démontrée quantitativement sur les archétypes modérés.

**Q4. Comment éviter le faux positif chez un utilisateur nouveau?**  
La logique d'escalade a été explicitement durcie contre ce biais: en historique insuffisant, la pente hebdomadaire ne force pas un signal d'alerte artificiel. Ainsi, un nouvel utilisateur n'est pas classé en escalade par absence de semaine antérieure.

**Q5. Comment passe-t-on de ce prototype à un produit mature?**  
Le chemin est incrémental: endpoint AI exposé, intégration backend de bout en bout, collecte terrain anonymisée, recalibrage statistique, puis validation d'impact des recommandations. L'architecture actuelle est déjà modulaire pour absorber ces étapes sans réécriture complète.
