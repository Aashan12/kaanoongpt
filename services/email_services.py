from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import os
import random
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@kaanoongpt.com")

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

async def send_otp_email(to_email: str, full_name: str, otp: str):
    """Send OTP via email using SendGrid"""
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .otp-box {{
                background: #f0f9ff;
                border: 2px dashed #3b82f6;
                border-radius: 10px;
                padding: 30px;
                text-align: center;
                margin: 30px 0;
            }}
            .otp-code {{
                font-size: 36px;
                font-weight: bold;
                color: #2563eb;
                letter-spacing: 8px;
                margin: 10px 0;
            }}
            .warning {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .footer {{
                background: #f9fafb;
                padding: 20px 30px;
                text-align: center;
                color: #6b7280;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚖️ KAANOONGPT</h1>
                <p style="margin: 10px 0 0 0;">Email Verification</p>
            </div>
            <div class="content">
                <h2>Hi {full_name}! 👋</h2>
                <p>Thank you for signing up with <strong>KAANOONGPT</strong>!</p>
                <p>To complete your registration, please use the following One-Time Password (OTP):</p>
                
                <div class="otp-box">
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">Your OTP Code</p>
                    <div class="otp-code">{otp}</div>
                    <p style="margin: 0; color: #6b7280; font-size: 14px;">Valid for 10 minutes</p>
                </div>
                
                <div class="warning">
                    <strong>⚠️ Security Notice:</strong>
                    <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                        <li>Never share this OTP with anyone</li>
                        <li>KAANOONGPT will never ask for your OTP via phone or email</li>
                        <li>This code expires in 10 minutes</li>
                    </ul>
                </div>
                
                <p>If you didn't request this verification code, please ignore this email.</p>
                
                <p style="margin-top: 30px; color: #6b7280;">
                    Best regards,<br>
                    <strong>The KAANOONGPT Team</strong>
                </p>
            </div>
            <div class="footer">
                <p>© 2024 KAANOONGPT - Your AI Legal Companion</p>
                <p>This is an automated message, please do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        message = Mail(
            from_email=Email(FROM_EMAIL),
            to_emails=To(to_email),
            subject=f"Your KAANOONGPT Verification Code: {otp}",
            html_content=Content("text/html", html_content)
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"✅ OTP email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send OTP email: {str(e)}")
        return False