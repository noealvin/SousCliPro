# SousClientPro — Souscription Produit Client (Sujet 4)

Application DevOps clé en main : gestion CRUD complète des souscriptions produit (créer, lister, modifier, supprimer), persistance PostgreSQL, reverse proxy Nginx, pipeline CI/CD Actions.

## Architecture

```
                        ┌────────────────────┐
   Navigateur  ───────► │  Nginx (port 80)   │   reverse proxy + en-têtes de sécurité
                        └─────────┬──────────┘
                                  │ http://api:5000
                                  ▼
                        ┌────────────────────┐
                        │  Flask API (5000)  │   validation métier, gunicorn, CRUD
                        └─────────┬──────────┘
                                  │ psycopg2 :5432
                                  ▼
                        ┌────────────────────┐
                        │ PostgreSQL (5432)  │   table `souscriptions`
                        └────────────────────┘

Réseaux Docker :
  frontend (nginx <-> api)         backend (api <-> db, interne, non exposé)
```

## Règles métier (Sujet 4)

- **Code client** : obligatoire, exactement 8 chiffres.
- **Nom du client** : obligatoire.
- **Produit souscrit** : doit appartenir au catalogue fermé (`LIVRET_EPARGNE`, `ASSURANCE_VIE`, `CREDIT_CONSOMMATION`, `COMPTE_COURANT`, `CARTE_PREMIUM`).
- **Date de souscription** : obligatoire, ne peut pas être dans le futur.
- **Unicité** : un même client (code_client) ne peut pas souscrire deux fois au même produit.

## Endpoints CRUD de l'API

| Méthode | Route                     | Description                           |
| ------- | ------------------------- | ------------------------------------- |
| GET     | `/`                       | Sert l'interface web                  |
| POST    | `/api/souscriptions`      | Crée une souscription (Create)        |
| GET     | `/api/souscriptions`      | Liste toutes les souscriptions (Read) |
| GET     | `/api/souscriptions/<id>` | Récupère une souscription (Read)      |
| PUT     | `/api/souscriptions/<id>` | Modifie une souscription (Update)     |
| DELETE  | `/api/souscriptions/<id>` | Supprime une souscription (Delete)    |
| GET     | `/health`                 | État de santé du backend et de la BDD |

## Authentification

L'interface est protégée par une page de connexion. Identifiants par défaut (modifiables dans `.env`) :

- Identifiant : `admin`
- Mot de passe : `admin123`

## Démarrage en local

```bash
cp .env.example .env
docker compose up --build
```

Application accessible sur **http://localhost** — redirige vers `/login`.

Pour arrêter : `docker compose down`. Pour repartir d'une base vide : `docker compose down -v`.

## Tester le CRUD via curl

```bash
# Create
curl -X POST http://localhost/api/souscriptions -H "Content-Type: application/json" \
  -d '{"code_client":"12345678","nom_client":"Jean Dupont","produit":"LIVRET_EPARGNE","date_souscription":"2026-01-15"}'

# Read (liste)
curl http://localhost/api/souscriptions

# Update (remplacer 1 par l'id retourné)
curl -X PUT http://localhost/api/souscriptions/1 -H "Content-Type: application/json" \
  -d '{"code_client":"12345678","nom_client":"Jean Dupont","produit":"ASSURANCE_VIE","date_souscription":"2026-01-15"}'

# Delete
curl -X DELETE http://localhost/api/souscriptions/1
```

## Exécuter les tests en local

```bash
cd app
pip install -r requirements.txt
pip install pytest pytest-cov flake8
cd ..
pytest --cov=app tests/
flake8 app tests --max-line-length=120
```

## Pipeline CI/CD

`.github/workflows/ci.yml` s'exécute sur `push`/`pull_request` (`main`, `develop`) : lint (flake8) → tests (pytest, SQLite en mémoire) → build Docker (API + Nginx).

## Sécurité (PCI-DSS / ISO 27001)

- Conteneur API exécuté avec un utilisateur non-root dédié.
- Build multi-stage réduisant la surface d'attaque.
- Réseau `backend` (api ↔ db) interne, non exposé ; seul `nginx` est publié.
- En-têtes de sécurité HTTP ajoutés par Nginx.
- Secrets fournis via `.env`, exclu du dépôt Git par `.gitignore` (seul `.env.example` versionné).

## Équipe (factice)

- Camille Martin — DevOps Lead
- Sofia Nguyen — Backend Flask
- Younes El Amrani — Frontend & QA
- Léa Bertrand — Sécurité & CI/CD
