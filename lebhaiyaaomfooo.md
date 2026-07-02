You are a Senior Python + FastAPI + Flask + Node.js + Express + MERN + Web Scraping Engineer.

Analyze the entire project before making any changes.

You are allowed to modify:

/backend
/ai-service
/frontend

Do not create duplicate implementations.

Find the real root cause and fix it.

Current Problem

The Search feature is failing.

Frontend shows:

Search Failed

Status:
[python-scraper] fetch failed

No leads are returned.

Statistics remain

Found: 0
Saved: 0
Duplicates: 0
Rejected: 0

The AI Service is already deployed on Render.

Backend is also deployed.

The frontend can communicate with backend.

Only the scraper request is failing.

Goal

Fix the Search functionality completely.

When a user searches

Example

Keyword:
Hotel

Country:
New Zealand

State:
Auckland Region

City:
Waitakere

the application should successfully

Frontend

↓

Backend

↓

AI Service

↓

Python Scraper

↓

Google Maps Search

↓

Lead Enrichment

↓

MongoDB

↓

Return Leads

↓

Display in Frontend

without any manual intervention.

Step 1

Inspect every request between

Frontend

↓

Backend

↓

AI Service

Log every request.

Log every response.

Log every error.

Do not swallow exceptions.

Step 2

Verify Backend Environment Variables

Check

AI_SERVICE_URL

PYTHON_SERVICE_URL

SCRAPER_URL

API_URL

BASE_URL

PORT

Confirm that production URLs are correct.

No localhost values should exist in production.

Step 3

Verify Render Deployment

Confirm

AI Service

is actually reachable.

Test

GET /

GET /health

GET /ping

Then test

POST /search

POST /scrape

POST /maps/search

POST /google/search

depending on the implemented routes.

If route names differ,

update backend accordingly.

Step 4

Verify Backend Request

Inspect the request payload sent from backend.

Example

{
  keyword,
  country,
  state,
  city,
  maxResults,
  searchSessionId
}

Ensure backend sends exactly what AI Service expects.

Step 5

Verify AI Service Routes

Inspect every route.

Example

POST /search

POST /scrape

POST /google-maps

POST /maps/search

Ensure backend calls the correct endpoint.

Fix route mismatches.

Step 6

Inspect Python Scraper

Inspect

main.py

app.py

scraper.py

google_maps.py

services/

routes/


Check

try

except

timeouts

request failures

selectors

Playwright

Selenium

Requests

BeautifulSoup

Find why

fetch failed

is thrown.

Return meaningful errors instead.

Step 7

Improve Error Logging

Current

fetch failed

is useless.

Instead return

Network timeout

Google blocked request

Invalid selector

Playwright crashed

Browser launch failed

Environment variable missing

Invalid payload

Route not found

Proxy unavailable

API limit exceeded

Unexpected exception

Include stack trace in server logs.

Step 8

Check Playwright

If Playwright is used,

verify

Chromium installed

Headless mode

Sandbox disabled

Render compatible launch options

Example

headless=True

--no-sandbox

--disable-dev-shm-usage

--disable-setuid-sandbox

Ensure Render supports browser launch.

Step 9

Check Dependencies

Verify

requirements.txt

package.json

Dockerfile

render.yaml

build.sh

start.sh

Ensure every dependency is installed during Render deployment.

Especially

playwright

browser binaries

selenium

beautifulsoup4

requests

httpx

aiohttp
Step 10

Verify Health Endpoint

Create

GET /health

Return

{
  success:true,
  service:"AI Service",
  scraper:true,
  browser:true,
  google:true
}

Backend should verify this before sending search requests.

Step 11

Retry Mechanism

If Google request fails,

Retry automatically

3 times

before returning failure.

Use exponential backoff.

Step 12

Improve Timeout

Current request should not fail because of short timeout.

Increase timeout

Backend

↓

AI Service

↓

Python Scraper

appropriately.

Step 13

Frontend

Improve error handling.

Instead of

fetch failed

Display

Unable to retrieve search results.

Reason:
<actual backend error>

Please try again.

Show loading state.

Show retry button.

Step 14

Production Validation

After fixing,

test all scenarios

Hotel

Restaurant

Dental Clinic

Agency

Gym

Cafe

Lawyer

Verify

Country

State

City

Keyword

produce valid results.

Step 15

Verify Complete Flow

Run complete production test.

Frontend Search

↓

Backend receives request

↓

Backend validates payload

↓

Backend calls AI Service

↓

AI Service receives request

↓

Python scraper executes

↓

Google Maps searched

↓

Leads extracted

↓

Lead enrichment

↓

Duplicate detection

↓

MongoDB save

↓

Backend returns leads

↓

Frontend updates cards

↓

Found count increases

↓

Saved count increases
Expected Result

After implementation:

Search works successfully in production.
No more [python-scraper] fetch failed errors.
AI Service responds correctly to backend requests.
Backend uses the correct Render AI Service URL.
Proper health checks and logging are implemented.
Playwright/browser dependencies work on Render.
Leads are scraped, enriched, stored, and displayed in the frontend.
Error messages are descriptive and actionable.
The entire search pipeline is production-ready, resilient, and fully functional.