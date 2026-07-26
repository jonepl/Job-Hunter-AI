import type { ProfileIn, ProfileOut, SettingsOut, SettingsUpdate } from "../api/client";

// PUT /api/settings replaces every global field, so a panel that edits one field
// (voice, provider) must send the full current settings with its change. This drops
// the read-only parts (envDefaults, secrets) to the writable shape. Scheduling is
// per-profile now (per-profile-scheduling) — it is not a global setting.

/** Map the settings read model to the writable update shape. */
export function settingsToUpdate(s: SettingsOut): SettingsUpdate {
  return {
    evaluatorProvider: s.evaluatorProvider as SettingsUpdate["evaluatorProvider"],
    evaluatorModel: s.evaluatorModel,
    enrichmentMode: s.enrichmentMode as SettingsUpdate["enrichmentMode"],
    voice: s.voice,
  };
}

/** Whether the voice descriptor differs from its `.env` seed (UI indicator). */
export function voiceDiffersFromEnv(s: SettingsOut): boolean {
  const a = s.voice;
  const b = s.envDefaults.voice;
  return a.tone !== b.tone || a.person !== b.person || a.styleNotes !== b.styleNotes;
}

// A profile update (PUT /api/profiles/{id}) replaces every field, so an editor that
// changes one field must resend the rest. This maps the read model to the write shape.

/** Map a stored profile to the writable profile-input shape (drops the id). */
export function profileToInput(p: ProfileOut): ProfileIn {
  return {
    name: p.name,
    query: p.query,
    location: p.location,
    workTypes: p.workTypes,
    datePosted: p.datePosted,
    activeScrapers: p.activeScrapers,
    scoreThreshold: p.scoreThreshold,
    topResults: p.topResults,
    // Carry `enabled` through so an edit never silently resumes a paused profile.
    enabled: p.enabled,
    // Carry the per-profile schedule through so a non-schedule edit never wipes it.
    scheduleCron: p.scheduleCron,
    scheduleTimezone: p.scheduleTimezone,
    scheduleEnabled: p.scheduleEnabled,
  };
}
