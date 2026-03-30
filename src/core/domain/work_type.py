"""WorkType — domain entity representing job work arrangement types."""

import enum


class WorkType(enum.Enum):
    """Valid work arrangement types for job search filtering."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"

    @staticmethod
    def to_linkedin_param(work_types: "list[WorkType]") -> str:
        """Return the LinkedIn f_WT URL parameter string for the given work types.

        LinkedIn work type codes:
            remote → f_WT=2
            hybrid → f_WT=3
            onsite → f_WT=1

        Multiple types produce multiple f_WT parameters, e.g. remote + hybrid
        yields ``&f_WT=2&f_WT=3``.

        Args:
            work_types: List of WorkType values to filter by. Empty list returns
                        an empty string (no filter applied).

        Returns:
            A URL parameter fragment such as ``&f_WT=2`` or ``&f_WT=2&f_WT=3``,
            or empty string when work_types is empty.
        """
        _linkedin_codes: dict[WorkType, str] = {
            WorkType.REMOTE: "2",
            WorkType.HYBRID: "3",
            WorkType.ONSITE: "1",
        }
        if not work_types:
            return ""
        return "".join(f"&f_WT={_linkedin_codes[wt]}" for wt in work_types)
