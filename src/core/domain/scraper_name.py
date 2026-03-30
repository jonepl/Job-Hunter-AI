"""ScraperName domain enum — valid scraper identifiers."""

from enum import Enum


class ScraperName(str, Enum):
    """Enumeration of all supported job platform scrapers.

    Each value is the canonical lowercase string identifier used in
    ACTIVE_SCRAPERS env var and --scrapers CLI argument.
    """

    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    ZIPRECRUITER = "ziprecruiter"

    @classmethod
    def from_string(cls, value: str) -> "ScraperName":
        """Parse a string to a ScraperName. Case insensitive.

        Args:
            value: String to parse (e.g. "LinkedIn", "indeed").

        Returns:
            The matching ScraperName enum value.

        Raises:
            ValueError: If value does not match any supported scraper name.
        """
        try:
            return cls(value.lower().strip())
        except ValueError:
            raise ValueError(
                f"Invalid scraper name: '{value}'. "
                f"Supported values: linkedin, indeed, glassdoor, ziprecruiter"
            )

    @classmethod
    def parse_list(cls, value: str) -> list["ScraperName"]:
        """Parse a comma-separated string of scraper names.

        Args:
            value: Comma-separated scraper names
                   (e.g. "linkedin,indeed").

        Returns:
            List of ScraperName values in the order they appear.

        Raises:
            ValueError: If any name in the list is invalid.
        """
        names = [v.strip() for v in value.split(",") if v.strip()]
        return [cls.from_string(n) for n in names]

    @classmethod
    def all(cls) -> list["ScraperName"]:
        """Return all four ScraperName values.

        Returns:
            List of all ScraperName enum members.
        """
        return list(cls)
