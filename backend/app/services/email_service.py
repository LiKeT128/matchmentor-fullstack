"""Email service for SendGrid integration."""

from typing import Optional
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails via SendGrid.
    
    Handles welcome emails, match analysis notifications,
    and other transactional emails.
    """
    
    def __init__(self):
        """Initialize SendGrid client if API key is configured."""
        self.api_key = settings.sendgrid_api_key
        self.from_email = settings.from_email
        self.client = None
        
        if self.api_key:
            self.client = SendGridAPIClient(api_key=self.api_key)
    
    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str
    ) -> bool:
        """
        Send an email via SendGrid.
        
        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            html_content: HTML body content.
            
        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.client:
            logger.warning("SendGrid not configured, skipping email send")
            return False
        
        try:
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            
            if response.status_code in (200, 202):
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Email send failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Email send error: {str(e)}")
            return False
    
    def send_welcome_email(self, to_email: str, username: Optional[str] = None) -> bool:
        """
        Send welcome email to new users.
        
        Args:
            to_email: New user's email address.
            username: Optional display name.
            
        Returns:
            True if sent successfully.
        """
        name = username or to_email.split("@")[0]
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4a90d9;">Welcome to MatchMentor! 🎮</h1>
            
            <p>Hi {name},</p>
            
            <p>Thanks for signing up for MatchMentor - your AI-powered Dota 2 coach!</p>
            
            <h2>Getting Started:</h2>
            <ol>
                <li>Upload your first replay (.dem file)</li>
                <li>Get detailed analysis with 60+ metrics</li>
                <li>Follow personalized coaching advice</li>
                <li>Track your improvement over time</li>
            </ol>
            
            <h2>Your Free Tier Includes:</h2>
            <ul>
                <li>5 replay analyses per month</li>
                <li>Basic performance metrics</li>
                <li>Top 3 improvement tips per match</li>
            </ul>
            
            <p style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                <strong>Pro Tip:</strong> Upload replays from your worst games - 
                that's where you'll learn the most!
            </p>
            
            <p>Ready to climb? Let's go! 🚀</p>
            
            <p>
                Best regards,<br>
                The MatchMentor Team
            </p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 12px; color: #888;">
                You're receiving this email because you signed up for MatchMentor.
            </p>
        </body>
        </html>
        """
        
        return self._send_email(
            to_email=to_email,
            subject="Welcome to MatchMentor! 🎮",
            html_content=html_content
        )
    
    def send_match_analysis_complete(
        self,
        to_email: str,
        match_id: str,
        hero_name: str,
        score: int
    ) -> bool:
        """
        Send notification when match analysis is complete.
        
        Args:
            to_email: User's email address.
            match_id: Internal match ID.
            hero_name: Hero played.
            score: Overall performance score.
            
        Returns:
            True if sent successfully.
        """
        emoji = "🌟" if score >= 70 else "📊" if score >= 50 else "💪"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4a90d9;">Match Analysis Ready! {emoji}</h1>
            
            <p>Your replay analysis is complete!</p>
            
            <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h2 style="margin: 0 0 10px 0;">{hero_name}</h2>
                <p style="font-size: 48px; margin: 10px 0; font-weight: bold;">{score}/100</p>
                <p style="margin: 0; color: #666;">Performance Score</p>
            </div>
            
            <p>
                <a href="{settings.frontend_url}/matches/{match_id}" 
                   style="display: inline-block; background: #4a90d9; color: white; 
                          padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                    View Full Analysis →
                </a>
            </p>
            
            <p style="color: #666;">
                See your detailed metrics, compare to benchmarks, and get 
                personalized coaching advice.
            </p>
            
            <p>
                Best regards,<br>
                The MatchMentor Team
            </p>
        </body>
        </html>
        """
        
        return self._send_email(
            to_email=to_email,
            subject=f"Your {hero_name} Match Analysis is Ready! {emoji}",
            html_content=html_content
        )
    
    def send_tier_upgrade_confirmation(
        self,
        to_email: str,
        new_tier: str
    ) -> bool:
        """
        Send confirmation email for subscription upgrade.
        
        Args:
            to_email: User's email address.
            new_tier: New subscription tier (PRO/PREMIUM).
            
        Returns:
            True if sent successfully.
        """
        tier_benefits = {
            "PRO": [
                "50 replay analyses per month",
                "Full 60+ metrics breakdown",
                "Priority support",
                "Hero-specific tips",
            ],
            "PREMIUM": [
                "Unlimited replay analyses",
                "Full 60+ metrics breakdown",
                "24/7 priority support",
                "1-on-1 coach matching",
                "Advanced trend analysis",
                "Team analytics",
            ]
        }
        
        benefits = tier_benefits.get(new_tier, [])
        benefits_html = "".join([f"<li>{b}</li>" for b in benefits])
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="color: #4a90d9;">Welcome to {new_tier}! 🎉</h1>
            
            <p>Your upgrade is complete. Here's what you unlocked:</p>
            
            <ul style="background: #f5f5f5; padding: 20px 40px; border-radius: 10px;">
                {benefits_html}
            </ul>
            
            <p>
                <a href="{settings.frontend_url}/upload" 
                   style="display: inline-block; background: #4a90d9; color: white; 
                          padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                    Upload a Replay Now →
                </a>
            </p>
            
            <p>
                Best regards,<br>
                The MatchMentor Team
            </p>
        </body>
        </html>
        """
        
        return self._send_email(
            to_email=to_email,
            subject=f"Welcome to MatchMentor {new_tier}! 🎉",
            html_content=html_content
        )


# Singleton instance
email_service = EmailService()


def send_welcome_email(to_email: str) -> bool:
    """Convenience function to send welcome email."""
    return email_service.send_welcome_email(to_email)


def send_payment_confirmation(to_email: str, tier: str) -> bool:
    """Convenience function to send payment confirmation email."""
    return email_service.send_tier_upgrade_confirmation(to_email, tier)
