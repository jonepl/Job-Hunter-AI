"""DatePosted domain type — represents a recency filter for job listings."""

from enum import Enum


class DatePosted(Enum):
    """Recency filter for job listings.

    Controls how far back the app searches for job postings.
    Maps to platform-specific filter parameters.
    """

    DAY = "24h"
    DAYS3 = "3days"
    WEEK = "week"
    MONTH = "month"

    @classmethod
    def from_string(cls, value: str) -> "DatePosted":
        """Parse a string to a DatePosted value.

        Args:
            value: String representation of the date posted filter.
                   Case insensitive. Surrounding whitespace is stripped.

        Returns:
            The matching DatePosted enum member.

        Raises:
            ValueError: If the value is not a recognised date posted filter.
        """
        try:
            return cls(value.lower().strip())
        except ValueError:
            raise ValueError(
                f"Invalid date posted value: '{value}'. Supported values: 24h, 3days, week, month"
            )

    @property
    def linkedin_param(self) -> str:
        """Return the LinkedIn f_TPR query parameter value for this filter.

        Returns:
            The f_TPR value string to append to the LinkedIn search URL.
        """
        mapping = {
            DatePosted.DAY: "r86400",
            DatePosted.DAYS3: "r259200",
            DatePosted.WEEK: "r604800",
            DatePosted.MONTH: "r2592000",
        }
        return mapping[self]

    @property
    def jsearch_param(self) -> str:
        """Return the JSearch date_posted query parameter value for this filter.

        Returns:
            The date_posted value string to include in the JSearch API request.
        """
        mapping = {
            DatePosted.DAY: "today",
            DatePosted.DAYS3: "3days",
            DatePosted.WEEK: "week",
            DatePosted.MONTH: "month",
        }
        return mapping[self]
