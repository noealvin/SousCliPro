"""
Application de souscription produit client - API Flask (CRUD complet)
Sujet 4 - TP DevOps

Expose:
  GET    /                          -> Interface web (index.html)
  POST   /api/souscriptions         -> Creer une souscription
  GET    /api/souscriptions         -> Lister toutes les souscriptions
  GET    /api/souscriptions/<id>    -> Recuperer une souscription
  PUT    /api/souscriptions/<id>    -> Modifier une souscription
  DELETE /api/souscriptions/<id>    -> Supprimer une souscription
  GET    /health                    -> Etat de sante du backend + BDD
"""""

import os
import re
import time
from datetime import datetime, date, timezone
from functools import wraps

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, UniqueConstraint
from sqlalchemy.exc import OperationalError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PRODUITS_VALIDES = [
    "LIVRET_EPARGNE",
    "ASSURANCE_VIE",
    "CREDIT_CONSOMMATION",
    "COMPTE_COURANT",
    "CARTE_PREMIUM",
]

CODE_CLIENT_REGEX = re.compile(r"^\d{8}$")

DEFAULT_DATABASE_URL = (
    "postgresql://postgres:postgres@localhost:5432/souscription_produit"
)


def build_database_url():
    """Construit l'URL de connexion PostgreSQL depuis les variables d'env."""
    explicit_url = os.environ.get("DATABASE_URL")
    if explicit_url:
        return explicit_url

    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db_name = os.environ.get("POSTGRES_DB", "souscription_produit")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = build_database_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
    }
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    app.config["LOGIN_DISABLED"] = False

    db.init_app(app)
    return app


ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def login_requis(vue):
    @wraps(vue)
    def enveloppe(*args, **kwargs):
        if app.config.get("LOGIN_DISABLED"):
            return vue(*args, **kwargs)
        if session.get("utilisateur"):
            return vue(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "errors": ["Authentification requise."]}), 401
        return redirect(url_for("login"))
    return enveloppe


db = SQLAlchemy()


# ---------------------------------------------------------------------------
# Modele de donnees
# ---------------------------------------------------------------------------

class Souscription(db.Model):
    __tablename__ = "souscriptions"
    __table_args__ = (
        UniqueConstraint("code_client", "produit", name="uq_client_produit"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code_client = db.Column(db.String(8), nullable=False)
    nom_client = db.Column(db.String(255), nullable=False)
    produit = db.Column(db.String(50), nullable=False)
    date_souscription = db.Column(db.Date, nullable=False)
    date_creation = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "code_client": self.code_client,
            "nom_client": self.nom_client,
            "produit": self.produit,
            "date_souscription": self.date_souscription.isoformat() if self.date_souscription else None,
            "date_creation": self.date_creation.isoformat() if self.date_creation else None,
        }


# ---------------------------------------------------------------------------
# Validation metier
# ---------------------------------------------------------------------------

def parser_date(valeur):
    """Parse une date ISO (YYYY-MM-DD). Retourne None si invalide."""
    if not valeur:
        return None
    try:
        return datetime.strptime(valeur, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def valider_souscription(data, souscription_id=None):
    """
    Valide les regles metier du Sujet 4 (souscription produit client).
    Retourne (erreurs: list[str], valeurs_nettoyees: dict)
    """
    erreurs = []

    if not isinstance(data, dict):
        return ["Le corps de la requete doit etre un objet JSON valide."], {}

    code_client = (data.get("code_client") or "").strip()
    nom_client = (data.get("nom_client") or "").strip()
    produit = (data.get("produit") or "").strip()
    date_souscription_str = (data.get("date_souscription") or "").strip()

    # Code client
    if not code_client:
        erreurs.append("Le code client est obligatoire.")
    elif not CODE_CLIENT_REGEX.match(code_client):
        erreurs.append("Le code client doit etre compose de 8 chiffres exactement.")

    # Nom client
    if not nom_client:
        erreurs.append("Le nom du client est obligatoire.")

    # Produit
    if not produit:
        erreurs.append("Le produit souscrit est obligatoire.")
    elif produit not in PRODUITS_VALIDES:
        erreurs.append(
            f"Produit invalide '{produit}'. Valeurs autorisees: {PRODUITS_VALIDES}."
        )

    # Date de souscription
    date_souscription = parser_date(date_souscription_str)
    if not date_souscription_str:
        erreurs.append("La date de souscription est obligatoire.")
    elif date_souscription is None:
        erreurs.append("La date de souscription doit etre au format YYYY-MM-DD.")
    elif date_souscription > date.today():
        erreurs.append("La date de souscription ne peut pas etre dans le futur.")

    # Unicite code_client + produit (hors la souscription elle-meme en cas de modification)
    if code_client and produit and produit in PRODUITS_VALIDES and CODE_CLIENT_REGEX.match(code_client):
        requete = Souscription.query.filter_by(code_client=code_client, produit=produit)
        if souscription_id is not None:
            requete = requete.filter(Souscription.id != souscription_id)
        if requete.first() is not None:
            erreurs.append(
                f"Le client {code_client} a deja souscrit au produit {produit}."
            )

    valeurs = {
        "code_client": code_client,
        "nom_client": nom_client,
        "produit": produit,
        "date_souscription": date_souscription,
    }

    return erreurs, valeurs


# ---------------------------------------------------------------------------
# Initialisation Flask + retry-loop de connexion PostgreSQL
# ---------------------------------------------------------------------------

app = create_app()


def attendre_bdd_et_creer_tables(max_tentatives=5, delai_secondes=3):
    """
    Mecanisme de retry-loop pour eviter que Flask ne crash si PostgreSQL
    n'a pas encore fini de demarrer lors du 'docker compose up'.
    """
    for tentative in range(1, max_tentatives + 1):
        try:
            with app.app_context():
                db.session.execute(text("SELECT 1"))
                db.create_all()
            print(f"[startup] Connexion PostgreSQL etablie (tentative {tentative}).")
            return True
        except OperationalError as exc:
            print(
                f"[startup] Tentative {tentative}/{max_tentatives} echouee : {exc}. "
                f"Nouvel essai dans {delai_secondes}s..."
            )
            time.sleep(delai_secondes)
        except Exception as exc:
            print(
                f"[startup] Tentative {tentative}/{max_tentatives} echouee (erreur inattendue) : {exc}. "
                f"Nouvel essai dans {delai_secondes}s..."
            )
            time.sleep(delai_secondes)

    print("[startup] Impossible de se connecter a PostgreSQL apres plusieurs tentatives.")
    return False


if os.environ.get("SKIP_DB_INIT") != "1":
    attendre_bdd_et_creer_tables()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET"])
def login():
    if session.get("utilisateur"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["utilisateur"] = username
        return jsonify({"success": True, "message": "Connexion reussie."})

    return jsonify({"success": False, "errors": ["Identifiants invalides."]}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("utilisateur", None)
    return jsonify({"success": True})


@app.route("/")
@login_requis
def index():
    return render_template("index.html", produits=PRODUITS_VALIDES)


@app.route("/api/souscriptions", methods=["POST"])
@login_requis
def creer_souscription():
    data = request.get_json(silent=True)
    erreurs, valeurs = valider_souscription(data)

    if erreurs:
        return jsonify({"success": False, "errors": erreurs}), 400

    souscription = Souscription(
        code_client=valeurs["code_client"],
        nom_client=valeurs["nom_client"],
        produit=valeurs["produit"],
        date_souscription=valeurs["date_souscription"],
    )

    db.session.add(souscription)
    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "message": "Souscription enregistree avec succes.",
                "souscription": souscription.to_dict(),
            }
        ),
        201,
    )


@app.route("/api/souscriptions", methods=["GET"])
@login_requis
def lister_souscriptions():
    souscriptions = Souscription.query.order_by(Souscription.date_creation.desc()).all()
    return jsonify(
        {
            "success": True,
            "count": len(souscriptions),
            "souscriptions": [s.to_dict() for s in souscriptions],
        }
    )


@app.route("/api/souscriptions/<int:souscription_id>", methods=["GET"])
@login_requis
def obtenir_souscription(souscription_id):
    souscription = Souscription.query.get(souscription_id)
    if souscription is None:
        return jsonify({"success": False, "errors": ["Souscription introuvable."]}), 404
    return jsonify({"success": True, "souscription": souscription.to_dict()})


@app.route("/api/souscriptions/<int:souscription_id>", methods=["PUT"])
@login_requis
def modifier_souscription(souscription_id):
    souscription = Souscription.query.get(souscription_id)
    if souscription is None:
        return jsonify({"success": False, "errors": ["Souscription introuvable."]}), 404

    data = request.get_json(silent=True)
    erreurs, valeurs = valider_souscription(data, souscription_id=souscription_id)

    if erreurs:
        return jsonify({"success": False, "errors": erreurs}), 400

    souscription.code_client = valeurs["code_client"]
    souscription.nom_client = valeurs["nom_client"]
    souscription.produit = valeurs["produit"]
    souscription.date_souscription = valeurs["date_souscription"]

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "Souscription modifiee avec succes.",
            "souscription": souscription.to_dict(),
        }
    )


@app.route("/api/souscriptions/<int:souscription_id>", methods=["DELETE"])
@login_requis
def supprimer_souscription(souscription_id):
    souscription = Souscription.query.get(souscription_id)
    if souscription is None:
        return jsonify({"success": False, "errors": ["Souscription introuvable."]}), 404

    db.session.delete(souscription)
    db.session.commit()

    return jsonify({"success": True, "message": "Souscription supprimee avec succes."})


@app.route("/health", methods=["GET"])
def health():
    db_status = "ok"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"erreur: {exc}"

    return jsonify(
        {
            "status": "ok",
            "database": db_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
