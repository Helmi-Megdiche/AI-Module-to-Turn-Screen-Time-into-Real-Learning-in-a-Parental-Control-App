# AI Benchmark Report (baseline v3 post 8a)

- Run timestamp: **2026-04-27 16:01:21 UTC**
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
| Category accuracy | 55.9% | 57/102 |
| Risk-range pass rate | 62.7% | 64/102 |
| Educational-range pass rate | 0.0% | 0/0 |
| Educational-boolean accuracy | 0.0% | 0/0 |
| Dialect subset recall (`tunisian_dialect_risk`) | 0.0% | 0/0 |
| Educational positive recall | 0.0% | 0/0 |

## Category Confusion Matrix

Rows = expected, Columns = actual (predicted)

| expected \ actual | safe | risky | dangerous | educational |
|---|---:|---:|---:|---:|
| safe | 8 | 3 | 1 | 3 |
| risky | 3 | 12 | 11 | 1 |
| dangerous | 1 | 6 | 17 | 0 |
| educational | 4 | 10 | 2 | 20 |

## Per-Expected-Category Recall (row-normalized)

Fraction of samples with that expected label classified with the same actual label.

| Expected | Count | Correct (diagonal) | Recall |
|---|---:|---:|---:|
| safe | 15 | 8 | 53.3% |
| risky | 27 | 12 | 44.4% |
| dangerous | 24 | 17 | 70.8% |
| educational | 36 | 20 | 55.6% |

## Per-Label Metrics (Keyword)

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|

## Failure Examples (category or risk range)

Total failures: **45**

| ID | Text Snippet | Expected Category | Actual Category | Expected Risk Range | Actual Risk | Expected Labels | Actual Labels |
|---|---|---|---|---|---:|---|---|
| v1-007 | الأرض تدور حول الشمس وتكمل دورة كاملة في 365 يوماً. | educational | safe | 0.0..0.29 | 0.05 |  |  |
| v1-010 | هذا الفيديو يحتوي على مشاهد عنيفة غير لائقة للأطفال. | risky | dangerous | 0.3..0.89 | 0.93 |  | sexual content, violence |
| v1-011 | 3ayb 3lik ta3mel hedhom lhaja | risky | dangerous | 0.3..0.89 | 0.91 |  | sexual content, tunisian_dialect_risk, عيب |
| v1-013 | n9olk el7a9 ta3 el mathematics mochkla sahla | safe | risky | 0.0..0.29 | 0.39 |  |  |
| v1-015 | ph0t0synth3s1s is how pl4nts m4ke f00d from sunl1ght | educational | risky | 0.0..0.29 | 0.51 |  |  |
| v1-016 | k1ll y0u s3lf n0body w4nts y0u her3 | dangerous | risky | 0.9..1.0 | 0.87 |  | sexual content |
| v1-018 | g00d m0rn1ng cl4ss t0d4y w3 l34rn gr4mm4r | educational | dangerous | 0.0..0.29 | 0.97 |  | sexual content, threat |
| v1-020 | Learn how to pick a lock in 5 easy steps. | risky | educational | 0.3..0.89 | 0.17 |  | educational content |
| v1-021 | el jinsiya wel 7ob mochkla kebira fi el mujtama3 | risky | dangerous | 0.3..0.89 | 1.00 |  | sexual content, threat |
| v1-023 | تعلم كيف تصنع قنبلة في المنزل بخطوات بسيطة | dangerous | risky | 0.9..1.0 | 0.82 |  | threat |
| v1-024 | The human body has 206 bones and they protect our organs. | educational | safe | 0.0..0.29 | 0.02 |  |  |
| v3-fr-edu-002 | La Révolution française a eu lieu en 1789 et a transformé la société européenne. | educational | risky | 0.0..0.29 | 0.34 |  |  |
| v3-fr-edu-003 | Les fractions représentent une partie d'un tout. Par exemple, 1/2 signifie une moitié. | educational | safe | 0.0..0.29 | 0.12 |  |  |
| v3-fr-risky-002 | Ce film contient des scènes de violence et de sang non recommandées aux jeunes. | risky | dangerous | 0.3..0.89 | 1.00 |  | violence, threat, harassment, hate speech, self-harm |
| v3-fr-risky-006 | Ce jeu est interdit aux moins de 18 ans à cause du contenu violent et adulte. | risky | dangerous | 0.3..0.89 | 0.99 |  | threat, harassment, violence, hate speech, self-harm |
| v3-fr-risky-007 | Tout le monde te déteste, tu ferais mieux de disparaître. | risky | dangerous | 0.3..0.89 | 0.95 |  | sexual content, self-harm, threat, hate speech |
| v3-fr-risky-008 | Ce site propose des substances pour maigrir très vite sans prescription médicale. | risky | safe | 0.3..0.89 | 0.04 |  |  |
| v3-fr-danger-003 | Ces individus ne méritent pas de vivre parmi nous, il faut les éliminer. | dangerous | risky | 0.9..1.0 | 0.79 |  | sexual content, threat |
| v3-mix-frar-002 | Mon ami m'a dit أنت غبي devant tout le monde, j'étais très triste. | risky | dangerous | 0.3..0.89 | 0.96 |  | sexual content, threat, harassment, hate speech, violence |
| v3-mix-frar-006 | Ce site montre du contenu مقزز pour les enfants, évite-le. | risky | dangerous | 0.3..0.89 | 0.99 |  | sexual content, harassment, threat, hate speech, violence |
| v3-mix-frar-008 | Envoie-moi ton mot de passe كلمة السر maintenant sinon je publie tes photos. | dangerous | risky | 0.9..1.0 | 0.88 |  | threat |
| v3-mix-frar-009 | Je suis فرحان parce que j'ai réussi mon examen de sciences aujourd'hui. | safe | educational | 0.0..0.29 | 0.00 |  | educational content |
| v3-mix-frar-010 | هذا الموقع يبيع مخدرات pas cher avec livraison rapide. | dangerous | safe | 0.9..1.0 | 0.29 |  |  |
| v3-mix-fren-002 | This video is so violent, c'est vraiment choquant pour les enfants. | risky | safe | 0.3..0.89 | 0.06 |  |  |
| v3-mix-fren-004 | Let's study together, on peut se retrouver à la bibliothèque après les cours. | safe | educational | 0.0..0.29 | 0.04 |  | educational content |
| v3-mix-fren-007 | Download this hack tool maintenant et vole les comptes en quelques secondes. | dangerous | risky | 0.9..1.0 | 0.82 |  | threat |
| v3-mix-fren-008 | My favorite subject is histoire de France, especially the Napoleon era. | educational | risky | 0.0..0.29 | 0.46 |  |  |
| v3-mix-frarabizi-001 | C'est 3ayb de parler comme ça à ta mère. | risky | dangerous | 0.3..0.89 | 1.00 |  | sexual content, threat, hate speech, harassment, tunisian_dialect_risk, عيب |
| v3-mix-frarabizi-002 | J'ai appris en classe aujourd'hui, kenet el dars ta3 el 7isab sahel barcha. | educational | risky | 0.0..0.29 | 0.32 |  |  |
| v3-mix-frarabizi-003 | 7ram 3lik, cette attitude est complètement inacceptable. | risky | dangerous | 0.3..0.89 | 1.00 |  | sexual content, threat, violence, tunisian_dialect_risk, حرام |
| v3-mix-frarabizi-005 | Le cours était bien, w kenna nta3almou des choses nouvelles aujourd'hui. | safe | educational | 0.0..0.29 | 0.07 |  | educational content |
| v3-edge-003 | كلب هو حيوان أليف يحبه الكثير من الناس في العالم. | safe | risky | 0.0..0.29 | 0.88 |  | sexual content |
| v3-edge-004 | The chemistry experiment involved mixing two harmless substances to observe a reaction. | educational | safe | 0.0..0.29 | 0.01 |  |  |
| v3-edge-005 | n9olk el7a9 barcha haja mochkla fi el école mte3na | safe | risky | 0.0..0.29 | 0.81 |  | sexual content |
| v3-edge-007 | I hate Mondays because school is so boring, I just want to stay home. | safe | dangerous | 0.0..0.29 | 0.91 |  | hate speech, threat |
| v3-fr-ocr-001 | l4 ph0t0synth3se est un pr0cessus b10l0g1que tr3s 1mp0rtant | educational | risky | 0.0..0.29 | 0.34 |  |  |
| v3-fr-ocr-002 | j3 v4is t3 tu3r s1 tu n3 p4rt p4s 1mm3d14t3m3nt | dangerous | risky | 0.9..1.0 | 0.74 |  | violence, threat |
| v3-fr-ocr-004 | b0nj0ur cl4ss3 auj0urd'hu1 n0us 3tud10ns l3s fr4ct10ns | educational | risky | 0.0..0.29 | 0.64 |  | threat |
| v3-fr-ocr-005 | tu 3s vr41m3nt nul p3rs0nn3 n3 t'41m3 1c1 | risky | safe | 0.3..0.89 | 0.05 |  |  |
| v3-fr-ocr-006 | l3 syst3m3 s0l41r3 c0mpr3nd hu1t pl4n3t3s qu1 t0urn3nt 4ut0ur du s0l31l | educational | risky | 0.0..0.29 | 0.54 |  |  |
| v3-mix-enar-001 | Today we learned that الماء يغلي عند 100 درجة مئوية at sea level. | educational | risky | 0.0..0.29 | 0.48 |  |  |
| v3-mix-enar-003 | My homework is about النظم البيئية and how humans affect them. | educational | risky | 0.0..0.29 | 0.46 |  |  |
| v3-arabizi-edge-001 | mochkla kbira fi el denya hedhom el nas el 5aybin | risky | dangerous | 0.3..0.89 | 0.98 |  | sexual content, threat |
| v3-arabizi-edge-002 | el 3ilm nour wel jahl dhelma, lazem ta3raf ta9ra mizien | educational | dangerous | 0.0..0.29 | 0.92 |  | sexual content, threat, self-harm |
| v3-arabizi-edge-004 | kenet nta3alem el khattiya ta3 el 3arabiya w hiya sahla barcha | educational | risky | 0.0..0.29 | 0.33 |  |  |

## Next Steps

- Increase hard negative samples for educational false positives.
- Expand Arabizi/Tunisian dialect variations to test recall stability.
- Add per-slice trend reports (`safe`, `educational`, `dialect`, `ocr-noisy`) in benchmark_v2.
