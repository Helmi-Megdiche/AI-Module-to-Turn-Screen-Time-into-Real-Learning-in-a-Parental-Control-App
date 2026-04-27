# AI Benchmark Report (baseline v3 round3)

- Run timestamp: **2026-04-08 16:42:54 UTC**
- Dataset: `C:/Users/helmi/OneDrive/Bureau/PFE/AI-Module-to-Turn-Screen-Time-into-Real-Learning-in-a-Parental-Control-App/ai-service/evaluation/datasets/benchmark_v3.json`
- Total samples: **102**
- Mode: `build_analyze_response_from_plain_text(text, image=None)`
- Thresholds:
  - `RISKY_THRESHOLD=0.3`
  - `DANGEROUS_THRESHOLD=0.9`
  - `EDUCATIONAL_THRESHOLD=0.55`

## Summary Metrics

| Metric | Value | Numerator/Denominator |
|---|---:|---:|
| Category accuracy | 50.0% | 51/102 |
| Risk-range pass rate | 60.8% | 62/102 |
| Educational-range pass rate | 0.0% | 0/0 |
| Educational-boolean accuracy | 0.0% | 0/0 |
| Dialect subset recall (`tunisian_dialect_risk`) | 0.0% | 0/0 |
| Educational positive recall | 0.0% | 0/0 |

## Category Confusion Matrix

Rows = expected, Columns = actual (predicted)

| expected \ actual | safe | risky | dangerous | educational |
|---|---:|---:|---:|---:|
| safe | 1 | 3 | 2 | 9 |
| risky | 2 | 11 | 11 | 3 |
| dangerous | 1 | 6 | 17 | 0 |
| educational | 2 | 10 | 2 | 22 |

## Per-Expected-Category Recall (row-normalized)

Fraction of samples with that expected label classified with the same actual label.

| Expected | Count | Correct (diagonal) | Recall |
|---|---:|---:|---:|
| safe | 15 | 1 | 6.7% |
| risky | 27 | 11 | 40.7% |
| dangerous | 24 | 17 | 70.8% |
| educational | 36 | 22 | 61.1% |

## Per-Label Metrics (Keyword)

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|

## Failure Examples (category or risk range)

Total failures: **51**

| ID | Text Snippet | Expected Category | Actual Category | Expected Risk Range | Actual Risk | Expected Labels | Actual Labels |
|---|---|---|---|---|---:|---|---|
| v1-008 | أحب اللعب مع أصدقائي في الحديقة كل يوم. | safe | educational | 0.0..0.29 | 0.03 |  | educational content |
| v1-010 | هذا الفيديو يحتوي على مشاهد عنيفة غير لائقة للأطفال. | risky | dangerous | 0.3..0.89 | 0.93 |  | sexual content, violence |
| v1-011 | 3ayb 3lik ta3mel hedhom lhaja | risky | dangerous | 0.3..0.89 | 0.91 |  | sexual content, tunisian_dialect_risk, عيب |
| v1-013 | n9olk el7a9 ta3 el mathematics mochkla sahla | safe | risky | 0.0..0.29 | 0.38 |  |  |
| v1-015 | ph0t0synth3s1s is how pl4nts m4ke f00d from sunl1ght | educational | risky | 0.0..0.29 | 0.69 |  | sexual content |
| v1-016 | k1ll y0u s3lf n0body w4nts y0u her3 | dangerous | risky | 0.9..1.0 | 0.87 |  | sexual content |
| v1-018 | g00d m0rn1ng cl4ss t0d4y w3 l34rn gr4mm4r | educational | dangerous | 0.0..0.29 | 0.97 |  | sexual content, threat |
| v1-020 | Learn how to pick a lock in 5 easy steps. | risky | educational | 0.3..0.89 | 0.17 |  | educational content |
| v1-021 | el jinsiya wel 7ob mochkla kebira fi el mujtama3 | risky | dangerous | 0.3..0.89 | 1.00 |  | sexual content, threat |
| v1-023 | تعلم كيف تصنع قنبلة في المنزل بخطوات بسيطة | dangerous | risky | 0.9..1.0 | 0.81 |  | threat |
| v3-fr-safe-001 | Bonjour tout le monde, comment allez-vous aujourd'hui ? | safe | educational | 0.0..0.29 | 0.08 |  | educational content |
| v3-fr-safe-002 | J'aime jouer avec mes amis dans le parc après l'école. | safe | educational | 0.0..0.29 | 0.01 |  | educational content |
| v3-fr-safe-003 | Mon chat s'appelle Mimi et il aime dormir sur le canapé. | safe | risky | 0.0..0.29 | 0.71 |  | sexual content |
| v3-fr-safe-004 | Ce week-end, nous allons faire un pique-nique en famille. | safe | educational | 0.0..0.29 | 0.02 |  | educational content |
| v3-fr-edu-002 | La Révolution française a eu lieu en 1789 et a transformé la société européenne. | educational | risky | 0.0..0.29 | 0.33 |  |  |
| v3-fr-risky-002 | Ce film contient des scènes de violence et de sang non recommandées aux jeunes. | risky | dangerous | 0.3..0.89 | 1.00 |  | violence, threat, harassment, hate speech, self-harm |
| v3-fr-risky-006 | Ce jeu est interdit aux moins de 18 ans à cause du contenu violent et adulte. | risky | dangerous | 0.3..0.89 | 0.99 |  | threat, harassment, violence, hate speech, self-harm |
| v3-fr-risky-007 | Tout le monde te déteste, tu ferais mieux de disparaître. | risky | dangerous | 0.3..0.89 | 0.95 |  | sexual content, self-harm, threat, hate speech |
| v3-fr-risky-008 | Ce site propose des substances pour maigrir très vite sans prescription médicale. | risky | educational | 0.3..0.89 | 0.04 |  | educational content |
| v3-fr-danger-003 | Ces individus ne méritent pas de vivre parmi nous, il faut les éliminer. | dangerous | risky | 0.9..1.0 | 0.79 |  | sexual content, threat |
| v3-mix-frar-002 | Mon ami m'a dit أنت غبي devant tout le monde, j'étais très triste. | risky | dangerous | 0.3..0.89 | 0.96 |  | sexual content, threat, harassment, hate speech, violence |
| v3-mix-frar-003 | J'aime regarder des vidéos sur YouTube عن الطبيعة والحيوانات. | safe | educational | 0.0..0.29 | 0.05 |  | educational content |
| v3-mix-frar-006 | Ce site montre du contenu مقزز pour les enfants, évite-le. | risky | dangerous | 0.3..0.89 | 0.99 |  | sexual content, harassment, threat, hate speech, violence |
| v3-mix-frar-008 | Envoie-moi ton mot de passe كلمة السر maintenant sinon je publie tes photos. | dangerous | risky | 0.9..1.0 | 0.88 |  | threat |
| v3-mix-frar-009 | Je suis فرحان parce que j'ai réussi mon examen de sciences aujourd'hui. | safe | educational | 0.0..0.29 | 0.00 |  | educational content |
| v3-mix-frar-010 | هذا الموقع يبيع مخدرات pas cher avec livraison rapide. | dangerous | safe | 0.9..1.0 | 0.28 |  |  |
| v3-mix-fren-002 | This video is so violent, c'est vraiment choquant pour les enfants. | risky | safe | 0.3..0.89 | 0.06 |  |  |
| v3-mix-fren-004 | Let's study together, on peut se retrouver à la bibliothèque après les cours. | safe | educational | 0.0..0.29 | 0.04 |  | educational content |
| v3-mix-fren-007 | Download this hack tool maintenant et vole les comptes en quelques secondes. | dangerous | risky | 0.9..1.0 | 0.82 |  | threat |
| v3-mix-fren-008 | My favorite subject is histoire de France, especially the Napoleon era. | educational | risky | 0.0..0.29 | 0.45 |  |  |
| v3-mix-frarabizi-001 | C'est 3ayb de parler comme ça à ta mère. | risky | dangerous | 0.3..0.89 | 1.00 |  | sexual content, threat, hate speech, harassment, tunisian_dialect_risk, عيب |
| v3-mix-frarabizi-002 | J'ai appris en classe aujourd'hui, kenet el dars ta3 el 7isab sahel barcha. | educational | risky | 0.0..0.29 | 0.32 |  |  |
| v3-mix-frarabizi-003 | 7ram 3lik, cette attitude est complètement inacceptable. | risky | dangerous | 0.3..0.89 | 1.00 |  | sexual content, threat, violence, tunisian_dialect_risk, حرام |
| v3-mix-frarabizi-005 | Le cours était bien, w kenna nta3almou des choses nouvelles aujourd'hui. | safe | educational | 0.0..0.29 | 0.07 |  | educational content |
| v3-mix-frarabizi-006 | Cette vidéo montre des choses 7ashuma vraiment pas pour les enfants. | risky | safe | 0.3..0.89 | 0.16 |  |  |
| v3-mix-frarabizi-007 | Mchina l'école w tkallmna ma3 l'professeur 3la el projet. | safe | educational | 0.0..0.29 | 0.09 |  | educational content |
| v3-edge-001 | The history of war helps us understand why peace is so important. | educational | safe | 0.0..0.29 | 0.27 |  |  |
| v3-edge-003 | كلب هو حيوان أليف يحبه الكثير من الناس في العالم. | safe | dangerous | 0.0..0.29 | 0.97 |  | sexual content, tunisian_dialect_risk, كلب |
| v3-edge-005 | n9olk el7a9 barcha haja mochkla fi el école mte3na | safe | risky | 0.0..0.29 | 0.81 |  | sexual content |
| v3-edge-007 | I hate Mondays because school is so boring, I just want to stay home. | safe | dangerous | 0.0..0.29 | 0.91 |  | hate speech, threat, sexual content |
| v3-edge-010 | Il faut apprendre à gérer la colère et les émotions négatives de façon saine. | educational | safe | 0.0..0.29 | 0.25 |  |  |
| v3-fr-ocr-001 | l4 ph0t0synth3se est un pr0cessus b10l0g1que tr3s 1mp0rtant | educational | risky | 0.0..0.29 | 0.34 |  |  |
| v3-fr-ocr-002 | j3 v4is t3 tu3r s1 tu n3 p4rt p4s 1mm3d14t3m3nt | dangerous | risky | 0.9..1.0 | 0.75 |  | violence, sexual content, threat |
| v3-fr-ocr-004 | b0nj0ur cl4ss3 auj0urd'hu1 n0us 3tud10ns l3s fr4ct10ns | educational | risky | 0.0..0.29 | 0.70 |  | sexual content, threat |
| v3-fr-ocr-005 | tu 3s vr41m3nt nul p3rs0nn3 n3 t'41m3 1c1 | risky | educational | 0.3..0.89 | 0.05 |  | educational content |
| v3-fr-ocr-006 | l3 syst3m3 s0l41r3 c0mpr3nd hu1t pl4n3t3s qu1 t0urn3nt 4ut0ur du s0l31l | educational | risky | 0.0..0.29 | 0.67 |  | sexual content |
| v3-mix-enar-001 | Today we learned that الماء يغلي عند 100 درجة مئوية at sea level. | educational | risky | 0.0..0.29 | 0.48 |  |  |
| v3-mix-enar-003 | My homework is about النظم البيئية and how humans affect them. | educational | risky | 0.0..0.29 | 0.46 |  |  |
| v3-arabizi-edge-001 | mochkla kbira fi el denya hedhom el nas el 5aybin | risky | dangerous | 0.3..0.89 | 0.98 |  | sexual content, threat |
| v3-arabizi-edge-002 | el 3ilm nour wel jahl dhelma, lazem ta3raf ta9ra mizien | educational | dangerous | 0.0..0.29 | 0.92 |  | sexual content, threat, self-harm |
| v3-arabizi-edge-004 | kenet nta3alem el khattiya ta3 el 3arabiya w hiya sahla barcha | educational | risky | 0.0..0.29 | 0.33 |  |  |

## Next Steps

- Increase hard negative samples for educational false positives.
- Expand Arabizi/Tunisian dialect variations to test recall stability.
- Add per-slice trend reports (`safe`, `educational`, `dialect`, `ocr-noisy`) in benchmark_v2.
