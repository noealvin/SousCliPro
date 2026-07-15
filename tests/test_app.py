"""
Suite de tests pytest - Application de souscription produit client (Sujet 4)
Utilise une base SQLite en mémoire pour exécuter les tests sans PostgreSQL
(compatible GitHub Actions runner sans service additionnel).
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

# Configuration avant l'import de l'application
os.environ["SKIP_DB_INIT"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Ajout de la racine du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.app as app_module  # noqa: E402


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    app_module.app.config["LOGIN_DISABLED"] = True
    app_module.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app_module.app.app_context():
        app_module.db.create_all()

    with app_module.app.test_client() as test_client:
        yield test_client

    with app_module.app.app_context():
        app_module.db.drop_all()


SOUSCRIPTION_VALIDE = {
    "code_client": "12345678",
    "nom_client": "Jean Dupont",
    "produit": "LIVRET_EPARGNE",
    "date_souscription": "2026-01-15",
}


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_index_route_sert_le_frontend(client):
    response = client.get("/")
    assert response.status_code == 200


def test_souscription_valide_reussit(client):
    response = client.post("/api/souscriptions", json=SOUSCRIPTION_VALIDE)
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["souscription"]["code_client"] == "12345678"


def test_code_client_invalide_est_rejete(client):
    payload = dict(SOUSCRIPTION_VALIDE, code_client="123")
    response = client.post("/api/souscriptions", json=payload)
    assert response.status_code == 400
    assert any("code client" in e.lower() for e in response.get_json()["errors"])


def test_code_client_obligatoire(client):
    payload = dict(SOUSCRIPTION_VALIDE, code_client="")
    response = client.post("/api/souscriptions", json=payload)
    assert response.status_code == 400


def test_produit_invalide_est_rejete(client):
    payload = dict(SOUSCRIPTION_VALIDE, produit="PRODUIT_INCONNU")
    response = client.post("/api/souscriptions", json=payload)
    assert response.status_code == 400
    assert any("produit" in e.lower() for e in response.get_json()["errors"])


def test_date_future_est_rejetee(client):
    date_future = (date.today() + timedelta(days=30)).isoformat()
    payload = dict(SOUSCRIPTION_VALIDE, date_souscription=date_future)
    response = client.post("/api/souscriptions", json=payload)
    assert response.status_code == 400
    assert any("futur" in e.lower() for e in response.get_json()["errors"])


def test_date_format_invalide_est_rejetee(client):
    payload = dict(SOUSCRIPTION_VALIDE, date_souscription="15/01/2026")
    response = client.post("/api/souscriptions", json=payload)
    assert response.status_code == 400


def test_doublon_client_produit_est_rejete(client):
    client.post("/api/souscriptions", json=SOUSCRIPTION_VALIDE)
    response = client.post("/api/souscriptions", json=SOUSCRIPTION_VALIDE)
    assert response.status_code == 400
    assert any("deja souscrit" in e.lower() for e in response.get_json()["errors"])


def test_meme_client_produit_different_est_accepte(client):
    client.post("/api/souscriptions", json=SOUSCRIPTION_VALIDE)
    payload = dict(SOUSCRIPTION_VALIDE, produit="ASSURANCE_VIE")
    response = client.post("/api/souscriptions", json=payload)
    assert response.status_code == 201


def test_lister_souscriptions(client):
    client.post("/api/souscriptions", json=SOUSCRIPTION_VALIDE)
    response = client.get("/api/souscriptions")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["count"] >= 1


def test_obtenir_une_souscription(client):
    creation = client.post("/api/souscriptions", json=SOUSCRIPTION_VALIDE)
    souscription_id = creation.get_json()["souscription"]["id"]
    response = client.get(f"/api/souscriptions/{souscription_id}")
    assert response.status_code == 200
    assert response.get_json()["souscription"]["code_client"] == "12345678"


def test_obtenir_souscription_inexistante(client):
    response = client.get("/api/souscriptions/9999")
    assert response.status_code == 404


def test_modifier_une_souscription(client):
    creation = client.post("/api/souscriptions", json=SOUSCRIPTION_VALIDE)
    souscription_id = creation.get_json()["souscription"]["id"]
    maj = dict(SOUSCRIPTION_VALIDE, nom_client="Nouveau Nom", produit="CARTE_PREMIUM")
    response = client.put(f"/api/souscriptions/{souscription_id}", json=maj)
    assert response.status_code == 200
    data = response.get_json()
    assert data["souscription"]["nom_client"] == "Nouveau Nom"
    assert data["souscription"]["produit"] == "CARTE_PREMIUM"


def test_modifier_souscription_inexistante(client):
    response = client.put("/api/souscriptions/9999", json=SOUSCRIPTION_VALIDE)
    assert response.status_code == 404


def test_supprimer_une_souscription(client):
    creation = client.post("/api/souscriptions", json=SOUSCRIPTION_VALIDE)
    souscription_id = creation.get_json()["souscription"]["id"]
    response = client.delete(f"/api/souscriptions/{souscription_id}")
    assert response.status_code == 200

    verification = client.get(f"/api/souscriptions/{souscription_id}")
    assert verification.status_code == 404


def test_supprimer_souscription_inexistante(client):
    response = client.delete("/api/souscriptions/9999")
    assert response.status_code == 404


def test_nom_client_obligatoire(client):
    payload = dict(SOUSCRIPTION_VALIDE, nom_client="")
    response = client.post("/api/souscriptions", json=payload)
    assert response.status_code == 400
    assert any("nom" in e.lower() for e in response.get_json()["errors"])
