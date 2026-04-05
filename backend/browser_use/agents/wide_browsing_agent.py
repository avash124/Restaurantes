import asyncio
import json
import logging

from backend.browser_use.agents.browser_use_client import get_browseruse_client
from backend.browser_use.agents.structured_schemas import WideDiscoveryOutput
from backend.browser_use import session_registry

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"finished", "failed", "stopped"}
_POLL_INTERVAL = 2.0
_POLL_TIMEOUT_SECONDS = 90.0


async def run_wide_discovery_agent(
    location: str,
    radius_miles: float,
    category: str,
) -> WideDiscoveryOutput:
    try:
        client = get_browseruse_client()
    except Exception as exc:
        logger.warning("[wide] browser-use client unavailable: %s", exc)
        return WideDiscoveryOutput(restaurants=[])

    # Narrow, focused prompt — listing discovery only, no menu pages.
    task = (
        f"Search for restaurants within {radius_miles} miles of {location} "
        f'that match the category "{category}". '
        "Return up to 15 results. "
        "For each restaurant collect ONLY: name, street address, homepage URL, "
        "cuisine type, and a discovery_confidence score (0.0–1.0) reflecting "
        "how well it matches the requested category. "
        "Do NOT open any restaurant website. "
        "Do NOT visit menu pages or browse food items. "
        "Only collect listing-level data visible on search-results pages."
    )

    schema_dict = WideDiscoveryOutput.model_json_schema()

    task_resp = await client.tasks.create(task, structured_output=json.dumps(schema_dict))
    task_id = str(task_resp.id)
    session_registry.register(task_id)
    task_result = None

    try:
        try:
            async with asyncio.timeout(_POLL_TIMEOUT_SECONDS):
                while True:
                    task_result = await client.tasks.get(task_id)
                    if task_result.status.value in _TERMINAL_STATUSES:
                        break
                    await asyncio.sleep(_POLL_INTERVAL)
        except TimeoutError:
            logger.warning("[wide] task %s timed out after %.1fs", task_id, _POLL_TIMEOUT_SECONDS)
            try:
                await client.tasks.stop(task_id)
            except Exception as stop_exc:
                logger.debug("[wide] could not stop timed out task %s: %s", task_id, stop_exc)
            return WideDiscoveryOutput(restaurants=[])

        if task_result is None or task_result.output is None:
            logger.warning("[wide] task %s finished with no output", task_id)
            return WideDiscoveryOutput(restaurants=[])

        try:
            output = task_result.output
            if isinstance(output, str):
                output = json.loads(output)
            return WideDiscoveryOutput.model_validate(output)
        except Exception as exc:
            logger.warning("[wide] schema validation failed for task %s: %s", task_id, exc)
            return WideDiscoveryOutput(restaurants=[])

    finally:
        session_registry.unregister(task_id)
