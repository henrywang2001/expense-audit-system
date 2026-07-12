"""
通知工具
提供邮件通知和系统消息推送功能
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationTool:
    """
    通知工具

    提供邮件发送和系统通知功能
    """

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
        cc: Optional[List[str]] = None,
    ) -> bool:
        """
        发送邮件通知

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            body: 邮件内容
            html: 是否为HTML格式
            cc: 抄送列表

        Returns:
            发送是否成功
        """
        if not self.smtp_host or not self.smtp_user:
            logger.warning("邮件服务未配置，跳过邮件发送")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[报销审核系统] {subject}"
            msg["From"] = self.smtp_user
            msg["To"] = to_email

            if cc:
                msg["Cc"] = ", ".join(cc)

            if html:
                msg.attach(MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"邮件发送成功: {subject} -> {to_email}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    def send_approval_notification(
        self,
        to_email: str,
        username: str,
        expense_title: str,
        expense_no: str,
        status: str,
        comment: Optional[str] = None,
    ) -> bool:
        """
        发送审批结果通知

        Args:
            to_email: 收件人邮箱
            username: 用户名
            expense_title: 报销单标题
            expense_no: 报销单编号
            status: 审批状态 (approved/rejected)
            comment: 审批意见
        """
        status_text = "通过" if status == "approved" else "未通过"

        subject = f"报销单审核{status_text}通知 - {expense_no}"

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: {'#4CAF50' if status == 'approved' else '#F44336'}; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">报销单审核通知</h2>
            </div>
            <div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 8px 8px;">
                <p>亲爱的 <strong>{username}</strong>：</p>
                <p>您的报销单审核结果如下：</p>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">报销单编号</td>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>{expense_no}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">报销单标题</td>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;">{expense_title}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">审核结果</td>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;">
                            <span style="color: {'#4CAF50' if status == 'approved' else '#F44336'}; font-weight: bold;">
                                {status_text}
                            </span>
                        </td>
                    </tr>
                    {f'<tr><td style="padding: 8px; color: #666;">审批意见</td><td style="padding: 8px;">{comment}</td></tr>' if comment else ''}
                </table>
                <p style="margin-top: 20px; color: #999; font-size: 12px;">
                    此邮件由系统自动发送，请勿回复。<br>
                    如有疑问请联系财务部。
                </p>
            </div>
        </div>
        """

        return self.send_email(to_email, subject, html_body, html=True)

    def send_ai_review_notification(
        self,
        to_email: str,
        username: str,
        expense_title: str,
        expense_no: str,
        risk_level: str,
        risk_score: float,
    ) -> bool:
        """
        发送AI审核结果通知

        Args:
            to_email: 收件人邮箱
            username: 用户名
            expense_title: 报销单标题
            expense_no: 报销单编号
            risk_level: 风险等级
            risk_score: 风险评分
        """
        risk_color_map = {
            "low": "#4CAF50",
            "medium": "#FF9800",
            "high": "#F44336",
            "critical": "#D32F2F",
        }
        risk_text_map = {
            "low": "低风险",
            "medium": "中等风险",
            "high": "高风险",
            "critical": "严重风险",
        }

        color = risk_color_map.get(risk_level, "#757575")
        risk_text = risk_text_map.get(risk_level, risk_level)

        subject = f"AI智能审核结果 - {expense_no}"

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #2196F3; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">AI智能审核结果</h2>
            </div>
            <div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 8px 8px;">
                <p>亲爱的 <strong>{username}</strong>：</p>
                <p>系统已完成对报销单的AI智能审核：</p>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">报销单编号</td>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>{expense_no}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">报销单标题</td>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;">{expense_title}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">风险等级</td>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;">
                            <span style="background-color: {color}; color: white; padding: 2px 10px; border-radius: 12px; font-size: 12px;">
                                {risk_text}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #eee; color: #666;">风险评分</td>
                        <td style="padding: 8px; border-bottom: 1px solid #eee;">{risk_score}/100</td>
                    </tr>
                </table>
                <p style="margin-top: 20px; color: #999; font-size: 12px;">
                    此邮件由系统自动发送。<br>
                    请登录系统查看详细审核结果。
                </p>
            </div>
        </div>
        """

        return self.send_email(to_email, subject, html_body, html=True)


# 单例
notification_tool = NotificationTool()
