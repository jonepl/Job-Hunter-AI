"""Email output adapter — delivers results via Gmail SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.core.domain.match_result import MatchResult
from src.core.ports.output_port import OutputPort

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587

_BREAKDOWN_LABELS: list[tuple[str, str]] = [
    ("Role Alignment", "role_alignment"),
    ("Technical Stack Match", "technical_stack_match"),
    ("System Design & Architecture", "system_design_architecture"),
    ("Impact & Metrics", "impact_and_metrics"),
    ("Domain/Industry Experience", "domain_industry_experience"),
    ("Problem Space Relevance", "problem_space_relevance"),
    ("Ownership & Leadership", "ownership_and_leadership"),
    ("Resume Signal Quality", "resume_signal_quality"),
    ("Career Trajectory", "career_trajectory"),
]

_HIRE_COLORS: dict[str, str] = {
    "Strong Yes": "#1a7f37",
    "Yes": "#2da44e",
    "Borderline": "#e16b16",
    "No": "#cf222e",
}

_TD = 'style="padding:6px 10px;border:1px solid #ddd;vertical-align:top;"'
_TH = 'style="padding:6px 10px;border:1px solid #ddd;background:#f2f2f2;text-align:left;"'


class EmailOutput(OutputPort):
    """Delivers ranked job match results via Gmail SMTP."""

    def __init__(
        self,
        sender: str,
        password: str,
        recipient: str,
    ) -> None:
        """Initialise the email output adapter.

        Args:
            sender: Gmail address used as the SMTP sender.
            password: Gmail App Password for SMTP authentication.
            recipient: Email address to receive the results.
        """
        self._sender = sender
        self._password = password
        self._recipient = recipient

    async def deliver(self, results: list[MatchResult]) -> None:
        """Send ranked job match results as an HTML email.

        Args:
            results: Ordered list of MatchResult entities to include in the email.
        """
        if not results:
            logger.info("EmailOutput — no results to deliver")
            return

        subject = f"Job Search Results — {len(results)} Match(es) Found"
        html_body = self._build_html(results)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self._sender
        message["To"] = self._recipient
        message.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(self._sender, self._password)
                server.sendmail(self._sender, self._recipient, message.as_string())
            logger.info("EmailOutput — email sent to %s", self._recipient)
        except smtplib.SMTPAuthenticationError:
            logger.error("EmailOutput — SMTP authentication failed. Check GMAIL_APP_PASSWORD.")
        except smtplib.SMTPException as exc:
            logger.error("EmailOutput — SMTP error: %s", exc)
        except Exception as exc:
            logger.error("EmailOutput — unexpected error: %s", exc)

    def _build_html(self, results: list[MatchResult]) -> str:
        """Build an HTML email body from a list of match results.

        Each result is rendered as a card with score, hire recommendation,
        seniority, years of experience, a score breakdown table, matched
        and missing skills, summary, and a link to the job posting.

        Args:
            results: Ordered list of MatchResult entities.

        Returns:
            An HTML string suitable for email delivery.
        """
        cards = "".join(
            self._build_result_card(i, result) for i, result in enumerate(results, start=1)
        )

        return (
            "<html>"
            "<body style=\"font-family:Arial,sans-serif;font-size:13px;color:#333;"
            "max-width:900px;margin:0 auto;padding:16px;\">"
            f"<h2 style=\"color:#1a1a2e;\">Job Search Results</h2>"
            f"<p>Found <strong>{len(results)}</strong> matching job(s).</p>"
            f"{cards}"
            "</body></html>"
        )

    def _build_result_card(self, rank: int, result: MatchResult) -> str:
        """Build an HTML card for a single MatchResult.

        Args:
            rank: 1-based position of this result in the ranked list.
            result: The MatchResult to render.

        Returns:
            An HTML string representing the result card.
        """
        hire_color = _HIRE_COLORS.get(result.hire_recommendation, "#333")
        years = (
            f"{result.years_experience_detected} years"
            if result.years_experience_detected is not None
            else "Not detected"
        )
        matched = ", ".join(result.matched_skills) or "—"
        missing = ", ".join(result.missing_skills) or "—"

        breakdown_rows = self._build_breakdown_rows(result)

        return (
            "<div style=\"border:1px solid #d0d7de;border-radius:8px;padding:20px;"
            "margin-bottom:24px;background:#fff;\">"

            f"<h3 style=\"margin:0 0 4px;font-size:17px;\">"
            f"#{rank} — <a href=\"{result.job.url}\" style=\"color:#0969da;\">"
            f"{result.job.title}</a></h3>"

            f"<p style=\"margin:0 0 14px;color:#656d76;\">"
            f"{result.job.company} &nbsp;·&nbsp; {result.job.location}"
            f" &nbsp;·&nbsp; {result.job.platform}</p>"

            "<table style=\"border-collapse:collapse;margin-bottom:14px;\">"
            "<tr>"
            f"<td style=\"padding:3px 14px 3px 0;\"><strong>Overall Score</strong></td>"
            f"<td style=\"padding:3px 0;\"><strong style=\"font-size:18px;\">"
            f"{result.score}/100</strong></td>"
            "</tr><tr>"
            f"<td style=\"padding:3px 14px 3px 0;\"><strong>Hire Recommendation</strong></td>"
            f"<td style=\"padding:3px 0;\">"
            f"<strong style=\"color:{hire_color};\">{result.hire_recommendation}</strong></td>"
            "</tr><tr>"
            f"<td style=\"padding:3px 14px 3px 0;\"><strong>Seniority Level</strong></td>"
            f"<td style=\"padding:3px 0;\">{result.seniority_level}</td>"
            "</tr><tr>"
            f"<td style=\"padding:3px 14px 3px 0;\"><strong>Experience Detected</strong></td>"
            f"<td style=\"padding:3px 0;\">{years}</td>"
            "</tr>"
            "</table>"

            "<h4 style=\"margin:0 0 6px;\">Score Breakdown</h4>"
            "<table style=\"border-collapse:collapse;width:100%;font-size:12px;"
            "margin-bottom:14px;\">"
            "<thead><tr>"
            f"<th {_TH}>Category</th>"
            f"<th {_TH}>Max</th>"
            f"<th {_TH}>Earned</th>"
            f"<th {_TH}>Reasoning</th>"
            "</tr></thead>"
            f"<tbody>{breakdown_rows}</tbody>"
            "</table>"

            f"<p style=\"margin:6px 0;\"><strong>Matched Skills:</strong> {matched}</p>"
            f"<p style=\"margin:6px 0;\"><strong>Missing Skills:</strong> {missing}</p>"
            f"<p style=\"margin:6px 0;\"><strong>Summary:</strong> {result.summary}</p>"
            f"<p style=\"margin:10px 0 0;\">"
            f"<a href=\"{result.job.url}\" style=\"color:#0969da;\">View Job Posting →</a></p>"

            "</div>"
        )

    def _build_breakdown_rows(self, result: MatchResult) -> str:
        """Build HTML table rows for the score breakdown categories.

        Args:
            result: The MatchResult whose score_breakdown to render.

        Returns:
            An HTML string of <tr> elements, one per scoring category.
        """
        rows = ""
        for label, field in _BREAKDOWN_LABELS:
            cat = getattr(result.score_breakdown, field)
            rows += (
                f"<tr>"
                f"<td {_TD}>{label}</td>"
                f"<td {_TD} style=\"text-align:center;\">{cat.max}</td>"
                f"<td {_TD} style=\"text-align:center;\">{cat.earned}</td>"
                f"<td {_TD}>{cat.reasoning}</td>"
                f"</tr>"
            )
        return rows
