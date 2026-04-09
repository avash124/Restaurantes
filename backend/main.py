import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)  # backend/.env - must load before any backend.* imports

from contextlib import asynccontextmanager
import asyncio
import json
import threading
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from google.genai import types as genai_types
from backend.gemini_llm.gemini_client import get_gemini_client

from backend.database.db.init import init_db
from backend.database.core.config import settings
from backend.database.cache.job_progress import get_job_progress, set_job_progress
from backend.browser_use.services.searching_service import discover_restaurants_for_query
from backend.browser_use.services.enrichment_service import enrich_restaurant
from backend.browser_use.services.recommendation_service import rank_top_items_across_restaurants
from backend.engine.dispatch import supported_conditions
from backend.browser_use import session_registry
from backend.browser_use.agents.browser_use_client import get_browseruse_client
from backend.gemini_llm.intent_parser import parse_search_intent


CONDITION_LABEL_TO_ID: dict[str, str] = {
    "Diabetes":         "diabetes",
    "Celiac disease":   "celiac",
    "High cholesterol": "high_cholesterol",
    "Pregnancy":        "pregnancy",
}

ALLERGY_LABEL_TO_ID: dict[str, str] = {
    "Nuts":         "nut_allergy",
    "Shellfish":    "shellfish_allergy",
    "Soy":          "soy_allergy",
    "Milk or dairy": "dairy_allergy",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.postgres_url_is_usable():
        host = settings.postgres_hostname() or "<missing>"
        print(
            "[startup] DB init skipped - POSTGRES_URL is missing/invalid "
            f"(host='{host}'). Expected host format: db.<project-ref>.supabase.co"
        )
    else:
        try:
            init_db()
        except Exception as e:
            print(f"[startup] DB init skipped - {e}")
    yield
    
    try:
        client = get_browseruse_client()
        await session_registry.stop_all_sessions(client.sessions)
    except Exception as exc:
        print(f"[shutdown] error stopping browser-use sessions: {exc}")


app = FastAPI(title="Nourish API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={"Access-Control-Allow-Origin": "http://localhost:3000"},
    )


class DiscoverRequest(BaseModel):
    location: str
    radius_miles: float = 5.0
    query: str = ""
    conditions: list[str] = []
    allergies: list[str] = []
    custom_allergy: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/conditions")
def get_supported_conditions():
    """Return every condition ID the policy engine understands."""
    return {"supported": supported_conditions()}


@app.post("/api/discover")
async def discover(req: DiscoverRequest):
    job_id = str(uuid.uuid4())

    condition_ids: list[str] = [
        CONDITION_LABEL_TO_ID.get(c, c.lower().replace(" ", "_"))
        for c in req.conditions
    ]
    condition_ids += [
        ALLERGY_LABEL_TO_ID.get(a, f"{a.lower().replace(' ', '_')}_allergy")
        for a in req.allergies
    ]

    search_parts = [req.query] if req.query.strip() else []
    search_parts += req.conditions + req.allergies
    if req.custom_allergy.strip():
        search_parts.append(f"no {req.custom_allergy.strip()}")
    category = ", ".join(search_parts) if search_parts else "restaurant"

    slug = req.location.lower().replace(",", "").replace(" ", "_")
    lat_bucket = slug[:24]
    lng_bucket = slug[24:48] if len(slug) > 24 else "x"

    try:
        try:
            await set_job_progress(job_id, {"status": "running", "message": "Searching for restaurants..."})
        except Exception:
            pass  
        discovery = await discover_restaurants_for_query(
            lat_bucket=lat_bucket,
            lng_bucket=lng_bucket,
            location=req.location,
            radius_miles=req.radius_miles,
            category=category,
        )
        restaurants = discovery.get("restaurants", [])

        _sem = asyncio.Semaphore(6)

        async def _enrich(r: dict) -> dict:
            async with _sem:
                try:
                    return await enrich_restaurant(
                        restaurant_name=r["name"],
                        website_url=r.get("website_url"),
                        location_hint=req.location,
                    )
                except Exception:
                    return {
                        "restaurant_name": r["name"],
                        "address": r.get("address", ""),
                        "website_url": r.get("website_url"),
                        "menu_items": [],
                    }

        enriched: list[dict] = list(
            await asyncio.gather(*[_enrich(r) for r in restaurants])
        )

        if condition_ids:
            results = await rank_top_items_across_restaurants(
                enriched_restaurants=enriched,
                condition_ids=condition_ids,
                top_n=30,
            )
        else:
            results = [
                {
                    "restaurant_name": r.get("restaurant_name", ""),
                    "restaurant_address": r.get("address", ""),
                    "website_url": r.get("website_url"),
                    "menu_items_count": len(r.get("menu_items", [])),
                }
                for r in enriched
            ]

        try:
            await set_job_progress(job_id, {
                "status": "completed",
                "restaurants_found": len(restaurants),
                "results_count": len(results),
            })
        except Exception:
            pass

        return {
            "job_id": job_id,
            "restaurants_found": len(restaurants),
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as exc:
        try:
            await set_job_progress(job_id, {"status": "failed", "message": str(exc)})
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/discover/stream")
async def discover_stream(req: DiscoverRequest):
    """
    Streaming version of /api/discover.  Emits SSE events as each restaurant
    is enriched and evaluated, so the frontend can render results immediately.

    Event types:
      {"type": "status",    "message": "..."}
      {"type": "restaurant","data": { ranked_items, restaurant_name, ... }}
      {"type": "first_batch_complete"}
      {"type": "done",      "total_restaurants": N}
      {"type": "error",     "message": "..."}
    """
    condition_ids: list[str] = [
        CONDITION_LABEL_TO_ID.get(c, c.lower().replace(" ", "_"))
        for c in req.conditions
    ]
    condition_ids += [
        ALLERGY_LABEL_TO_ID.get(a, f"{a.lower().replace(' ', '_')}_allergy")
        for a in req.allergies
    ]

    search_parts = [req.query] if req.query.strip() else []
    search_parts += req.conditions + req.allergies
    if req.custom_allergy.strip():
        search_parts.append(f"no {req.custom_allergy.strip()}")
    category = ", ".join(search_parts) if search_parts else "restaurant"

    slug = req.location.lower().replace(",", "").replace(" ", "_")
    lat_bucket = slug[:24]
    lng_bucket = slug[24:48] if len(slug) > 24 else "x"

    async def _enrich_and_evaluate(r: dict) -> dict:
        """Enrich one restaurant and run condition analysis; return a result dict."""
        try:
            data = await enrich_restaurant(
                restaurant_name=r["name"],
                website_url=r.get("website_url"),
                location_hint=req.location,
            )
        except Exception:
            data = {
                "restaurant_name": r["name"],
                "address": r.get("address", ""),
                "website_url": r.get("website_url"),
                "menu_items": [],
            }

        if condition_ids:
            ranked = await rank_top_items_across_restaurants(
                enriched_restaurants=[data],
                condition_ids=condition_ids,
                top_n=10,
            )
        else:
            ranked = [
                {
                    "restaurant_name": data.get("restaurant_name", r["name"]),
                    "restaurant_address": data.get("address", ""),
                    "website_url": data.get("website_url"),
                    "menu_items_count": len(data.get("menu_items", [])),
                }
            ]

        return {
            "restaurant_name": data.get("restaurant_name", r["name"]),
            "restaurant_address": data.get("address", r.get("address", "")),
            "website_url": data.get("website_url"),
            "items": ranked,
        }

    async def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Searching for restaurants...'})}\n\n"

            discovery = await discover_restaurants_for_query(
                lat_bucket=lat_bucket,
                lng_bucket=lng_bucket,
                location=req.location,
                radius_miles=req.radius_miles,
                category=category,
            )
            restaurants: list[dict] = discovery.get("restaurants", [])

            restaurants.sort(key=lambda r: r.get("discovery_confidence", 0.5), reverse=True)

            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {len(restaurants)} restaurants. Analysing...'})}\n\n"

            first_batch = restaurants[:3]
            rest = restaurants[3:]

            if first_batch:
                first_results = await asyncio.gather(
                    *[_enrich_and_evaluate(r) for r in first_batch],
                    return_exceptions=True,
                )
                for result in first_results:
                    if isinstance(result, Exception):
                        continue
                    yield f"data: {json.dumps({'type': 'restaurant', 'data': result})}\n\n"

            yield f"data: {json.dumps({'type': 'first_batch_complete'})}\n\n"

            if rest:
                rest_results = await asyncio.gather(
                    *[_enrich_and_evaluate(r) for r in rest],
                    return_exceptions=True,
                )
                for result in rest_results:
                    if isinstance(result, Exception):
                        continue
                    yield f"data: {json.dumps({'type': 'restaurant', 'data': result})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'total_restaurants': len(restaurants)})}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "http://localhost:3000",
        },
    )


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Poll the progress of a discover job by its ID."""
    progress = await get_job_progress(job_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return progress


_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Access-Control-Allow-Origin": "http://localhost:3000",
}

_GEMINI_SYSTEM = (
    "You are Nourish.ai, a dietary safety assistant. "
    "Restaurants and dishes have been found and evaluated by our safety engine. "
    "The data is split into two groups: the TOP 5 SAFEST DISHES and the BOTTOM 5 MOST "
    "CONCERNING DISHES. Present both groups clearly. "
    "For each dish include its safety label (Compatible / Caution / High risk), "
    "score out of 100, and a plain-English explanation of why it is safe or unsafe "
    "for the user's conditions. "
    "Lead with the safest options, then clearly warn about the most concerning ones. "
    "Stick strictly to the data provided - do not add, invent, or guess any dish "
    "or restaurant not listed below."
)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _format_results_for_prompt(results: list[dict], condition_ids: list[str],
                                 location: str, radius_miles: float) -> str:
    lines = [
        f"\n\n=== EVALUATED RESULTS (near {location}, within {radius_miles} mi) ===",
        f"User conditions: {', '.join(condition_ids)}",
        "Scale: Compatible=safe | Caution=review ingredients | High risk=avoid | Unclear=insufficient data",
        "",
    ]

    def _render_group(items: list[dict]) -> list[str]:
        out: list[str] = []
        by_restaurant: dict[str, list[dict]] = {}
        for item in items:
            by_restaurant.setdefault(item.get("restaurant_name", "Unknown"), []).append(item)
        for rname, dishes in by_restaurant.items():
            out.append(f"Restaurant: {rname}")
            if dishes[0].get("restaurant_address"):
                out.append(f"  Address: {dishes[0]['restaurant_address']}")
            for dish in dishes:
                score = dish.get("score")
                conf  = dish.get("confidence")
                out.append(
                    f"  - {dish.get('item_name', '?')} "
                    f"[{dish.get('label','Unclear')}, "
                    f"score {score:.0f}/100, "
                    f"confidence {conf:.0%}]"
                    if (score is not None and conf is not None) else
                    f"  - {dish.get('item_name', '?')} [{dish.get('label','Unclear')}]"
                )
                if dish.get("short_explanation"):
                    out.append(f"    Reason: {dish['short_explanation']}")
            out.append("")
        return out

    # Split into tiers when tier field is present; otherwise treat all as "best"
    has_tiers = any("tier" in r for r in results)
    if has_tiers:
        best  = [r for r in results if r.get("tier") != "worst"]
        worst = [r for r in results if r.get("tier") == "worst"]
        lines.append("--- TOP 5 SAFEST DISHES ---")
        lines.extend(_render_group(best))
        if worst:
            lines.append("--- BOTTOM 5 MOST CONCERNING DISHES ---")
            lines.extend(_render_group(worst))
    else:
        lines.extend(_render_group(results))

    lines.append("=== END RESULTS ===")
    return "\n".join(lines)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    location: str
    radius_miles: float = 5.0
    conditions: list[str]
    allergies: list[str]


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Full pipeline chat endpoint.  SSE event types:
      {"type": "status",     "message": "..."}   - agent progress
      {"type": "restaurant", "data": {...}}       - one restaurant card ready
      {"type": "token",      "token":  "..."}    - Gemini text chunk
      [DONE]
    """
    condition_ids: list[str] = [
        CONDITION_LABEL_TO_ID.get(c, c.lower().replace(" ", "_"))
        for c in req.conditions
    ]
    condition_ids += [
        ALLERGY_LABEL_TO_ID.get(a, f"{a.lower().replace(' ', '_')}_allergy")
        for a in req.allergies
    ]

    last_user_text = req.messages[-1].content if req.messages else ""

    slug = req.location.lower().replace(",", "").replace(" ", "_")
    lat_bucket = slug[:24]
    lng_bucket  = slug[24:48] if len(slug) > 24 else "x"

    history: list[genai_types.Content] = [
        genai_types.Content(
            role="user" if m.role == "user" else "model",
            parts=[genai_types.Part(text=m.content)],
        )
        for m in req.messages[:-1]
    ]

    category = await parse_search_intent(last_user_text)

    _ENRICH_CONCURRENCY = 6

    async def event_stream():
        yield _sse({"type": "status", "message": f"Searching for {category} restaurants near {req.location}..."})
        try:
            discovery = await discover_restaurants_for_query(
                lat_bucket=lat_bucket,
                lng_bucket=lng_bucket,
                location=req.location,
                radius_miles=req.radius_miles,
                category=category,
            )
        except Exception as exc:
            yield _sse({"type": "status", "message": f"Discovery error: {exc}"})
            discovery = {"restaurants": []}

        restaurants: list[dict] = discovery.get("restaurants", [])
        restaurants.sort(key=lambda r: r.get("discovery_confidence", 0.5), reverse=True)

        yield _sse({"type": "status",
                    "message": f"Found {len(restaurants)} restaurant(s). Analysing menus..."})

        enriched: list[dict] = []
        sem = asyncio.Semaphore(_ENRICH_CONCURRENCY)

        async def _process(r: dict) -> dict:
            async with sem:
                try:
                    data = await enrich_restaurant(
                        restaurant_name=r["name"],
                        website_url=r.get("website_url"),
                        location_hint=req.location,
                    )
                except Exception:
                    data = {"restaurant_name": r["name"], "address": r.get("address", ""),
                            "website_url": r.get("website_url"), "menu_items": []}
            return data


        tasks = [asyncio.create_task(_process(r)) for r in restaurants]
        for coro in asyncio.as_completed(tasks):
            try:
                data = await coro
            except Exception:
                continue
            enriched.append(data)
            ranked = await rank_top_items_across_restaurants(
                enriched_restaurants=[data], condition_ids=condition_ids, top_n=5)
            yield _sse({"type": "restaurant", "data": {
                "restaurant_name": data.get("restaurant_name", ""),
                "restaurant_address": data.get("address", ""),
                "website_url": data.get("website_url"),
                "items": ranked,
            }})

        all_ranked = await rank_top_items_across_restaurants(
            enriched_restaurants=enriched, condition_ids=condition_ids, top_n=5, bottom_n=5)

        system_prompt = (
            _GEMINI_SYSTEM
            + _format_results_for_prompt(all_ranked, condition_ids, req.location, req.radius_miles)
        )

        yield _sse({"type": "status", "message": "Preparing your personalised results..."})

        
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def run_gemini():
            try:
                client = get_gemini_client()
                session = client.chats.create(
                    model="gemini-2.5-flash",
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.2,
                    ),
                    history=history,
                )
                for chunk in session.send_message_stream(last_user_text):
                    if chunk.text:
                        loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, json.dumps({"error": str(exc)}))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=run_gemini, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                yield "data: [DONE]\n\n"
                break
            if item.startswith('{"error":'):
                yield f"data: {item}\n\n"
                break
            yield _sse({"type": "token", "token": item})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)
