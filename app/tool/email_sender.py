import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from app.config import config
from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class EmailConfig(BaseModel):
    """Email configuration settings."""
    smtp_server: str = Field(description="SMTP server address")
    smtp_port: int = Field(description="SMTP server port")
    smtp_username: str = Field(description="SMTP username/email")
    smtp_password: str = Field(description="SMTP password")
    use_tls: bool = Field(default=True, description="Whether to use TLS")


class EmailResult(ToolResult):
    """Result of an email sending operation."""
    recipient: str = Field(description="Email recipient")
    subject: str = Field(description="Email subject")
    message_sent: bool = Field(description="Whether the message was sent successfully")
    
    @model_validator(mode="after")
    def populate_output(self) -> "EmailResult":
        """Populate the output field based on the email result."""
        if self.error:
            return self
            
        status = "successfully" if self.message_sent else "failed to be"
        self.output = f"Email to {self.recipient} with subject '{self.subject}' was {status} sent."
        return self


class EmailSender(BaseTool):
    """Tool for sending emails to specified recipients."""
    
    name: str = "email_sender"
    description: str = """Send an email to a specified recipient with a custom subject and message.
    This tool allows agents to send emails as part of their workflow.
    Email configuration must be set up in the application config."""
    parameters: dict = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "(required) Email address of the recipient.",
            },
            "subject": {
                "type": "string",
                "description": "(required) Subject line of the email.",
            },
            "body": {
                "type": "string",
                "description": "(required) Content of the email. Can be plain text or HTML.",
            },
            "cc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "(optional) CC recipients email addresses.",
            },
            "bcc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "(optional) BCC recipients email addresses.",
            },
            "is_html": {
                "type": "boolean",
                "description": "(optional) Whether the body is HTML. Default is false.",
                "default": False,
            },
        },
        "required": ["to", "subject", "body"],
    }
    
    async def execute(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        is_html: bool = False,
    ) -> EmailResult:
        """
        Send an email to the specified recipient.
        
        Args:
            to: Email address of the recipient
            subject: Subject line of the email
            body: Content of the email
            cc: Optional list of CC recipients
            bcc: Optional list of BCC recipients
            is_html: Whether the body is HTML
            
        Returns:
            EmailResult containing the status of the email sending operation
        """
        # Get email configuration from app config
        email_config = self._get_email_config()
        if not email_config:
            return EmailResult(
                recipient=to,
                subject=subject,
                message_sent=False,
                error="Email configuration is missing or incomplete in app config."
            )
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = email_config.smtp_username
        msg['To'] = to
        msg['Subject'] = subject
        
        # Add CC if provided
        if cc:
            msg['Cc'] = ", ".join(cc)
            
        # Set email content
        content_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, content_type))
        
        # Prepare recipient list (including CC and BCC)
        recipients = [to]
        if cc:
            recipients.extend(cc)
        if bcc:
            recipients.extend(bcc)
            
        try:
            # Send email using asyncio to avoid blocking
            return await self._send_email_async(email_config, msg, recipients)
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return EmailResult(
                recipient=to,
                subject=subject,
                message_sent=False,
                error=f"Failed to send email: {str(e)}"
            )
    
    def _get_email_config(self) -> Optional[EmailConfig]:
        """Get email configuration from app config."""
        try:
            if not hasattr(config, 'email_config'):
                logger.error("Email configuration not found in app config")
                return None
                
            return EmailConfig(
                smtp_server=config.email_config.smtp_server,
                smtp_port=config.email_config.smtp_port,
                smtp_username=config.email_config.smtp_username,
                smtp_password=config.email_config.smtp_password,
                use_tls=getattr(config.email_config, 'use_tls', True)
            )
        except AttributeError as e:
            logger.error(f"Missing email configuration: {str(e)}")
            return None
    
    async def _send_email_async(
        self, 
        email_config: EmailConfig, 
        msg: MIMEMultipart, 
        recipients: List[str]
    ) -> EmailResult:
        """Send email asynchronously."""
        def _send():
            with smtplib.SMTP(email_config.smtp_server, email_config.smtp_port) as server:
                if email_config.use_tls:
                    server.starttls()
                server.login(email_config.smtp_username, email_config.smtp_password)
                server.sendmail(email_config.smtp_username, recipients, msg.as_string())
                
        try:
            # Run SMTP operations in a thread pool
            await asyncio.get_event_loop().run_in_executor(None, _send)
            logger.info(f"Email sent successfully to {msg['To']} with subject '{msg['Subject']}'")
            return EmailResult(
                recipient=msg['To'],
                subject=msg['Subject'],
                message_sent=True
            )
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return EmailResult(
                recipient=msg['To'],
                subject=msg['Subject'],
                message_sent=False,
                error=f"Error sending email: {str(e)}"
            )


if __name__ == "__main__":
    # Example usage
    email_sender = EmailSender()
    result = asyncio.run(
        email_sender.execute(
            to="recipient@example.com",
            subject="Test Email",
            body="This is a test email sent from the EmailSender tool."
        )
    )
    print(result)