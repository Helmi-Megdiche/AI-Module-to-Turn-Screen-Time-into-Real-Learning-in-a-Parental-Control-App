# Rapport complet du projet

## Titre du projet

AI Module to Turn Screen Time into Real Learning in a Parental Control App

## 1. Contexte general

Ce projet a pour objectif de transformer le temps d'ecran de l'enfant en opportunites d'apprentissage reel, tout en renforcant le role des parents dans le suivi, la prevention et l'accompagnement. L'idee centrale est d'observer ce qui apparait sur l'ecran, d'analyser automatiquement le contenu, de detecter les risques ou les contenus inappropries, puis de generer une reponse educative adaptee plutot qu'une simple punition ou un simple blocage.

Le projet combine donc plusieurs dimensions :

- analyse intelligente du contenu affiche
- detection automatique des situations a risque
- generation de missions educatives
- gamification pour motiver l'enfant
- tableau de bord pour les parents

## 2. Objectifs specifiques

Les objectifs specifiques du projet sont les suivants :

- Analyser le contenu affiche sur l'ecran a l'aide de techniques d'OCR et de vision par ordinateur.
- Detecter automatiquement les contenus potentiellement dangereux ou inappropries.
- Generer des missions educatives et des activites reelles adaptees a l'age et aux interets de l'enfant.
- Mettre en place un systeme de gamification pour encourager la participation.
- Fournir aux parents des outils de suivi et de gestion des recompenses dans la vie reelle.

## 3. Architecture actuelle du projet

Le projet est actuellement structure en trois blocs principaux.

### 3.1 Backend Node.js / Express

Le backend joue le role d'orchestrateur principal.

Responsabilites actuelles :

- recevoir les requetes du front/demo
- communiquer avec le service IA
- enregistrer les analyses dans la base
- generer et stocker les missions
- exposer les routes de suivi pour les parents

Principales routes deja en place :

- `POST /api/analyze`
- `GET /api/user/:id/summary`
- `GET /api/user/:id/history`
- `GET /api/user/:id/missions`
- `GET /api/health`

Ameliorations deja realisees :

- augmentation de la limite JSON Express a `15mb` pour supporter les captures encodees en base64
- pagination sur l'historique et les missions
- calcul du resume parent avec score moyen de risque et nombre de contenus dangereux
- persistance des champs d'explicabilite comme `displayText` et `matchedKeywords`

### 3.2 AI service Python / FastAPI

Le service IA traite l'image et produit l'analyse textuelle et le niveau de risque.

Pipeline actuel :

1. reception de l'image en base64
2. conversion base64 vers image PIL
3. extraction de texte via OCR avec EasyOCR
4. analyse locale du texte via `risk_scoring.py`
5. calcul d'un `riskScore`, d'une `category` et d'une explication exploitable

Ce service expose actuellement :

- `POST /analyze`
- `GET /health`

### 3.3 Demo web

Une interface demo HTML simple existe pour tester rapidement le systeme.

Fonctions deja presentes :

- envoi d'une image pour analyse
- affichage du score de risque et de la categorie
- affichage du texte OCR et de l'explicabilite
- affichage du resume parent
- affichage de l'historique et des missions

Ameliorations UI deja faites :

- etats de chargement
- temps ecoule pendant l'analyse
- meilleurs boutons et feedback visuel
- affichage du `Average risk` en pourcentage

## 4. Base de donnees et persistance

Le projet utilise Prisma pour la partie backend.

Informations actuellement persistees :

- utilisateur
- analyses
- missions
- points / gamification
- texte OCR
- texte d'affichage pour le parent
- mots/etiquettes detectes

La logique actuelle permet deja de construire une vraie trace parentale :

- ce que l'enfant a vu
- quand cela a ete vu
- quel niveau de risque a ete calcule
- quelle mission a ete proposee

## 5. Etat actuel de la detection

La detection actuelle repose sur une logique locale dans `ai-service/app/services/risk_scoring.py`.

Cette logique n'est plus une simple liste de 7 ou 10 mots. Elle a deja ete amelioree avec :

- signaux contextuels
- ponderation par type de risque
- phrases critiques pour self-harm, violence, overdose, etc.
- tolerance a certaines erreurs OCR
- conversion vers un `riskScore` borne et une categorie finale

Exemples de signaux pris en compte :

- self-harm
- violent threat
- weapon
- dangerous challenge
- dangerous jump
- dangerous fire
- poison or overdose
- toxic abuse

## 6. Probleme principal identifie

Malgre les ameliorations, la logique actuelle reste essentiellement une logique de regles manuelles. Cela pose plusieurs limites importantes.

### 6.1 Limites des regles manuelles

- elles sont difficiles a maintenir a grande echelle
- elles ne generalisent pas bien a des formulations nouvelles
- elles dependent fortement des mots choisis par le developpeur
- elles sont fragiles face au bruit OCR
- elles ne comprennent pas vraiment le contexte semantique

### 6.2 Exemple concret deja observe

Une image liee au self-harm a ete analysee. L'OCR a produit un texte degrade de type :

`anxietyo tentlona amc feeling voida self-harmj risk Guin anxious deliberate damagc Jttemd To`

Le systeme l'a d'abord classe a tort comme `safe`, car :

- le texte etait deforme
- le modele etait encore trop dependante de motifs explicites

Ce cas montre clairement que la detection ne doit pas reposer uniquement sur une logique de mots cibles.

## 7. Tentative OpenAI et conclusion

Une integration OpenAI Moderation API a ete essayee comme solution rapide et production-like.

Ce qui a ete verifie :

- la cle API etait lue correctement
- le projet pouvait lister les modeles OpenAI
- l'integration etait techniquement en place

Mais les requetes reelles vers les endpoints OpenAI retournaient des erreurs de quota :

- `429 Too Many Requests`
- `insufficient_quota`

Conclusion :

- le probleme n'etait pas le code
- le probleme n'etait pas le format de la cle
- le probleme venait des quotas/billing du projet OpenAI

Cette methode a donc ete retiree du code pour ne pas garder une dependance externe non fiable dans l'etat actuel du projet.

## 8. Decision actuelle

La decision actuelle est de ne pas utiliser OpenAI dans la version courante du projet.

Le code est revenu a une logique locale uniquement.

Cela signifie :

- pas de dependance a une API payante
- pas de probleme de quota
- pas d'exposition du projet a une instabilite externe
- mais une detection encore insuffisante sur le plan semantique

## 9. Meilleure direction proposee

La meilleure direction pour le projet est d'utiliser un modele NLP local pre-entraine et fine-tune pour la moderation, charge directement dans le service Python.

Autrement dit :

- garder OCR
- remplacer la logique regle-first par un modele de classification locale
- conserver un petit fallback base sur les regles pour les cas OCR bruyants

## 10. Pourquoi un modele pre-entraine de type BERT

Un modele de type BERT est une bonne piste, mais il faut faire une precision importante :

### 10.1 Ce qu'il ne faut pas faire

Il ne faut pas utiliser un BERT brut, non fine-tune, en esperant qu'il detecte tout seul :

- self-harm
- violence
- hate
- harassment

Un BERT brut produit des representations linguistiques, mais pas une moderation fiable sans apprentissage specialise.

### 10.2 Ce qu'il faut faire

Il faut utiliser un modele BERT-family deja fine-tune pour la moderation ou la classification de contenu sensible.

Exemples de familles de modeles adaptees :

- BERT fine-tune moderation
- DistilBERT
- MiniLM
- DeBERTa

Le plus important n'est pas le nom "BERT" seul, mais le fait que le modele soit deja entraine pour reconnaitre :

- self-harm
- violence
- hate speech
- harassment
- toxicity
- contenu inapproprie

## 11. Pourquoi cette solution est meilleure pour ce projet

Cette solution est bien plus alignee avec les objectifs du projet.

### 11.1 Pour la detection automatique

Un modele de moderation local comprend mieux :

- le contexte
- les formulations implicites
- les variantes linguistiques
- certaines paraphrases

Il est donc plus robuste qu'une simple liste de mots.

### 11.2 Pour la fiabilite du systeme

Le projet a besoin d'une detection plus solide car cette detection alimente ensuite :

- les missions educatives
- le suivi parent
- la gamification
- la categorisation du risque

Si la detection de base est faible, tout le reste perd en pertinence.

### 11.3 Pour l'autonomie technique

Une solution locale offre :

- pas de dependance a un fournisseur externe
- pas de cout variable par requete
- pas de probleme de quota
- plus de controle sur le pipeline

## 12. Limites d'un modele BERT local

Il faut aussi rester realiste sur ses limites.

Un modele texte local ne resout pas tout :

- il depend encore de la qualite OCR
- il ne comprend pas parfaitement les images sans texte
- il peut etre plus lent que des regles simples
- il necessite une integration et un calibrage des seuils

Donc BERT ne remplace pas toute l'intelligence du projet. Il ameliore surtout la couche de detection textuelle apres OCR.

## 13. Architecture recommandee pour la suite

Architecture recommandee :

```text
Image ecran
  -> OCR (EasyOCR)
  -> modele local de moderation NLP
  -> scores par type de risque
  -> conversion en riskScore / category
  -> generation mission / gamification / suivi parent
  -> fallback regles OCR si besoin
```

## 14. Proposition technique concrete

La proposition technique la plus pertinente est la suivante :

1. Ajouter `transformers` dans `ai-service`
2. Creer un nouveau `moderation_service.py`
3. Charger un modele de moderation local via Hugging Face pipeline
4. Retourner des labels du type :
   - self-harm
   - violence
   - hate
   - harassment
5. Convertir ces scores vers le schema deja existant :
   - `matchedKeywords`
   - `riskScore`
   - `category`
6. Conserver `build_display_text()` et un fallback OCR tolerant dans `risk_scoring.py`

## 15. Comparaison entre l'approche actuelle et l'approche recommandee

### Approche actuelle

Avantages :

- simple
- rapide
- facile a comprendre
- totalement locale

Inconvenients :

- trop dependante de regles manuelles
- fragile face aux variantes linguistiques
- fragile face aux erreurs OCR
- difficile a faire evoluer proprement

### Approche recommandee avec modele local fine-tune

Avantages :

- bien meilleure comprehension contextuelle
- plus robuste aux formulations variees
- meilleure base pour un vrai systeme intelligent
- compatible avec les objectifs academiques du projet

Inconvenients :

- integration un peu plus complexe
- inference potentiellement plus lente sur CPU
- necessite du tuning et de l'evaluation

## 16. Impact attendu sur le projet

Si cette evolution est implemente correctement, on peut s'attendre a :

- une meilleure detection des contenus sensibles
- moins de faux negatifs sur les cas dangereux
- moins de dependance a des listes de mots
- des missions educatives plus coherentes
- un suivi parental plus credible
- une architecture plus defendable dans un contexte de PFE

## 17. Recommandation finale

Pour ce projet, la meilleure suite n'est pas :

- d'ajouter encore plus de mots manuellement
- ni de dependre d'une API externe payante

La meilleure suite est :

- conserver OCR
- integrer un modele local NLP fine-tune pour moderation
- garder les regles actuelles comme couche secondaire de secours

## 18. Section speciale a donner a ChatGPT

Tu peux donner la partie suivante a ChatGPT si tu veux lui demander une aide technique ou une refonte propre :

### Prompt recommande

J'ai un projet de controle parental intelligent compose d'un backend Node.js/Express, d'un service IA Python/FastAPI et d'une demo web. Le service IA recoit une capture d'ecran en base64, applique EasyOCR, puis analyse le texte pour detecter des contenus dangereux ou inappropries. Actuellement, la detection repose sur une logique locale basee sur des regles dans `risk_scoring.py`, avec des signaux comme self-harm, violence, menace, challenge dangereux, toxicite et overdose. Cette logique a deja ete amelioree, mais elle reste trop dependante de regles manuelles et ne generalise pas assez bien aux formulations nouvelles ou aux erreurs OCR.

Je veux remplacer cette logique par une approche plus robuste basee sur un modele local de moderation NLP. Je ne veux pas utiliser d'API externe. Je veux une solution locale dans `ai-service`, idealement avec `transformers` et un modele BERT-family ou equivalent deja fine-tune pour des categories comme self-harm, violence, hate, harassment et toxicite.

Le systeme doit conserver le contrat actuel de l'API :

- `text`
- `displayText`
- `matchedKeywords`
- `riskScore`
- `category`

Je veux une architecture propre ou :

- OCR reste present
- un `moderation_service.py` local utilise un modele Hugging Face
- les scores du modele sont convertis vers `riskScore` et `category`
- `risk_scoring.py` devient un fallback leger pour les erreurs OCR et l'explicabilite

Propose-moi une implementation detaillee, pragmatique, CPU-friendly, bien adaptee a un PFE, avec :

- choix du modele
- structure des fichiers
- code Python
- mapping des scores
- gestion des erreurs
- recommandations de tests
- compromis precision / vitesse

## 19. Nouvelles idees a ajouter en bas du rapport

### Idee 1 : utiliser un modele BERT-family fine-tune au lieu de regles manuelles

Ce n'est pas "BERT ou `transformers`". La bonne solution est :

- un modele BERT-family fine-tune
- charge localement via `transformers`

### Idee 2 : garder un fallback OCR-tolerant

Meme avec un modele fort, le fallback local reste utile pour :

- corriger certaines deformations OCR
- produire une explication simple
- eviter qu'une panne du modele casse toute l'analyse

### Idee 3 : separer clairement detection et mission

La detection de contenu et la generation de mission ne doivent pas etre confondues.

Pipeline recommande :

- module 1 : OCR
- module 2 : moderation / scoring
- module 3 : generation de mission educative
- module 4 : gamification et suivi parent

### Idee 4 : utiliser un modele CPU-friendly pour commencer

Pour une integration simple dans un PFE :

- commencer avec DistilBERT ou MiniLM
- evaluer ensuite une version plus forte si besoin

### Idee 5 : evaluer le systeme sur des cas reels du projet

Il faut construire un petit jeu de test maison avec :

- captures d'ecran dangereuses
- contenus ambigus
- contenus normaux
- sorties OCR degradees

Cela permettra de mesurer :

- faux positifs
- faux negatifs
- robustesse OCR
- qualite des missions generees ensuite
