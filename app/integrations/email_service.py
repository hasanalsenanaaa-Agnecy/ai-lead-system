"""
Email Notification Service
Sends email alerts for escalations, hot leads, and reports
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class EmailService:
    """
    Email notification service.
    
    Supports:
    - SendGrid API (preferred)
    - SMTP fallback
    
    Features:
    - Hot lead alerts
    - Escalation notifications
    - Daily/weekly reports
    - Custom templates
    """

    def __init__(self):
        self.sendgrid_api_key = settings.sendgrid_api_key
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.email_from_address or "noreply@aileads.local"
        self.from_name = settings.email_from_name or "AI Lead System"

    # =========================================================================
    # Core Send Methods
    # =========================================================================

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        body_html: str,
        body_text: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        reply_to: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Send an email.
        
        Args:
            to: Recipient email(s)
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional, extracted from HTML if not provided)
            from_email: Sender email
            from_name: Sender name
            reply_to: Reply-to address
            cc: CC recipients
            bcc: BCC recipients
            
        Returns:
            Send result
        """
        # Normalize recipients
        if isinstance(to, str):
            to = [to]
        
        from_email = from_email or self.from_email
        from_name = from_name or self.from_name
        
        # Generate plain text if not provided
        if not body_text:
            body_text = self._html_to_text(body_html)

        # Try SendGrid first, fall back to SMTP
        if self.sendgrid_api_key:
            return await self._send_via_sendgrid(
                to=to,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                from_email=from_email,
                from_name=from_name,
                reply_to=reply_to,
                cc=cc,
                bcc=bcc,
            )
        elif self.smtp_host:
            return await self._send_via_smtp(
                to=to,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                from_email=from_email,
                from_name=from_name,
                reply_to=reply_to,
                cc=cc,
                bcc=bcc,
            )
        else:
            logger.warning("No email provider configured, skipping send")
            return {"status": "skipped", "reason": "not_configured"}

    # =========================================================================
    # Alert Templates
    # =========================================================================

    async def send_hot_lead_alert(
        self,
        to: str | list[str],
        lead_name: str,
        lead_phone: str | None = None,
        lead_email: str | None = None,
        service_interest: str | None = None,
        urgency: str | None = None,
        summary: str | None = None,
        conversation_link: str | None = None,
    ) -> dict[str, Any]:
        """
        Send hot lead alert email.
        
        Args:
            to: Recipient(s)
            lead_name: Lead's name
            lead_phone: Lead's phone
            lead_email: Lead's email
            service_interest: What they're interested in
            urgency: Urgency level
            summary: AI conversation summary
            conversation_link: Link to view conversation
            
        Returns:
            Send result
        """
        subject = f"🔥 HOT LEAD: {lead_name}"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #ff4444; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">🔥 Hot Lead Alert</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9;">
                <h2 style="color: #333; margin-top: 0;">New Hot Lead Requires Immediate Attention</h2>
                
                <div style="background-color: white; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                    <h3 style="color: #ff4444; margin-top: 0;">Contact Information</h3>
                    <p><strong>Name:</strong> {lead_name}</p>
                    {f'<p><strong>Phone:</strong> <a href="tel:{lead_phone}">{lead_phone}</a></p>' if lead_phone else ''}
                    {f'<p><strong>Email:</strong> <a href="mailto:{lead_email}">{lead_email}</a></p>' if lead_email else ''}
                </div>
                
                <div style="background-color: white; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                    <h3 style="color: #333; margin-top: 0;">Lead Details</h3>
                    {f'<p><strong>Service Interest:</strong> {service_interest}</p>' if service_interest else ''}
                    {f'<p><strong>Urgency:</strong> {urgency}</p>' if urgency else ''}
                    {f'<p><strong>Summary:</strong> {summary}</p>' if summary else ''}
                </div>
                
                {f'''
                <div style="text-align: center; margin-top: 20px;">
                    <a href="{conversation_link}" style="background-color: #ff4444; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Full Conversation →
                    </a>
                </div>
                ''' if conversation_link else ''}
            </div>
            
            <div style="padding: 15px; background-color: #333; color: white; text-align: center; font-size: 12px;">
                <p style="margin: 0;">This is an automated alert from your AI Lead System</p>
            </div>
        </div>
        """
        
        return await self.send_email(to=to, subject=subject, body_html=html)

    async def send_escalation_alert(
        self,
        to: str | list[str],
        lead_name: str,
        escalation_reason: str,
        lead_phone: str | None = None,
        lead_email: str | None = None,
        conversation_snippet: str | None = None,
        conversation_link: str | None = None,
    ) -> dict[str, Any]:
        """
        Send escalation notification.
        
        Args:
            to: Recipient(s)
            lead_name: Lead's name
            escalation_reason: Why it was escalated
            lead_phone: Lead's phone
            lead_email: Lead's email
            conversation_snippet: Recent conversation
            conversation_link: Link to full conversation
            
        Returns:
            Send result
        """
        subject = f"⚠️ Escalation: {lead_name} - {escalation_reason}"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #ff9800; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">⚠️ Human Assistance Required</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9;">
                <h2 style="color: #333; margin-top: 0;">Conversation Escalated</h2>
                
                <div style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin-bottom: 20px;">
                    <p style="margin: 0;"><strong>Reason:</strong> {escalation_reason}</p>
                </div>
                
                <div style="background-color: white; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                    <h3 style="color: #333; margin-top: 0;">Contact</h3>
                    <p><strong>Name:</strong> {lead_name}</p>
                    {f'<p><strong>Phone:</strong> <a href="tel:{lead_phone}">{lead_phone}</a></p>' if lead_phone else ''}
                    {f'<p><strong>Email:</strong> <a href="mailto:{lead_email}">{lead_email}</a></p>' if lead_email else ''}
                </div>
                
                {f'''
                <div style="background-color: white; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                    <h3 style="color: #333; margin-top: 0;">Recent Conversation</h3>
                    <pre style="white-space: pre-wrap; font-family: inherit; margin: 0;">{conversation_snippet}</pre>
                </div>
                ''' if conversation_snippet else ''}
                
                {f'''
                <div style="text-align: center; margin-top: 20px;">
                    <a href="{conversation_link}" style="background-color: #ff9800; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Take Over Conversation →
                    </a>
                </div>
                ''' if conversation_link else ''}
            </div>
            
            <div style="padding: 15px; background-color: #333; color: white; text-align: center; font-size: 12px;">
                <p style="margin: 0;">Automated escalation from AI Lead System</p>
            </div>
        </div>
        """
        
        return await self.send_email(to=to, subject=subject, body_html=html)

    async def send_appointment_confirmation(
        self,
        to: str,
        lead_name: str,
        appointment_time: str,
        service: str | None = None,
        location: str | None = None,
        notes: str | None = None,
        calendar_link: str | None = None,
    ) -> dict[str, Any]:
        """
        Send appointment confirmation to lead.
        
        Args:
            to: Lead's email
            lead_name: Lead's name
            appointment_time: Formatted appointment time
            service: Service type
            location: Meeting location/details
            notes: Additional notes
            calendar_link: Add to calendar link
            
        Returns:
            Send result
        """
        subject = f"Your Appointment is Confirmed - {appointment_time}"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #4caf50; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">✓ Appointment Confirmed</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9;">
                <p>Hi {lead_name},</p>
                
                <p>Your appointment has been confirmed!</p>
                
                <div style="background-color: white; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <h3 style="color: #4caf50; margin-top: 0;">📅 Appointment Details</h3>
                    <p><strong>When:</strong> {appointment_time}</p>
                    {f'<p><strong>Service:</strong> {service}</p>' if service else ''}
                    {f'<p><strong>Location:</strong> {location}</p>' if location else ''}
                    {f'<p><strong>Notes:</strong> {notes}</p>' if notes else ''}
                </div>
                
                {f'''
                <div style="text-align: center; margin-top: 20px;">
                    <a href="{calendar_link}" style="background-color: #4caf50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Add to Calendar
                    </a>
                </div>
                ''' if calendar_link else ''}
                
                <p style="margin-top: 20px;">If you need to reschedule or cancel, please let us know as soon as possible.</p>
                
                <p>We look forward to speaking with you!</p>
            </div>
            
            <div style="padding: 15px; background-color: #333; color: white; text-align: center; font-size: 12px;">
                <p style="margin: 0;">This is an automated confirmation.</p>
            </div>
        </div>
        """
        
        return await self.send_email(to=to, subject=subject, body_html=html)

    async def send_daily_summary(
        self,
        to: str | list[str],
        client_name: str,
        date: str,
        total_leads: int,
        hot_leads: int,
        appointments_booked: int,
        conversations_handled: int,
        escalations: int,
        avg_response_time: str | None = None,
        top_interests: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Send daily performance summary.
        
        Args:
            to: Recipient(s)
            client_name: Client business name
            date: Report date
            total_leads: Total leads received
            hot_leads: Hot leads identified
            appointments_booked: Appointments booked
            conversations_handled: Total conversations
            escalations: Number of escalations
            avg_response_time: Average response time
            top_interests: Top service interests
            
        Returns:
            Send result
        """
        subject = f"📊 Daily Summary for {client_name} - {date}"
        
        interests_html = ""
        if top_interests:
            interests_html = "<ul>" + "".join(f"<li>{i}</li>" for i in top_interests[:5]) + "</ul>"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #2196f3; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">📊 Daily Performance Summary</h1>
                <p style="margin: 5px 0 0;">{date}</p>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9;">
                <h2 style="color: #333; margin-top: 0;">{client_name}</h2>
                
                <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 20px;">
                    <div style="flex: 1; min-width: 120px; background: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #2196f3;">{total_leads}</div>
                        <div style="color: #666;">Total Leads</div>
                    </div>
                    <div style="flex: 1; min-width: 120px; background: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #ff4444;">{hot_leads}</div>
                        <div style="color: #666;">Hot Leads</div>
                    </div>
                    <div style="flex: 1; min-width: 120px; background: white; padding: 20px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #4caf50;">{appointments_booked}</div>
                        <div style="color: #666;">Appointments</div>
                    </div>
                </div>
                
                <div style="background-color: white; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                    <h3 style="margin-top: 0;">Performance Metrics</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;">Conversations Handled</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{conversations_handled}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;">Escalations</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{escalations}</td>
                        </tr>
                        {f'''
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;">Avg Response Time</td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right; font-weight: bold;">{avg_response_time}</td>
                        </tr>
                        ''' if avg_response_time else ''}
                    </table>
                </div>
                
                {f'''
                <div style="background-color: white; border-radius: 8px; padding: 20px;">
                    <h3 style="margin-top: 0;">Top Service Interests</h3>
                    {interests_html}
                </div>
                ''' if interests_html else ''}
            </div>
            
            <div style="padding: 15px; background-color: #333; color: white; text-align: center; font-size: 12px;">
                <p style="margin: 0;">AI Lead System Daily Report</p>
            </div>
        </div>
        """
        
        return await self.send_email(to=to, subject=subject, body_html=html)

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _send_via_sendgrid(
        self,
        to: list[str],
        subject: str,
        body_html: str,
        body_text: str,
        from_email: str,
        from_name: str,
        reply_to: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send email via SendGrid API."""
        personalizations = [{
            "to": [{"email": email} for email in to],
        }]
        
        if cc:
            personalizations[0]["cc"] = [{"email": email} for email in cc]
        if bcc:
            personalizations[0]["bcc"] = [{"email": email} for email in bcc]

        payload = {
            "personalizations": personalizations,
            "from": {"email": from_email, "name": from_name},
            "subject": subject,
            "content": [
                {"type": "text/plain", "value": body_text},
                {"type": "text/html", "value": body_html},
            ],
        }
        
        if reply_to:
            payload["reply_to"] = {"email": reply_to}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {self.sendgrid_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                
                if response.status_code >= 400:
                    logger.error(
                        "SendGrid error",
                        status=response.status_code,
                        response=response.text,
                    )
                    response.raise_for_status()
                
                logger.info(
                    "Email sent via SendGrid",
                    to=to,
                    subject=subject[:50],
                )
                
                return {"status": "sent", "provider": "sendgrid"}
                
        except Exception as e:
            logger.error("SendGrid send failed", error=str(e))
            raise

    async def _send_via_smtp(
        self,
        to: list[str],
        subject: str,
        body_html: str,
        body_text: str,
        from_email: str,
        from_name: str,
        reply_to: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = ", ".join(to)
        
        if cc:
            msg["Cc"] = ", ".join(cc)
        if reply_to:
            msg["Reply-To"] = reply_to

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        all_recipients = to + (cc or []) + (bcc or [])

        try:
            # Use run_in_executor for sync SMTP
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._smtp_send_sync,
                msg,
                all_recipients,
            )
            
            logger.info(
                "Email sent via SMTP",
                to=to,
                subject=subject[:50],
            )
            
            return {"status": "sent", "provider": "smtp"}
            
        except Exception as e:
            logger.error("SMTP send failed", error=str(e))
            raise

    def _smtp_send_sync(
        self,
        msg: MIMEMultipart,
        recipients: list[str],
    ) -> None:
        """Synchronous SMTP send."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_user and self.smtp_password:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg, to_addrs=recipients)

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple version)."""
        import re
        
        # Remove style and script tags
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Replace common tags
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<div[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '• ', text, flags=re.IGNORECASE)
        
        # Remove remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        
        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text


# Singleton instance
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get singleton email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
