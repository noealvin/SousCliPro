# Tutoriel complet — SousClientPro (Sujet 4)
### Objectif : 20/20 sur la grille de notation du TP

Ce tutoriel suit exactement les 7 critères de la grille de notation (page 6 du sujet). Coche chaque section au fur et à mesure.

---

## Connexion à l'application

L'application démarre sur une page de connexion (`/login`).
- Identifiant : `admin`
- Mot de passe : `admin123`

Modifiable dans `.env` via `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

---

## 0. Prérequis

- Docker Desktop installé et lancé (inclut Docker Compose).
- Git installé, compte GitHub créé.
- Aucune installation de Python/PostgreSQL nécessaire : tout tourne dans Docker.

```bash
git --version
docker --version
docker compose version
```

---

## Critère 1 — Git & collaboration (3 pts) : branches, PR, commits répartis

**Exigé** : aucun commit direct sur `main`, au moins 3 commits par membre, modèle branche → pull request → fusion.

```bash
cd projet4-souscription
git init
git add .
git commit -m "chore: squelette initial du projet SousClientPro"
git branch -M main
git remote add origin https://github.com/<ton-utilisateur>/<nom-du-repo>.git
git push -u origin main
```

Ensuite, **chaque membre** du groupe travaille sur sa propre branche, jamais directement sur `main` :

```bash
git checkout -b feature/nom-de-la-tache
# ... modifications ...
git add .
git commit -m "feat: description claire de la modification"
git push -u origin feature/nom-de-la-tache
```

Ouvre une **Pull Request** sur GitHub (`feature/... → main`), fais-la relire par un autre membre, puis clique sur **Merge**. Répète pour que chaque membre du groupe ait au moins 3 commits distincts. Le professeur vérifiera avec :

```bash
git log --author="Nom du membre" --oneline
```

Répartition suggérée (à adapter) :
- Membre 1 : backend Flask (`app/app.py`)
- Membre 2 : frontend (`app/templates/`)
- Membre 3 : tests + CI (`tests/`, `.github/workflows/`)
- Membre 4 : Docker + Nginx + README

---

## Critère 2 — API REST & données (3 pts) : endpoints CRUD, persistance PostgreSQL

**Rien à modifier** — déjà fourni et fonctionnel :

| Méthode | Route                       | Action CRUD |
|---------|------------------------------|-------------|
| POST    | `/api/souscriptions`         | Create      |
| GET     | `/api/souscriptions`         | Read (liste)|
| GET     | `/api/souscriptions/<id>`    | Read (un)   |
| PUT     | `/api/souscriptions/<id>`    | Update      |
| DELETE  | `/api/souscriptions/<id>`    | Delete      |

Démarre l'application :

```bash
cp .env.example .env
docker compose up --build
```

Attends le log `[startup] Connexion PostgreSQL etablie`, puis ouvre **http://localhost**, connecte-toi, et utilise l'interface : formulaire à gauche (Create/Update), tableau à droite avec boutons **Modifier** et **Supprimer** sur chaque ligne (Update/Delete).

Vérifie la persistance réelle en PostgreSQL (pas de stockage mémoire) :

```bash
docker exec -it souscription_db psql -U postgres -d souscription_produit -c "\dt"
docker exec -it souscription_db psql -U postgres -d souscription_produit -c "SELECT * FROM souscriptions;"
```

Teste chaque action CRUD en ligne de commande :

```bash
# Create
curl -X POST http://localhost/api/souscriptions -H "Content-Type: application/json" \
  -d '{"code_client":"12345678","nom_client":"Jean Dupont","produit":"LIVRET_EPARGNE","date_souscription":"2026-01-15"}'

# Read (liste)
curl http://localhost/api/souscriptions

# Update (remplace 1 par l'id retourné à l'étape Create)
curl -X PUT http://localhost/api/souscriptions/1 -H "Content-Type: application/json" \
  -d '{"code_client":"12345678","nom_client":"Jean Dupont","produit":"ASSURANCE_VIE","date_souscription":"2026-01-15"}'

# Delete
curl -X DELETE http://localhost/api/souscriptions/1
```

Note : ces appels curl échoueront avec `401` si tu n'es pas connecté dans le même client HTTP — pour tester en curl, connecte-toi d'abord et réutilise le cookie de session :

```bash
curl -c cookies.txt -X POST http://localhost/api/login -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
curl -b cookies.txt http://localhost/api/souscriptions
```

---

## Critère 3 — Validation métier & tests (4 pts)

Règles implémentées dans `app/app.py` (fonction `valider_souscription`) :
- Code client obligatoire, exactement 8 chiffres.
- Nom du client obligatoire.
- Produit souscrit dans un catalogue fermé.
- Date de souscription obligatoire, non future.
- Unicité code_client + produit.

17 tests pytest couvrent chaque règle (`tests/test_app.py`). Exécute-les en local :

```bash
cd app
pip install -r requirements.txt
pip install pytest pytest-cov flake8
cd ..
pytest --cov=app tests/
```

Tous les tests doivent passer en vert et la couverture s'afficher.

---

## Critère 4 — Conteneurisation (4 pts) : Dockerfile, docker-compose (api + db + nginx)

**Rien à modifier.** `docker compose up --build` démarre les 3 services :
- `db` — PostgreSQL 15, volume persistant, healthcheck `pg_isready`.
- `api` — Flask/gunicorn, attend `db` en `service_healthy`.
- `nginx` — reverse proxy, seul service exposé publiquement (port 80).

Vérifie que l'API n'est **jamais** accessible directement (exigence de l'énoncé) :

```bash
curl http://localhost:5000   # doit échouer : ce port n'est pas publié
curl http://localhost        # doit répondre : tout passe par Nginx
```

Bonus possible (2 pts hors barème) : passer l'API en 2 réplicas. Dans `docker-compose.yml`, remplace le service `api` par une configuration avec `deploy: replicas: 2` (nécessite `docker compose up --scale api=2` en pratique avec Compose classique) et laisse Nginx faire le round-robin — mentionne cette tentative dans le README si tu la fais.

---

## Critère 5 — Pipeline CI (3 pts) : GitHub Actions, lint + tests + build

Le fichier `.github/workflows/ci.yml` s'exécute automatiquement sur `push` et `pull_request` (`main`, `develop`) :
1. **lint** — `flake8 app tests --max-line-length=120`
2. **test** — `pytest --cov=app tests/` (SQLite en mémoire, pas de PostgreSQL nécessaire dans le runner)
3. **docker-build** — build de l'image API et de l'image Nginx

Après ton premier `git push`, va dans l'onglet **Actions** de ton dépôt GitHub et vérifie que les 3 jobs passent au vert. **Prends une capture d'écran de ce statut vert — c'est un livrable exigé** (voir Critère 7).

Si un job échoue :
```bash
flake8 app tests --max-line-length=120   # reproduit l'erreur de lint en local
pytest --cov=app tests/                   # reproduit l'erreur de test en local
docker build -t test-image .              # reproduit l'erreur de build en local
```
Corrige, commit, repush.

---

## Critère 6 — Sécurité (2 pts) : secrets hors du code

Déjà en place :
- `.env` contient tous les secrets (mots de passe BDD, `SECRET_KEY`, identifiants admin) et est exclu du dépôt par `.gitignore`.
- `.env.example` (sans valeurs sensibles réelles) est versionné à sa place.
- Aucun mot de passe en dur dans `app/app.py`, `docker-compose.yml` ou `ci.yml` — tout passe par variables d'environnement.

**Avant de push sur GitHub**, vérifie que `.env` n'est jamais suivi par Git :

```bash
git status   # .env ne doit PAS apparaître dans "Changes to be committed"
```

Si le pipeline CI a besoin d'un secret un jour (ex. déploiement), utilise **GitHub Secrets** (Settings → Secrets and variables → Actions) — jamais une valeur en clair dans `ci.yml`.

Bonus possible : ajoute un scan de vulnérabilités avec `bandit` (code) ou `trivy` (image) comme job supplémentaire dans `ci.yml`.

---

## Critère 7 — Documentation (1 pt) : README complet

`README.md` contient déjà : description du sujet, schéma d'architecture ASCII, instructions de lancement en une commande, liste des règles de validation, et une liste de membres factices — **remplace cette liste par les vrais noms de ton groupe et leur répartition des tâches** avant de rendre.

### Livrables finaux à réunir avant la remise

1. Lien du dépôt GitHub (public, ou accès donné à l'enseignant).
2. `README.md` à jour (vrais membres + répartition des tâches).
3. Capture d'écran du pipeline GitHub Actions au vert.
4. Vérifier que `docker compose up --build` fonctionne bien en partant d'un clone propre du dépôt (teste-le avant de rendre) :

```bash
git clone https://github.com/<ton-utilisateur>/<nom-du-repo>.git test-clone
cd test-clone
cp .env.example .env
docker compose up --build
```

Si cette dernière étape fonctionne sans erreur, ton rendu est complet.

---

## Récapitulatif des seules lignes à modifier si besoin

| Besoin | Fichier | Ligne à changer |
|---|---|---|
| Changer les identifiants de connexion | `.env` | `ADMIN_USERNAME=` / `ADMIN_PASSWORD=` |
| Changer le mot de passe BDD | `.env` | `POSTGRES_PASSWORD=` |
| Ajouter/retirer un produit du catalogue | `app/app.py` puis `app/templates/index.html` | `PRODUITS_VALIDES = [...]` et les `<option>` du `<select id="produit">` + `PRODUITS_LABELS` en JS |
| Changer le format du code client | `app/app.py` | `CODE_CLIENT_REGEX = re.compile(...)` |
| Changer le port public exposé | `docker-compose.yml` | `ports: - "80:80"` (service `nginx`) |
| Mettre à jour les membres du groupe | `README.md` | section "Équipe" |
