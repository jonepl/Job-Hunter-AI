// Platforms are stored lowercase ("linkedin"). These give them their display
// casing for the card ("LinkedIn") and badges ("LINKEDIN").

const DISPLAY_NAMES: Record<string, string> = {
  linkedin: "LinkedIn",
  indeed: "Indeed",
  glassdoor: "Glassdoor",
  ziprecruiter: "ZipRecruiter",
};

/** Return a platform's display name, falling back to a capitalized form. */
export function platformName(platform: string): string {
  return DISPLAY_NAMES[platform] ?? platform.charAt(0).toUpperCase() + platform.slice(1);
}
