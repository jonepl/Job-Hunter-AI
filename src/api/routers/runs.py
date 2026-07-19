"""Runs router — trigger a pipeline run from the browser (W8, ADR-026).

Exposes the "Run search now" control. A run is far too slow to block an HTTP request,
so ``POST /runs`` validates preconditions synchronously, creates a ``running`` record,
schedules the pipeline as a FastAPI background task, and returns the id immediately
(202); the client polls ``GET /runs/{id}`` via React Query until a terminal status,
then refetches the job list to see the new results.

Routes contain no business logic (ADR-026): they call the service and shape its
entities. The single-flight guard (one run at a time) and the summary aggregation
live in ``RunService``; the router only maps its errors to HTTP status codes.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from src.api.deps import get_run_service
from src.api.schemas import RunOut
from src.core.exceptions import NoProfilesError, RunInProgressError
from src.core.services.run_service import RunService

router = APIRouter(tags=["runs"])


@router.post("/runs", response_model=RunOut, status_code=202)
async def start_run(
    background_tasks: BackgroundTasks,
    service: RunService = Depends(get_run_service),
) -> RunOut:
    """Start a background pipeline run and return its ``running`` record.

    Preconditions (no run already in progress, at least one profile) are checked
    synchronously so a user-fixable problem is a clear 4xx rather than a silently
    failed background run.

    Args:
        background_tasks: FastAPI's post-response task runner.
        service: The shared RunService (injected).

    Returns:
        The ``running`` RunOut (poll it via ``GET /runs/{id}``).

    Raises:
        HTTPException: 409 when a run is already in progress; 400 when no search
            profiles are configured.
    """
    try:
        run = service.start_run()
    except RunInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except NoProfilesError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(service.execute_run, run.id)
    return RunOut.from_run(run)


@router.get("/runs", response_model=list[RunOut])
def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    service: RunService = Depends(get_run_service),
) -> list[RunOut]:
    """List recent runs, newest first (healing any run lost to a restart).

    Args:
        limit: Maximum number of runs to return (1–100).
        service: The shared RunService (injected).

    Returns:
        Up to ``limit`` runs as response models.
    """
    return [RunOut.from_run(run) for run in service.recent_runs(limit)]


@router.get("/runs/{run_id}", response_model=RunOut)
def poll_run(
    run_id: str,
    service: RunService = Depends(get_run_service),
) -> RunOut:
    """Return one run's current state, flipping a timed-out ``running`` row to failed.

    Args:
        run_id: The id returned by the start call.
        service: The shared RunService (injected).

    Returns:
        The run's current RunOut.

    Raises:
        HTTPException: 404 when no run has that id.
    """
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No run {run_id}")
    return RunOut.from_run(run)
