"""
Alerting system for fraud detection.
"""

import asyncio
import aiohttp
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime
import redis

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manage alerts for fraud detection system.
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis: redis.Redis = redis_client
        self.webhook_sessions: Dict[str, Any] = {}
        self.alert_cooldowns: Dict[str, datetime] = {}

    async def send_alert(self, alert_data: Dict[str, Any]):
        """
        Send alert through configured channels.
        """

        alert_type = alert_data.get("type", "info")
        severity = alert_data.get("severity", "info")

        alert_key = f"alert_cooldown:{alert_data.get('transaction_id', 'system')}"

        # ✅ Type-safe Redis check
        cooldown_raw = self.redis.get(alert_key)
        if isinstance(cooldown_raw, (str, bytes)):
            logger.info(f"Alert {alert_key} in cooldown, skipping")
            return

        tasks: List[asyncio.Task] = []

        # Webhook
        webhook_url = self._get_webhook_url(severity)
        if webhook_url:
            tasks.append(asyncio.create_task(self._send_webhook(webhook_url, alert_data)))

        # Email
        email_config = self._get_email_config()
        if email_config:
            tasks.append(asyncio.create_task(self._send_email(email_config, alert_data)))

        # Slack
        slack_config = self._get_slack_config()
        if slack_config:
            tasks.append(asyncio.create_task(self._send_slack(slack_config, alert_data)))

        # SMS (critical only)
        sms_config = self._get_sms_config()
        if severity == "critical" and sms_config:
            tasks.append(asyncio.create_task(self._send_sms(sms_config, alert_data)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Set cooldown safely
        try:
            self.redis.setex(alert_key, 300, "1")
        except Exception as e:
            logger.error(f"Redis cooldown error: {e}")

        logger.info(f"Alert sent: {alert_type} - {alert_data.get('message', '')}")

    async def _send_webhook(self, url: str, data: Dict[str, Any]):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as resp:
                    if resp.status >= 400:
                        logger.error(f"Webhook failed: {resp.status}")
        except Exception as e:
            logger.error(f"Webhook error: {e}")

    async def _send_email(self, config: Dict[str, Any], data: Dict[str, Any]):
        try:
            msg = MIMEMultipart()
            msg["From"] = config["from"]
            msg["To"] = config["to"]
            msg["Subject"] = (
                f"[{data.get('severity', 'INFO').upper()}] "
                f"Fraud Alert: {data.get('transaction_id', 'System')}"
            )

            body = self._format_email_body(data)
            msg.attach(MIMEText(body, "html"))

            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"])
            server.starttls()

            if config.get("username") and config.get("password"):
                server.login(config["username"], config["password"])

            server.send_message(msg)
            server.quit()

        except Exception as e:
            logger.error(f"Email error: {e}")

    async def _send_slack(self, config: Dict[str, Any], data: Dict[str, Any]):
        try:
            webhook_url = config["webhook_url"]
            message = self._format_slack_message(data)

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=message) as resp:
                    if resp.status >= 400:
                        logger.error(f"Slack failed: {resp.status}")
        except Exception as e:
            logger.error(f"Slack error: {e}")

    async def _send_sms(self, config: Dict[str, Any], data: Dict[str, Any]):
        try:
            # Placeholder for Twilio or other SMS provider
            logger.info(f"SMS alert would be sent: {data.get('message', '')}")
        except Exception as e:
            logger.error(f"SMS error: {e}")

    def _format_email_body(self, data: Dict[str, Any]) -> str:
        html = f"""
        <html>
        <body>
            <h2>🚨 Fraud Detection Alert</h2>
            <p><strong>Severity:</strong> {data.get('severity', 'INFO')}</p>
            <p><strong>Type:</strong> {data.get('type', 'unknown')}</p>
            <p><strong>Timestamp:</strong> {datetime.now().isoformat()}</p>
            <hr>
            <h3>Details:</h3>
            <pre>{json.dumps(data.get('details', {}), indent=2)}</pre>
            <hr>
            <h3>Recommendations:</h3>
            <ul>
        """

        for rec in data.get("recommendations", []):
            html += f"<li>{rec}</li>"

        html += """
            </ul>
        </body>
        </html>
        """

        return html

    def _format_slack_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        color_map = {
            "info": "#36a64f",
            "warning": "#FFA500",
            "critical": "#FF0000",
        }

        return {
            "attachments": [
                {
                    "color": color_map.get(data.get("severity", "info"), "#36a64f"),
                    "title": f"Fraud Alert: {data.get('type', 'System Alert')}",
                    "fields": [
                        {
                            "title": "Severity",
                            "value": data.get("severity", "INFO"),
                            "short": True,
                        },
                        {
                            "title": "Transaction ID",
                            "value": data.get("transaction_id", "N/A"),
                            "short": True,
                        },
                        {
                            "title": "Risk Score",
                            "value": str(data.get("risk_score", "N/A")),
                            "short": True,
                        },
                        {
                            "title": "Message",
                            "value": data.get("message", ""),
                            "short": False,
                        },
                    ],
                    "footer": "Safari-Shield Fraud Detection",
                    "ts": int(datetime.now().timestamp()),
                }
            ]
        }

    def _get_webhook_url(self, severity: str) -> Optional[str]:
        return os.getenv(f"WEBHOOK_{severity.upper()}_URL")

    def _get_email_config(self) -> Optional[Dict[str, Any]]:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port_str = os.getenv("SMTP_PORT")
        email_from = os.getenv("EMAIL_FROM")
        email_to = os.getenv("EMAIL_TO")
        username = os.getenv("SMTP_USERNAME")
        password = os.getenv("SMTP_PASSWORD")

        # Required fields must not be None
        if (
            smtp_host is None
            or smtp_port_str is None
            or email_from is None
            or email_to is None
        ):
            return None

        try:
            smtp_port: int = int(smtp_port_str)
        except ValueError:
            logger.error("SMTP_PORT must be a valid integer")
            return None

        return {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "from": email_from,
            "to": email_to,
            "username": username,
            "password": password,
        }

    def _get_slack_config(self) -> Optional[Dict[str, Any]]:
        webhook = os.getenv("SLACK_WEBHOOK_URL")
        if webhook:
            return {"webhook_url": webhook}
        return None

    def _get_sms_config(self) -> Optional[Dict[str, Any]]:
        required = ["TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM", "SMS_TO"]
        if all(os.getenv(k) for k in required):
            return {
                "sid": os.getenv("TWILIO_SID"),
                "token": os.getenv("TWILIO_TOKEN"),
                "from": os.getenv("TWILIO_FROM"),
                "to": os.getenv("SMS_TO"),
            }
        return None


class AlertRules:
    """Define alert rules for fraud detection."""

    @staticmethod
    def check_fraud_alert(prediction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if prediction.get("is_fraud") and prediction.get("risk_score", 0) > 0.8:
            return {
                "type": "fraud_detected",
                "severity": "critical",
                "transaction_id": prediction.get("transaction_id"),
                "risk_score": prediction.get("risk_score"),
                "message": "High-confidence fraud detected",
                "details": prediction,
                "recommendations": [
                    "Block transaction immediately",
                    "Contact customer for verification",
                    "Freeze account temporarily",
                ],
            }
        return None

    @staticmethod
    def check_high_risk_alert(prediction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        risk_score = prediction.get("risk_score", 0)
        if 0.5 <= risk_score < 0.8:
            return {
                "type": "high_risk",
                "severity": "warning",
                "transaction_id": prediction.get("transaction_id"),
                "risk_score": risk_score,
                "message": "High-risk transaction detected",
                "details": prediction,
                "recommendations": [
                    "Send OTP verification",
                    "Place 30-minute hold",
                    "Add to watchlist",
                ],
            }
        return None