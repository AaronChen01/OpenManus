#!/usr/bin/env python
"""
Test script for the EmailSender tool.
This script demonstrates how to use the EmailSender tool to send emails.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.tool import EmailSender
from app.logger import logger


async def test_email_sender():
    """Test the EmailSender tool."""
    # Create an instance of the EmailSender tool
    email_sender = EmailSender()
    
    # Check if email configuration is available
    if not hasattr(email_sender, "_get_email_config") or not email_sender._get_email_config():
        logger.error("Email configuration is missing or incomplete in config.toml")
        logger.info("Please add the following to your config/config.toml file:")
        logger.info("""
[email]
smtp_server = "smtp.example.com"
smtp_port = 587
smtp_username = "your-email@example.com"
smtp_password = "your-password-or-app-password"
use_tls = true
        """)
        return
    
    # Get recipient email from command line or use a default for testing
    recipient = input("Enter recipient email address: ") if len(sys.argv) < 2 else sys.argv[1]
    
    # Send a test email
    logger.info(f"Sending test email to {recipient}...")
    result = await email_sender.execute(
        to=recipient,
        subject="Test Email from OpenManus",
        body="""
Hello from OpenManus!

This is a test email sent using the EmailSender tool.

Best regards,
OpenManus Agent
        """,
    )
    
    # Print the result
    if result.message_sent:
        logger.info("Email sent successfully!")
    else:
        logger.error(f"Failed to send email: {result.error}")


if __name__ == "__main__":
    asyncio.run(test_email_sender())