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

        Args:
            results: Ordered list of MatchResult entities.

        Returns:
            An HTML string suitable for email delivery.
        """
        rows = ""
        for i, result in enumerate(results, start=1):
            matched = ", ".join(result.matched_skills) or "—"
            missing = ", ".join(result.missing_skills) or "—"
            rows += f"""
            <tr>
                <td style="padding:8px;border:1px solid #ddd;">{i}</td>
                <td style="padding:8px;border:1px solid #ddd;">
                    <a href="{result.job.url}">{result.job.title}</a>
                </td>
                <td style="padding:8px;border:1px solid #ddd;">{result.job.company}</td>
                <td style="padding:8px;border:1px solid #ddd;">{result.job.location}</td>
                <td style="padding:8px;border:1px solid #ddd;text-align:center;">
                    <strong>{result.score}</strong>
                </td>
                <td style="padding:8px;border:1px solid #ddd;">{matched}</td>
                <td style="padding:8px;border:1px solid #ddd;">{missing}</td>
                <td style="padding:8px;border:1px solid #ddd;">{result.summary}</td>
            </tr>"""

        return f"""
        <html><body>
        <h2>Job Search Results</h2>
        <p>Found <strong>{len(results)}</strong> matching job(s).</p>
        <table style="border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:13px;">
            <thead style="background:#f2f2f2;">
                <tr>
                    <th style="padding:8px;border:1px solid #ddd;">#</th>
                    <th style="padding:8px;border:1px solid #ddd;">Title</th>
                    <th style="padding:8px;border:1px solid #ddd;">Company</th>
                    <th style="padding:8px;border:1px solid #ddd;">Location</th>
                    <th style="padding:8px;border:1px solid #ddd;">Score</th>
                    <th style="padding:8px;border:1px solid #ddd;">Matched Skills</th>
                    <th style="padding:8px;border:1px solid #ddd;">Missing Skills</th>
                    <th style="padding:8px;border:1px solid #ddd;">Summary</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        </body></html>"""
