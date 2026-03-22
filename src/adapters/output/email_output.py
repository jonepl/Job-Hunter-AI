"""Email output adapter — delivers results via Gmail SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.core.domain.run_report import RunReport
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
    """Delivers a run report via Gmail SMTP. Always sends — even on zero results."""

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

    async def deliver(self, report: RunReport) -> None:
        """Send a run report as an HTML email.

        Always sends regardless of whether qualifying results exist. When zero
        qualifying results are found the email includes the top near-miss jobs
        and a suggestion for lowering the score threshold.

        Args:
            report: RunReport produced by the pipeline this run.
        """
        if report.has_qualifying_results:
            subject = (
                f"Job Search Results — {len(report.qualifying_results)} matches found"
                f" [{report.query} | {report.location}]"
            )
        else:
            subject = (
                f"Job Search Results — 0 matches above threshold ({report.score_threshold})"
                f" [{report.query} | {report.location}]"
            )

        html_body = self._build_html(report)

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

            if report.has_qualifying_results:
                logger.info(
                    "EmailOutput — email sent to %s — %d qualifying results",
                    self._recipient,
                    len(report.qualifying_results),
                )
            else:
                logger.info(
                    "EmailOutput — zero results report sent to %s — %d near-misses included",
                    self._recipient,
                    len(report.near_miss_results),
                )
        except smtplib.SMTPAuthenticationError:
            logger.error("EmailOutput — SMTP authentication failed. Check GMAIL_APP_PASSWORD.")
        except smtplib.SMTPException as exc:
            logger.error("EmailOutput — SMTP error: %s", exc)
        except Exception as exc:
            logger.error("EmailOutput — unexpected error: %s", exc)

    def _build_html(self, report: RunReport) -> str:
        """Build the full HTML email body from a RunReport.

        Args:
            report: The RunReport to render.

        Returns:
            An HTML string suitable for email delivery.
        """
        top_results_label = str(report.top_results) if report.top_results is not None else "not set"
        run_at_str = report.run_at.strftime("%Y-%m-%d %H:%M:%S")

        if report.has_qualifying_results:
            return self._build_qualifying_html(report, top_results_label, run_at_str)
        return self._build_zero_results_html(report, top_results_label, run_at_str)

    def _build_qualifying_html(
        self, report: RunReport, top_results_label: str, run_at_str: str
    ) -> str:
        """Build HTML body for a run with qualifying results.

        Args:
            report: The RunReport to render.
            top_results_label: Display string for the top results cap setting.
            run_at_str: Formatted run timestamp string.

        Returns:
            An HTML string for the qualifying results email.
        """
        cards = "".join(
            self._build_result_card(i, result)
            for i, result in enumerate(report.qualifying_results, start=1)
        )

        return (
            "<html>"
            "<body style=\"font-family:Arial,sans-serif;font-size:13px;color:#333;"
            "max-width:900px;margin:0 auto;padding:16px;\">"
            "<h2 style=\"color:#1a1a2e;\">Job Search Results</h2>"
            "<table style=\"margin-bottom:16px;\">"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Query</strong></td>"
            f"<td>{report.query}</td></tr>"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Location</strong></td>"
            f"<td>{report.location}</td></tr>"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Run at</strong></td>"
            f"<td>{run_at_str}</td></tr>"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Score threshold</strong></td>"
            f"<td>{report.score_threshold}</td></tr>"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Top results cap</strong></td>"
            f"<td>{top_results_label}</td></tr>"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Matches found</strong></td>"
            f"<td><strong>{len(report.qualifying_results)}</strong></td></tr>"
            "</table>"
            f"{cards}"
            f"<p style=\"color:#666;font-size:12px;\">Total jobs evaluated: "
            f"{report.total_evaluated}</p>"
            "</body></html>"
        )

    def _build_zero_results_html(
        self, report: RunReport, top_results_label: str, run_at_str: str
    ) -> str:
        """Build HTML body for a zero-results run.

        Args:
            report: The RunReport to render.
            top_results_label: Display string for the top results cap setting.
            run_at_str: Formatted run timestamp string.

        Returns:
            An HTML string for the zero results email.
        """
        near_miss_section = ""
        if report.near_miss_results:
            near_miss_cards = "".join(
                self._build_near_miss_card(i, result)
                for i, result in enumerate(report.near_miss_results, start=1)
            )
            near_miss_section = (
                "<h3 style=\"color:#1a1a2e;margin-top:24px;\">Top Near-Miss Results</h3>"
                "<p style=\"color:#656d76;font-style:italic;\">"
                "Scored below threshold — shown for reference only</p>"
                f"{near_miss_cards}"
            )

        suggestion_block = ""
        if report.near_miss_results and report.suggested_threshold is not None:
            suggestion_block = (
                f"<p>Suggestion: Consider lowering "
                f"<strong>SCORE_THRESHOLD</strong> to "
                f"<strong>{report.suggested_threshold}</strong> "
                f"in your .env file to capture more matches.</p>"
            )

        return (
            "<html>"
            "<body style=\"font-family:Arial,sans-serif;font-size:13px;color:#333;"
            "max-width:900px;margin:0 auto;padding:16px;\">"
            "<h2 style=\"color:#1a1a2e;\">Job Search Results — No Matches Found</h2>"
            "<table style=\"margin-bottom:16px;\">"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Query</strong></td>"
            f"<td>{report.query}</td></tr>"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Location</strong></td>"
            f"<td>{report.location}</td></tr>"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Run at</strong></td>"
            f"<td>{run_at_str}</td></tr>"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Score threshold</strong></td>"
            f"<td>{report.score_threshold}</td></tr>"
            f"<tr><td style=\"padding:2px 12px 2px 0;\"><strong>Jobs evaluated</strong></td>"
            f"<td>{report.total_evaluated}</td></tr>"
            "</table>"
            "<div style=\"background:#fff8e1;border:1px solid #f9c74f;border-radius:6px;"
            "padding:16px;margin-bottom:20px;\">"
            f"<p style=\"margin:0 0 8px;\"><strong>No jobs met your score threshold of "
            f"{report.score_threshold} this run.</strong></p>"
            f"{suggestion_block}"
            "</div>"
            f"{near_miss_section}"
            "<p style=\"color:#666;font-size:12px;margin-top:24px;\">"
            f"Total jobs evaluated: {report.total_evaluated} &nbsp;·&nbsp; "
            f"Score threshold: {report.score_threshold} &nbsp;·&nbsp; "
            f"Top results cap: {top_results_label}</p>"
            "</body></html>"
        )

    def _build_result_card(self, rank: int, result) -> str:
        """Build an HTML card for a single qualifying MatchResult.

        Args:
            rank: 1-based position of this result in the ranked list.
            result: The MatchResult to render.

        Returns:
            An HTML string representing the result card with full score breakdown.
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

    def _build_near_miss_card(self, rank: int, result) -> str:
        """Build a condensed HTML card for a near-miss MatchResult.

        Near-miss cards show key info only — no score breakdown table.

        Args:
            rank: 1-based position in the near-miss list.
            result: The MatchResult to render.

        Returns:
            An HTML string representing the condensed near-miss card.
        """
        hire_color = _HIRE_COLORS.get(result.hire_recommendation, "#333")
        matched = ", ".join(result.matched_skills) or "—"
        missing = ", ".join(result.missing_skills) or "—"

        return (
            "<div style=\"border:1px solid #e1e4e8;border-radius:8px;padding:16px;"
            "margin-bottom:16px;background:#fafafa;\">"

            f"<h4 style=\"margin:0 0 4px;font-size:15px;\">"
            f"#{rank} — <a href=\"{result.job.url}\" style=\"color:#0969da;\">"
            f"{result.job.title}</a></h4>"

            f"<p style=\"margin:0 0 10px;color:#656d76;font-size:12px;\">"
            f"{result.job.company} &nbsp;·&nbsp; {result.job.location}"
            f" &nbsp;·&nbsp; {result.job.platform}</p>"

            f"<p style=\"margin:4px 0;\"><strong>Score:</strong> {result.score}/100"
            f" &nbsp;·&nbsp; "
            f"<strong style=\"color:{hire_color};\">{result.hire_recommendation}</strong></p>"

            f"<p style=\"margin:4px 0;\"><strong>Matched Skills:</strong> {matched}</p>"
            f"<p style=\"margin:4px 0;\"><strong>Missing Skills:</strong> {missing}</p>"
            f"<p style=\"margin:4px 0;\"><strong>Summary:</strong> {result.summary}</p>"
            f"<p style=\"margin:8px 0 0;\">"
            f"<a href=\"{result.job.url}\" style=\"color:#0969da;\">View Job Posting →</a></p>"

            "</div>"
        )

    def _build_breakdown_rows(self, result) -> str:
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
