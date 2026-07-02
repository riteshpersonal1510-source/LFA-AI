git add .
git commit -m "Accha - 7.0"
git push


Still i got this error :
[python-scraper] Python scraper returned HTTP 404: {"detail":"Not Found"}
Also you can changes creating updating modifying the /frontend /backend /ai-service folder with accurate output
You are the lead software architect responsible for repairing this production application.

PROJECT
/frontend      -> Next.js
/backend       -> Node.js + Express
/ai-service    -> FastAPI
MISSION
The application MUST work completely in production.
The goal is NOT to patch one error.
The goal is to repair the entire search pipeline while preserving every existing feature.
========================================================
STRICT RULES
========================================================
DO NOT guess.
DO NOT create duplicate APIs.
DO NOT create duplicate models.
DO NOT replace working code.
DO NOT remove existing WhatsApp automation.
DO NOT remove existing analysis APIs.
DO NOT remove authentication.
DO NOT stop after fixing one error.
Work until the entire production flow works.
========================================================
CURRENT ERROR
========================================================
Frontend
Searching Leads Failed
Backend
Python scraper returned HTTP 404
{"detail":"Not Found"}
This means the backend is calling a endpoint that does not exist inside the deployed FastAPI service.
Find the real cause.
========================================================
PHASE 1 — COMPLETE PROJECT AUDIT
========================================================
Inspect every file inside
/backend
/ai-service
/frontend
Build an architecture map.
Identify
all routers
all services
all controllers
all websocket handlers
all database services
all API clients
all scraping modules
all background workers
all session managers
all models
all DTOs
all schemas
========================================================
PHASE 2 — FASTAPI ROUTES
========================================================
Search the entire AI Service for
APIRouter(
Search for
include_router(
List every router.
List every endpoint.
If routers exist but are not registered
register them.
If endpoints are missing
implement them.
Never duplicate an existing router.
========================================================
PHASE 3 — REQUIRED ENDPOINTS
========================================================
The production API must expose
POST /api/v1/search
POST /api/v1/scraper/search
GET /api/v1/scraper/search-progress/{sessionId}
POST /api/v1/google-maps/search
POST /api/v1/lead-enrichment
POST /api/v1/semantic-search
GET /api/v1/search/results/{sessionId}
GET /api/v1/search/status/{sessionId}
GET /health
GET /
========================================================
PHASE 4 — IF FILES ARE MISSING
========================================================
If search.py
scraper.py
google_maps.py
progress.py
do not exist,
create them using the existing architecture.
Do NOT invent a different architecture.
Use the project's dependency injection, settings, logging and database style.
========================================================
PHASE 5 — BACKEND
========================================================
Search every file using
AI_SERVICE_URL
PYTHON_SCRAPER_URL
axios
fetch
httpx
requests
Verify every outgoing request.
Every backend endpoint MUST match FastAPI exactly.
If backend calls
/api/v1/search
FastAPI must expose
/api/v1/search
No mismatches.
========================================================
PHASE 6 — SEARCH PIPELINE
========================================================
Implement or repair
Keyword
Location
Google Maps search
Business extraction
Website detection
Phone extraction
Email extraction
Address extraction
Google rating
Review count
Lead scoring
MongoDB save
Session management
========================================================
PHASE 7 — LIVE SEARCH
========================================================
Searching should work like
Frontend
↓
Backend
↓
AI Service
↓
Scraper
↓
Google Maps
↓
Website Analyzer
↓
Lead Scoring
↓
MongoDB
↓
Backend
↓
WebSocket
↓
Frontend
========================================================
PHASE 8 — SESSION MANAGEMENT
========================================================
Implement
SearchSession
Progress
Status
Completion
Errors
Current Business
Current Page
Lead Count
Store active sessions in memory.
Persist completed sessions.
Progress endpoint must NEVER return 404.
========================================================
PHASE 9 — WEBSOCKET
========================================================
Implement
/ws
Features
Reconnect
Progress updates
Lead count
Status
Completion
Errors
========================================================
PHASE 10 — WHATSAPP
========================================================
Keep existing WhatsApp automation working.
Do not break
Template service
Mongo connection
Engine
API
Routes
Background workers
========================================================
PHASE 11 — STARTUP DIAGNOSTICS
========================================================
During startup print
Registered Routes
Router Count
Environment
PORT
BACKEND_URL
FRONTEND_URL
MongoDB
Every endpoint
========================================================
PHASE 13 — PRODUCTION TEST
========================================================
Verify
GET /
GET /health
POST /api/v1/search
POST /api/v1/scraper/search
GET /api/v1/scraper/search-progress/test
All must return valid responses.
No 404.
========================================================
PHASE 14 — FINAL
========================================================
Return
Files modified
Files created
Endpoints created
Endpoints repaired
Backend fixes
Frontend fixes
WebSocket fixes
Database fixes
Production verification
The task is NOT complete until searching leads works successfully from the frontend in production.


You are the Lead Staff Software Engineer responsible for fixing a production MERN + FastAPI application.

This is NOT a greenfield project.

DO NOT rewrite the project.

DO NOT create duplicate functionality.

DO NOT remove existing business logic unless it is broken.

Your first job is to understand the existing architecture.

You MUST inspect the project before modifying anything.

===========================================================
PROJECT
===========================================================

Folders

/frontend
/backend
/ai-service

Frontend

Next.js

Backend

Node.js
Express
MongoDB
Socket.IO

AI Service

FastAPI
Python

===========================================================
CURRENT PRODUCTION ISSUE
===========================================================

Search fails.

Frontend shows

Search Failed

Backend logs

Python scraper returned HTTP 404

AI Service returns

404 Not Found

===========================================================
CRITICAL RULE
===========================================================

Never guess.

Never invent endpoints.

Never assume router names.

Always inspect the codebase.

===========================================================
PHASE 1
PROJECT AUDIT
===========================================================

Search the entire project.

Locate

main.py

Find every

APIRouter

Find every

include_router

Find every

router = APIRouter()

Print

File

Router prefix

Tags

Methods

Endpoints

===========================================================
PHASE 2
FASTAPI ROUTES
===========================================================

Print every registered route.

Example

for route in app.routes:
    print(route.path, route.methods)

Startup log should contain

REGISTERED ROUTES

Router Count

Environment

PORT

BACKEND_URL

AI_SERVICE_URL

===========================================================
PHASE 3
VERIFY  
===========================================================

Open

  

Verify endpoints exist.

Search endpoint

Scraper endpoint

Progress endpoint

Maps endpoint

Lead enrichment endpoint

Semantic endpoint

If missing

Find why

Router not imported

Router not included

Wrong prefix

Wrong module

Wrong file

===========================================================
PHASE 4
BACKEND AUDIT
===========================================================

Search

AI_SERVICE_URL

axios

fetch

request

httpx

Every outgoing request.

Print

Method

URL

Headers

Payload

Timeout

===========================================================
PHASE 5
COMPARE CONTRACT
===========================================================

Backend endpoint

↓

FastAPI endpoint

They must match.

If backend calls

/api/v1/scraper/search

FastAPI MUST expose

/api/v1/scraper/search

Do not create multiple aliases.

Use one consistent API contract.

===========================================================
PHASE 6
SEARCH PIPELINE
===========================================================

Search request

↓

Validate payload

↓

Generate sessionId

↓

Store active session

↓

Start async scraper

↓

Return sessionId immediately

↓

Progress updates

↓

Lead extraction

↓

Mongo save

↓

Status completed

===========================================================
PHASE 7
SCRAPER
===========================================================

Inspect current scraper.

If incomplete

Fix it.

Never replace with fake data.

Scraper must collect

Business Name

Website

Phone

Email

Address

Rating

Reviews

Google Maps URL

Latitude

Longitude

Category

Status

===========================================================
PHASE 8
WEBSITE ANALYSIS
===========================================================

Visit website.

Extract

Emails

Phone numbers

Facebook

Instagram

LinkedIn

Contact page

About page

Title

Meta description

Technologies

===========================================================
PHASE 9
EMAIL EXTRACTION
===========================================================

Collect emails from

Homepage

Contact

Footer

Header

mailto

Schema

JSON

Scripts

===========================================================
PHASE 10
PHONE EXTRACTION
===========================================================

Extract

International

Local

WhatsApp

Click-to-call

===========================================================
PHASE 11
LEAD SCORING
===========================================================

Generate

Has Website

Has Email

Has Phone

Business Category

Lead Score

Priority

===========================================================
PHASE 12
DATABASE
===========================================================

Prevent duplicates.

Upsert existing leads.

Keep history.

===========================================================
PHASE 13
SEARCH PROGRESS
===========================================================

Never return 404.

If session exists

Return progress.

If completed

Return completed.

If failed

Return reason.

===========================================================
PHASE 14
WEBSOCKET
===========================================================

Implement

/ws

Reconnect

Heartbeat

Progress updates

Errors

Completion

===========================================================
PHASE 15
LOGGING
===========================================================

Log every step.

Request received

Validation

AI request

Scraper started

Maps search

Website scraping

Email extraction

Mongo save

Socket emit

Completed

===========================================================
PHASE 16
ERROR HANDLING
===========================================================

Never return raw traceback.

Return structured JSON.

Example

status

message

details

sessionId

===========================================================
PHASE 17
RENDER
===========================================================

Verify deployment.

Verify environment variables.

Verify latest commit deployed.

Verify startup logs.

===========================================================
PHASE 18
HEALTH CHECK
===========================================================

Startup logs must print

All registered routes

Router count

Mongo status

Environment

===========================================================
PHASE 19
TEST
===========================================================

Verify

GET /

GET /health


POST /api/v1/search

POST /api/v1/scraper/search

GET /api/v1/scraper/search-progress/{sessionId}

WebSocket

===========================================================
PHASE 20
PRODUCTION READY
===========================================================

Search flow must be

Frontend

↓

Backend

↓

AI Service

↓

Scraper

↓

Lead Extraction

↓

Website Analysis

↓

MongoDB

↓

Progress

↓

WebSocket

↓

Frontend

===========================================================
IMPORTANT
===========================================================

Do not stop after fixing one bug.

Continue inspecting until

No endpoint returns 404.

No router missing.

No backend URL mismatch.

No websocket failure.

No missing environment variable.

No API contract mismatch.

No progress endpoint failure.

No duplicate routes.

No deployment mismatch.

The search must return real leads.

The scraper must collect real businesses.

The frontend must display them live.

At the end provide

1. Root cause

2. Files modified

3. Why it failed

4. What was fixed

5. Routes added

6. Deployment verification

7. Production test results

8. Remaining recommendations

Do not finish until the entire production search flow works successfully.

Also you can update the /frontend /backend /ai-service folder with accurate output


You are a senior FastAPI + MERN architect.

Do not make temporary fixes.

Do not create mock endpoints.

Do not return fake responses.

Inspect the ENTIRE repository before editing.

Allowed folders

/backend
/ai-service
/frontend

====================================================
GOAL
====================================================

The backend calls the AI Service for production lead scraping.

Current production error:

Python scraper returned HTTP 404

The deployed AI Service only exposes

POST /api/v1/analyze-lead
POST /api/v1/bulk-analyze
POST /api/v1/score-only

The backend expects endpoints like

POST /api/v1/search
POST /api/v1/scraper/search
GET /api/v1/scraper/search-progress/{sessionId}

These routes do not exist.

Do NOT create fake placeholder routes.

Implement the REAL production scraper.

====================================================
STEP 1
====================================================

Search the ENTIRE ai-service for

APIRouter(

Print every router.

Print every endpoint.

Print every HTTP method.

====================================================
STEP 2
====================================================

Search backend for

AI_SERVICE_URL

requests

httpx

axios

fetch

Find EVERY request sent to AI Service.

Print

Method

URL

Payload

Expected Response

====================================================
STEP 3
====================================================

Compare backend URLs with FastAPI URLs.

Identify every mismatch.

====================================================
STEP 4
====================================================

If backend expects

POST /api/v1/search

implement it.

If backend expects

POST /api/v1/scraper/search

implement it.

If backend expects

GET /api/v1/scraper/search-progress/{sessionId}

implement it.

These endpoints must perform REAL scraping.

====================================================
STEP 5
====================================================

Search the project for

playwright

google maps

maps scraper

business parser

lead finder

search session

If code already exists

reuse it.

Do NOT rewrite working code.

====================================================
STEP 6
====================================================

If scraper code is missing

create

app/routes/search.py

app/services/google_maps_scraper.py

app/services/session_manager.py

app/models/search_models.py

Implement production Google Maps scraping.

====================================================
STEP 7
====================================================

POST /api/v1/search

must

create session

start background scraping

return

{
 sessionId,
 status:"started"
}

====================================================
STEP 8
====================================================

Implement

GET /api/v1/scraper/search-progress/{sessionId}

Return

status

current page

current business

processed

total

saved

failed

percentage

completed

====================================================
STEP 9
====================================================

Google Maps scraper must collect

Business Name

Category

Website

Phone

Email

Address

Google Rating

Review Count

Latitude

Longitude

Maps URL

====================================================
STEP 10
====================================================

Save every lead into MongoDB exactly as backend expects.

====================================================
STEP 11
====================================================

Backend websocket must receive

session started

progress

business found

lead saved

completed

errors

====================================================
STEP 12
====================================================

Register every router inside

main.py

Verify

app.include_router(...)

====================================================
STEP 13
====================================================

Startup logs must print

REGISTERED ROUTES

Router Count

Environment

PORT

BACKEND_URL

====================================================
STEP 14
====================================================

Verify

contains

POST /api/v1/search

POST /api/v1/scraper/search

GET /api/v1/scraper/search-progress/{sessionId}

====================================================
STEP 15
====================================================

After implementation verify

curl GET /

curl GET /health

curl POST /api/v1/search

curl POST /api/v1/scraper/search

curl GET /api/v1/scraper/search-progress/test

All must return valid responses.

Do not stop until production search successfully scrapes Google Maps businesses and backend no longer returns HTTP 404.

https://lfa-ai.onrender.com/api/v1/search it shows not found

Also you can update the /frontend /backend /ai-service folder with accurate output
