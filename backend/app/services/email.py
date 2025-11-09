"""Email notification service for sending real-time notifications"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.config import settings
from app.utils.monitoring import StructuredLogger


class EmailService:
    """Service for sending email notifications"""
    
    @staticmethod
    def get_user_email(user_id: str) -> Optional[str]:
        """
        Get user email from Supabase auth.users via database function
        
        Args:
            user_id: User ID
            
        Returns:
            User email address or None
        """
        try:
            from app.database import supabase
            from uuid import UUID
            
            # Use RPC function to get user email
            # This function is defined in migration 004_get_user_email_function.sql
            try:
                response = supabase.rpc("get_user_email", {"user_uuid": user_id}).execute()
                
                # RPC function returns the value directly
                if response.data is not None:
                    # RPC can return scalar value or dict
                    if isinstance(response.data, str):
                        return response.data
                    elif isinstance(response.data, dict):
                        return response.data.get("get_user_email") or response.data.get("email")
                    elif isinstance(response.data, list) and len(response.data) > 0:
                        email = response.data[0]
                        if isinstance(email, str):
                            return email
                        elif isinstance(email, dict):
                            return email.get("get_user_email") or email.get("email")
                
                # If RPC doesn't work, try admin API as fallback
                try:
                    admin_response = supabase.auth.admin.get_user_by_id(user_id)
                    if admin_response and hasattr(admin_response, 'user') and admin_response.user:
                        return admin_response.user.email
                except (AttributeError, Exception):
                    pass
                
            except Exception as rpc_error:
                # Fallback: Try admin API
                try:
                    admin_response = supabase.auth.admin.get_user_by_id(user_id)
                    if admin_response and hasattr(admin_response, 'user') and admin_response.user:
                        return admin_response.user.email
                except (AttributeError, Exception):
                    StructuredLogger.log_error(
                        rpc_error,
                        context={"function": "get_user_email_rpc", "user_id": user_id},
                    )
            
            return None
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={"function": "get_user_email", "user_id": user_id},
            )
            return None
    
    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send email notification
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.EMAIL_ENABLED:
            StructuredLogger.log_event(
                "email_disabled",
                "Email notifications are disabled",
                metadata={"to_email": to_email, "subject": subject},
            )
            return False
        
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            StructuredLogger.log_event(
                "email_config_missing",
                "Email configuration is missing",
                metadata={"to_email": to_email},
                level="WARNING",
            )
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.EMAIL_FROM or settings.SMTP_USER
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_body:
                text_part = MIMEText(text_body, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            StructuredLogger.log_event(
                "email_sent",
                f"Email sent to {to_email}",
                metadata={
                    "to_email": to_email,
                    "subject": subject,
                },
            )
            return True
            
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={
                    "function": "send_email",
                    "to_email": to_email,
                    "subject": subject,
                },
            )
            return False
    
    @staticmethod
    def send_task_nudge_email(
        user_email: str,
        task_title: str,
        task_time: str,
        is_critical: bool = False,
        is_urgent: bool = False
    ) -> bool:
        """
        Send task nudge email notification
        
        Args:
            user_email: User email address
            task_title: Task title
            task_time: Task scheduled time
            is_critical: Whether task is critical
            is_urgent: Whether task is urgent
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Build subject
        if is_critical:
            subject = f"🔴 CRITICAL: {task_title} is starting now"
        elif is_urgent:
            subject = f"⚠️ URGENT: {task_title} is starting now"
        else:
            subject = f"📋 {task_title} is starting now"
        
        # Build HTML body
        priority_badge = ""
        if is_critical:
            priority_badge = '<span style="background-color: #dc2626; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">CRITICAL</span>'
        elif is_urgent:
            priority_badge = '<span style="background-color: #ea580c; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">URGENT</span>'
        
        # Determine colors
        border_color = '#dc2626' if is_critical else ('#ea580c' if is_urgent else '#3b82f6')
        title_color = '#dc2626' if is_critical else ('#ea580c' if is_urgent else '#1f2937')
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f9fafb; border-radius: 8px; padding: 24px; border-left: 4px solid {border_color};">
                <h2 style="margin-top: 0; color: {title_color};">
                    {subject}
                </h2>
                {priority_badge}
                <p style="font-size: 16px; margin: 16px 0;">
                    <strong>{task_title}</strong> is scheduled to start at <strong>{task_time}</strong>.
                </p>
                <p style="font-size: 14px; color: #6b7280; margin-top: 24px;">
                    This is an automated notification from LifeFlow.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Build text body
        text_body = f"""
{subject}

{task_title} is scheduled to start at {task_time}.

This is an automated notification from LifeFlow.
        """.strip()
        
        return EmailService.send_email(
            to_email=user_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

