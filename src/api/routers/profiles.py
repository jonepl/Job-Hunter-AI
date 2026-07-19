"""Profiles router — search-profile CRUD over the browser (W7, ADR-031).

The search definitions the run pipeline iterates, editable from the Settings screen.
Routes contain no business logic (ADR-026): they map request/response shapes and call
``SettingsService``. Deleting the last remaining profile is refused (409) so a run
never has nothing to do.
"""

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_settings_service
from src.api.schemas import ProfileIn, ProfileOut
from src.core.services.settings_service import SettingsService

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileOut])
def list_profiles(
    service: SettingsService = Depends(get_settings_service),
) -> list[ProfileOut]:
    """List every stored search profile, ordered by position."""
    return [ProfileOut.from_profile(p) for p in service.list_profiles()]


@router.post("", response_model=ProfileOut, status_code=201)
def create_profile(
    body: ProfileIn,
    service: SettingsService = Depends(get_settings_service),
) -> ProfileOut:
    """Create a new search profile.

    Raises:
        HTTPException: 400 on an invalid location/work-type combination or enum value.
    """
    profile = service.create_profile(_to_profile_or_400(body))
    return ProfileOut.from_profile(profile)


@router.put("/{profile_id}", response_model=ProfileOut)
def update_profile(
    profile_id: int,
    body: ProfileIn,
    service: SettingsService = Depends(get_settings_service),
) -> ProfileOut:
    """Update an existing search profile.

    Raises:
        HTTPException: 404 when the profile does not exist; 400 on invalid input.
    """
    if service.get_profile(profile_id) is None:
        raise HTTPException(status_code=404, detail=f"No profile {profile_id}")
    profile = service.update_profile(_to_profile_or_400(body, profile_id))
    return ProfileOut.from_profile(profile)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(
    profile_id: int,
    service: SettingsService = Depends(get_settings_service),
) -> None:
    """Delete a search profile.

    Raises:
        HTTPException: 404 when the profile does not exist; 409 when it is the last
            remaining profile (a run must always have something to do).
    """
    if service.get_profile(profile_id) is None:
        raise HTTPException(status_code=404, detail=f"No profile {profile_id}")
    if service.profile_count() <= 1:
        raise HTTPException(
            status_code=409, detail="Cannot delete the last remaining profile."
        )
    service.delete_profile(profile_id)


def _to_profile_or_400(body: ProfileIn, profile_id: int = 0):
    """Map the request to a SearchProfile, turning a validation error into a 400."""
    try:
        return body.to_profile(profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
