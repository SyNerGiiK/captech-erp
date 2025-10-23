# AGENTS.md – Configuration des Agents pour CapTech ERP

Ce fichier définit la manière dont les agents (comme Codex ou tout autre assistant IA) interagissent avec le projet **CapTech ERP**.

---

## 🎯 Objectif

Fournir un cadre clair pour permettre à un agent IA de :

* Installer et lancer le projet localement.
* Comprendre les rôles et les responsabilités de chaque agent.
* Respecter les limites de sécurité et d’accès aux données.

---

## 🧠 Agents définis

### 🧩 Agent Codex (principal)

**Rôle :** Développeur et assistant technique.

**Responsabilités :**

* Lire et interpréter le code Python/Django et le frontend TailwindCSS.
* Aider à la configuration de l’environnement local.
* Générer ou corriger du code selon les besoins.
* Documenter automatiquement les modules si nécessaire.

**Ne doit pas faire :**

* Exécuter des commandes de production ou de déploiement.
* Modifier directement la base de données distante.
* Supprimer ou écraser les fichiers de configuration sensibles.

### 🧮 Agent Analyseur (optionnel)

**Rôle :** Vérifier la qualité du code et identifier les erreurs.
**Responsabilités :**

* Exécuter des vérifications de linting (PEP8, ESLint, etc.).
* Proposer des optimisations de performance ou de structure.

---

## ⚙️ Instructions d’environnement

### Backend (Django)

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend (TailwindCSS / JS)

```bash
npm install
npm run dev
```

**Base de données :** SQLite (par défaut `db.sqlite3`)

---

## 🔒 Règles et sécurité

* Aucune clé API ou mot de passe ne doit être enregistré en dur dans le code.
* Les variables sensibles sont stockées dans `.env`.
* Les scripts d’installation ne doivent pas modifier les données de production.

---

## 🚀 Extensions futures

* Intégration d’un agent de documentation automatique (`doc_agent`).
* Création d’un agent de test unitaire (`test_agent`).

---

## ✅ Validation

Avant de lancer une tâche :

1. Vérifier que toutes les dépendances sont installées.
2. S’assurer que la base locale (`db.sqlite3`) est bien configurée.
3. Exécuter les migrations avant tout test de lancement.

---

**Auteur :** Vincent Navel
**Projet :** CapTech ERP
**Version :** 1.0.0
