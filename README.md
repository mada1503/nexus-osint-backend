# NexusSearch OSINT Platform

## 🗂️ Structure du Projet

```
NexusSearch/
├── docker-compose.yml         # Tous les services en 1 commande
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example           # ⚠️ Copiez en .env et ajoutez vos clés
│   └── app/
│       ├── main.py            # FastAPI application
│       ├── config.py          # Settings (env vars)
│       ├── models/
│       │   ├── database.py    # SQLAlchemy async engine
│       │   └── models.py      # ORM: User, SearchJob, SearchResult
│       ├── workers/
│       │   ├── celery_app.py  # Celery factory
│       │   └── tasks.py       # 6 workers OSINT (pivot, google, holehe...)
│       └── api/routes/
│           ├── search.py      # POST /api/search + GET /api/search/status/{id}
│           ├── auth.py        # (à implémenter)
│           └── results.py     # (à implémenter)
└── frontend/                  # React/Vite (voir README)
```

## 🚀 Démarrage Rapide

### Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et lancé
- Python 3.11+ (pour le dev local uniquement)

### 1. Configuration

```bash
cd backend
cp .env.example .env
# Ouvrez .env et ajoutez vos clés API (voir section ci-dessous)
```

### 2. Lancer tous les services

```bash
docker-compose up --build
```

Cela démarre :
| Service | URL |
|---------|-----|
| FastAPI API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Celery Flower (Monitor) | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 3. Tester l'API

```bash
# Lancer une recherche par email
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "target@example.com", "search_type": "email"}'

# Réponse: {"job_id": "...", "status": "pending", "message": "..."}

# Vérifier le statut de la tâche
curl http://localhost:8000/api/search/status/{TASK_ID}
```

## 🔑 Clés API Nécessaires

| Clé | Gratuit ? | Lien |
|-----|-----------|------|
| `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` | ✅ 100 req/jour gratuit | [Google Cloud Console](https://console.cloud.google.com/) + [Custom Search Engine](https://cse.google.com/) |
| `HUNTER_API_KEY` | ✅ 25 req/mois gratuit | [hunter.io](https://hunter.io/) |
| `HIBP_API_KEY` | ❌ Payant (£3.50/mois) | [haveibeenpwned.com](https://haveibeenpwned.com/API/Key) |
| `SHODAN_API_KEY` | ✅ Free tier | [shodan.io](https://account.shodan.io/) |

## ⚙️ Les 6 Workers OSINT

| Worker | Source | Type | Légal |
|--------|--------|------|-------|
| `task_pivot_username` | HTTP HEAD sur 16 plateformes | Pseudo | ✅ |
| `task_google_search` | Google Custom Search API | Pseudo/Nom | ✅ |
| `task_holehe_email` | Holehe (110+ sites via forgot-password) | Email | ✅ |
| `task_hunter_lookup` | Hunter.io API | Email pro | ✅ |
| `task_hibp_check` | HaveIBeenPwned API | Email | ✅ |
| `task_whois_lookup` | WHOIS public | Domaine | ✅ |

## 📊 Architecture

```
Frontend (React)
    │ POST /api/search
    ▼
FastAPI (main.py)
    │ dispatch task
    ▼
Celery Worker ──────────► Redis (broker)
    │                       ▲
    │ run_full_investigation │ result
    ▼                       │
 subtasks (concurrent):     │
   task_google_search       │
   task_holehe_email  ──────┘
   task_pivot_username
   task_hibp_check
    │
    ▼
PostgreSQL (SearchResult rows)
```

## 🔮 Prochaines Étapes

1. **Frontend React** : Dashboard avec polling, timeline, et D3.js graph
2. **Auth JWT** : Système de comptes utilisateurs
3. **NLP Layer** : Intégration GPT-4o mini pour synthèse automatique des résultats
4. **Neo4j** : Graphe relationnel persistant entre entités
