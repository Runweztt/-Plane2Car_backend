import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config


def _send_email(to_email, subject, html_body):
    """Send an HTML email via SMTP. Silently skips if SMTP is not configured."""
    if not Config.MAIL_SERVER or not Config.MAIL_USERNAME:
        print(f"[EMAIL] Skipped (no SMTP config): {subject} → {to_email}")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = Config.MAIL_DEFAULT_SENDER or Config.MAIL_USERNAME
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
            if Config.MAIL_USE_TLS:
                server.starttls()
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.sendmail(msg['From'], to_email, msg.as_string())
        print(f"[EMAIL] Sent '{subject}' → {to_email}")
    except Exception as e:
        print(f"[EMAIL] Failed '{subject}' → {to_email}: {e}")


def send_passenger_assignment_email(
    passenger_email, passenger_name,
    concierge_name, concierge_phone,
    flight_number, arrival_time, airport_name
):
    subject = "Your Concierge Has Been Assigned — Plane to Car"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#0f172a;
                color:#e2e8f0;padding:40px 32px;border-radius:16px;">
      <div style="margin-bottom:24px;">
        <h1 style="color:#f59e0b;margin:0 0 4px;font-size:24px;">Plane to Car</h1>
        <p style="color:#64748b;margin:0;font-size:13px;">Priority Passenger Clearance</p>
      </div>
      <hr style="border:none;border-top:1px solid #1e293b;margin:0 0 28px;" />

      <p style="font-size:17px;margin:0 0 12px;">Hi <strong>{passenger_name}</strong>,</p>
      <p style="color:#94a3b8;margin:0 0 24px;line-height:1.6;">
        Great news! Your dedicated concierge has been assigned for your upcoming arrival.
        They will be waiting for you at <strong style="color:#e2e8f0;">{airport_name}</strong>.
      </p>

      <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:24px;
                  border-left:4px solid #f59e0b;">
        <p style="margin:0 0 4px;font-size:11px;color:#64748b;text-transform:uppercase;
                  letter-spacing:0.1em;">Your Concierge</p>
        <p style="margin:0 0 16px;font-size:20px;font-weight:bold;color:#f8fafc;">{concierge_name}</p>
        <p style="margin:0 0 4px;font-size:11px;color:#64748b;text-transform:uppercase;
                  letter-spacing:0.1em;">Phone Number</p>
        <p style="margin:0;font-size:18px;font-weight:bold;color:#f59e0b;">
          {concierge_phone if concierge_phone else 'Will contact you on arrival'}
        </p>
      </div>

      <p style="margin:0 0 8px;font-size:13px;color:#64748b;text-transform:uppercase;
                letter-spacing:0.08em;">Your Booking Details</p>
      <div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:28px;">
        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="padding:6px 0;color:#64748b;font-size:13px;width:120px;">Flight</td>
            <td style="padding:6px 0;color:#f8fafc;font-weight:bold;font-family:monospace;">{flight_number}</td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#64748b;font-size:13px;">Arrival</td>
            <td style="padding:6px 0;color:#f8fafc;font-weight:bold;">{arrival_time}</td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#64748b;font-size:13px;">Airport</td>
            <td style="padding:6px 0;color:#f8fafc;font-weight:bold;">{airport_name}</td>
          </tr>
        </table>
      </div>

      <p style="font-size:13px;color:#64748b;line-height:1.6;margin:0 0 28px;">
        Your concierge will meet you at the arrivals hall. Feel free to reach them directly
        using the phone number above if needed.
      </p>

      <hr style="border:none;border-top:1px solid #1e293b;margin:0 0 20px;" />
      <p style="font-size:12px;color:#475569;text-align:center;margin:0;">
        Plane to Car · Nigeria's Premium Airport Concierge Service
      </p>
    </div>
    """
    _send_email(passenger_email, subject, html)


def send_concierge_assignment_email(
    concierge_email, concierge_name,
    passenger_name, passenger_email,
    flight_number, arrival_time, airport_name
):
    subject = f"New Assignment: {passenger_name} — Plane to Car"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#0f172a;
                color:#e2e8f0;padding:40px 32px;border-radius:16px;">
      <div style="margin-bottom:24px;">
        <h1 style="color:#f59e0b;margin:0 0 4px;font-size:24px;">Plane to Car</h1>
        <p style="color:#64748b;margin:0;font-size:13px;">Priority Passenger Clearance</p>
      </div>
      <hr style="border:none;border-top:1px solid #1e293b;margin:0 0 28px;" />

      <p style="font-size:17px;margin:0 0 12px;">Hi <strong>{concierge_name}</strong>,</p>
      <p style="color:#94a3b8;margin:0 0 24px;line-height:1.6;">
        You have been assigned a new passenger. Please review the details below and be at
        <strong style="color:#e2e8f0;">{airport_name}</strong> before the arrival time.
      </p>

      <p style="margin:0 0 8px;font-size:13px;color:#64748b;text-transform:uppercase;
                letter-spacing:0.08em;">Passenger Details</p>
      <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:24px;
                  border-left:4px solid #f59e0b;">
        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="padding:6px 0;color:#64748b;font-size:13px;width:130px;">Passenger Name</td>
            <td style="padding:6px 0;color:#f8fafc;font-weight:bold;">{passenger_name}</td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#64748b;font-size:13px;">Passenger Email</td>
            <td style="padding:6px 0;color:#f8fafc;">{passenger_email}</td>
          </tr>
        </table>
      </div>

      <p style="margin:0 0 8px;font-size:13px;color:#64748b;text-transform:uppercase;
                letter-spacing:0.08em;">Booking Details</p>
      <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:28px;
                  border-left:4px solid #3b82f6;">
        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="padding:6px 0;color:#64748b;font-size:13px;width:130px;">Flight Number</td>
            <td style="padding:6px 0;color:#f8fafc;font-weight:bold;font-family:monospace;
                       font-size:16px;">{flight_number}</td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#64748b;font-size:13px;">Arrival Time</td>
            <td style="padding:6px 0;color:#f59e0b;font-weight:bold;font-size:16px;">{arrival_time}</td>
          </tr>
          <tr>
            <td style="padding:6px 0;color:#64748b;font-size:13px;">Airport</td>
            <td style="padding:6px 0;color:#f8fafc;font-weight:bold;">{airport_name}</td>
          </tr>
        </table>
      </div>

      <p style="font-size:13px;color:#64748b;line-height:1.6;margin:0 0 28px;">
        Log into your concierge dashboard to track and update this booking's status.
      </p>

      <hr style="border:none;border-top:1px solid #1e293b;margin:0 0 20px;" />
      <p style="font-size:12px;color:#475569;text-align:center;margin:0;">
        Plane to Car · Nigeria's Premium Airport Concierge Service
      </p>
    </div>
    """
    _send_email(concierge_email, subject, html)


def send_concierge_welcome_email(concierge_email, concierge_name, temp_password):
    subject = "Welcome to Plane to Car — Your Concierge Account"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;background:#0f172a;
                color:#e2e8f0;padding:40px 32px;border-radius:16px;">
      <div style="margin-bottom:24px;">
        <h1 style="color:#f59e0b;margin:0 0 4px;font-size:24px;">Plane to Car</h1>
        <p style="color:#64748b;margin:0;font-size:13px;">Priority Passenger Clearance</p>
      </div>
      <hr style="border:none;border-top:1px solid #1e293b;margin:0 0 28px;" />

      <p style="font-size:17px;margin:0 0 12px;">Welcome, <strong>{concierge_name}</strong>!</p>
      <p style="color:#94a3b8;margin:0 0 24px;line-height:1.6;">
        Your concierge account has been created. You can now log in to your dashboard
        to manage passenger assignments.
      </p>

      <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:28px;
                  border-left:4px solid #10b981;">
        <p style="margin:0 0 4px;font-size:11px;color:#64748b;text-transform:uppercase;
                  letter-spacing:0.1em;">Your Login Email</p>
        <p style="margin:0 0 16px;font-size:16px;color:#f8fafc;">{concierge_email}</p>
        <p style="margin:0 0 4px;font-size:11px;color:#64748b;text-transform:uppercase;
                  letter-spacing:0.1em;">Temporary Password</p>
        <p style="margin:0;font-size:20px;font-weight:bold;color:#10b981;font-family:monospace;">
          {temp_password}
        </p>
      </div>

      <p style="font-size:13px;color:#94a3b8;line-height:1.6;margin:0 0 8px;">
        Please log in and change your password at your earliest convenience.
      </p>

      <hr style="border:none;border-top:1px solid #1e293b;margin:24px 0 20px;" />
      <p style="font-size:12px;color:#475569;text-align:center;margin:0;">
        Plane to Car · Nigeria's Premium Airport Concierge Service
      </p>
    </div>
    """
    _send_email(concierge_email, subject, html)
