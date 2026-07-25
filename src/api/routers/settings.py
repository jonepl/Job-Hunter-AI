"""Settings router — the global config + secrets over the browser (W7, ADR-031).

Exposes the DB-backed settings layer to the SPA. Routes contain no business logic
(ADR-026): they call ``SettingsService`` and shape its entities. **No route returns a
secret value** — only masked status (a last-4 suffix + configured/overridden flags).
The cron preview computes fire times without touching any live scheduler.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_settings_service
from src.api.schemas import (
    SchedulePreview,
    SecretStatus,
    SecretUpdate,
    SettingsOut,
    SettingsUpdate,
)
from src.core.services.settings_service import SECRET_NAMES, SettingsService
from src.orchestration.scheduler import get_scheduler_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(
    service: SettingsService = Depends(get_settings_service),
) -> SettingsOut:
    """Return the global settings, the ``.env`` defaults, and masked secret status."""
    return SettingsOut.build(
        service.get_settings(),
        service.env_defaults(),
        service.all_secret_statuses(),
    )


@router.put("", response_model=SettingsOut)
def update_settings(
    body: SettingsUpdate,
    service: SettingsService = Depends(get_settings_service),
) -> SettingsOut:
    """Persist the editable global settings (provider allowlist enforced by the schema).

    When the in-process scheduler is running, a saved cron/timezone reschedules it live
    by a direct method call (ADR-032) — no restart. An invalid cron never fails the save
    (the preview endpoint is where cron is validated); it is logged and left unscheduled.
    """
    service.update_settings(body.to_settings())
    manager = get_scheduler_manager()
    if manager is not None and manager.running:
        current = service.get_settings()
        try:
            manager.reschedule(current.schedule_cron, current.schedule_timezone)
        except ValueError as exc:
            logger.warning("Kept saved settings but could not reschedule: %s", exc)
    return SettingsOut.build(
        service.get_settings(),
        service.env_defaults(),
        service.all_secret_statuses(),
    )


@router.put("/secrets/{name}", response_model=SecretStatus)
def set_secret(
    name: str,
    body: SecretUpdate,
    service: SettingsService = Depends(get_settings_service),
) -> SecretStatus:
    """Replace a secret (write-only). The value is stored, never returned.

    Raises:
        HTTPException: 404 for an unknown secret name.
    """
    _known_secret_or_404(name)
    service.set_secret(name, body.value)
    return SecretStatus(**service.secret_status(name))


@router.delete("/secrets/{name}", response_model=SecretStatus)
def clear_secret(
    name: str,
    service: SettingsService = Depends(get_settings_service),
) -> SecretStatus:
    """Clear a secret's DB override, reverting to the ``.env`` value.

    Raises:
        HTTPException: 404 for an unknown secret name.
    """
    _known_secret_or_404(name)
    service.clear_secret(name)
    return SecretStatus(**service.secret_status(name))


@router.get("/schedule/preview", response_model=SchedulePreview)
def schedule_preview(
    cron: str = Query(...),
    timezone: str = Query("UTC"),
    service: SettingsService = Depends(get_settings_service),
) -> SchedulePreview:
    """Return the next 3 fire times for a cron expression (no live scheduler).

    Raises:
        HTTPException: 400 for an invalid cron expression or timezone.
    """
    try:
        return SchedulePreview(next_runs=service.next_run_times(cron, timezone, n=3))
    except Exception as exc:  # noqa: BLE001 — bad user input, not a server fault
        raise HTTPException(status_code=400, detail=f"Invalid schedule: {exc}") from exc


def _known_secret_or_404(name: str) -> None:
    """Reject an unknown secret name with a 404."""
    if name not in SECRET_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown secret {name!r}")
