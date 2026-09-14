import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional

class EmailSender:
    """
    분석 완료된 당일 주식 리포트(HTML 본문 및 첨부파일)를 이메일로 자동 전송하는 모듈
    (네이버 메일 / Gmail 등 표준 SMTP 지원)
    """

    def __init__(self):
        self.sender_email = os.getenv("EMAIL_SENDER", "").strip()
        self.sender_password = os.getenv("EMAIL_PASSWORD", "").strip()
        self.receiver_email = os.getenv("EMAIL_RECEIVER", "").strip() or os.getenv("MAIL_RECEIVER", "").strip() or self.sender_email
        self.smtp_server = os.getenv("SMTP_SERVER", "").strip() or "smtp.naver.com"
        port_env = os.getenv("SMTP_PORT", "").strip()
        self.smtp_port = int(port_env) if port_env.isdigit() else 465

    def send_report_email(self, target_date: str, html_content: str, attachment_path: Optional[str] = None, seo_title: str = "", seo_tags: str = "", thumbnail_path: Optional[str] = None) -> bool:
        """
        완성된 리포트 HTML을 본문으로 넣고 .html 파일 및 대표 썸네일 이미지를 첨부하여 이메일을 발송합니다.
        (SEO 최적화 제목, 복사용 추천 태그, 대표 썸네일 이미지 포함)
        """
        if not self.sender_email or not self.sender_password:
            print("⚠️ EMAIL_SENDER 또는 EMAIL_PASSWORD가 설정되지 않아 이메일 발송을 건너뜁니다.")
            return False

        date_formatted = f"{target_date[:4]}.{target_date[4:6]}.{target_date[6:]}" if len(target_date) == 8 else target_date
        default_title = f"[{date_formatted}] 오늘의 상한가 & 1,000만주 특징주 총정리"
        final_seo_title = seo_title if seo_title else default_title
        subject = f"📊 {final_seo_title}"

        msg = MIMEMultipart("mixed")
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email
        msg["Subject"] = subject

        import html as html_lib
        import base64
        escaped_html = html_lib.escape(html_content)
        escaped_title = html_lib.escape(final_seo_title)
        escaped_tags = html_lib.escape(seo_tags) if seo_tags else f"상한가,특징주,급등주,주식시황,{date_formatted}"

        # 대표 썸네일 인라인 Base64 이미지 태그 생성
        thumbnail_html_block = ""
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                with open(thumbnail_path, "rb") as img_f:
                    b64_str = base64.b64encode(img_f.read()).decode("utf-8")
                    thumbnail_html_block = f"""
                    <!-- 대표 썸네일 이미지 영역 -->
                    <div style="margin-bottom: 18px; background: #f8f9fa; border: 1px solid #ced4da; border-radius: 8px; padding: 12px; text-align: center;">
                        <div style="font-size: 13px; font-weight: bold; color: #1971c2; margin-bottom: 8px; text-align: left;">🖼️ [대표 썸네일 이미지] (우클릭하여 '이미지 저장' ➔ 블로그 대표사진으로 지정):</div>
                        <img src="data:image/png;base64,{b64_str}" alt="블로그 대표 썸네일" style="max-width: 100%; height: auto; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" />
                    </div>
                    """
            except Exception:
                pass

        # 안내 문구 + SEO 제목/태그 복사 + 원클릭 복사 박스 + 썸네일 + 본문 미리보기 HTML
        intro_text = f"""
        <div style="background: #e7f5ff; border: 2px solid #339af0; padding: 20px; border-radius: 10px; margin-bottom: 25px; font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', sans-serif;">
            <h3 style="margin: 0 0 12px 0; color: #1864ab; font-size: 17px; font-weight: 800;">🚀 티스토리 글쓰기 원클릭 가이드 (SEO 최적화)</h3>
            
            {thumbnail_html_block}

            <!-- 1. 추천 글 제목 -->
            <div style="margin-bottom: 12px;">
                <div style="font-size: 13px; font-weight: bold; color: #1971c2; margin-bottom: 4px;">📌 [1단계] 복사용 추천 글 제목 (클릭 시 자동 선택):</div>
                <input type="text" readonly value="{escaped_title}" onclick="this.select();" style="width: 100%; padding: 8px 12px; font-size: 13px; font-weight: bold; color: #212529; background: #ffffff; border: 1px solid #74c0fc; border-radius: 6px; box-sizing: border-box;" />
            </div>

            <!-- 2. 추천 태그 -->
            <div style="margin-bottom: 15px;">
                <div style="font-size: 13px; font-weight: bold; color: #1971c2; margin-bottom: 4px;">🏷️ [2단계] 티스토리 태그란 복사용 키워드 (클릭 시 자동 선택):</div>
                <input type="text" readonly value="{escaped_tags}" onclick="this.select();" style="width: 100%; padding: 8px 12px; font-size: 12px; color: #495057; background: #ffffff; border: 1px solid #74c0fc; border-radius: 6px; box-sizing: border-box;" />
            </div>

            <!-- 3. HTML 본문 코드 -->
            <div style="margin-bottom: 5px;">
                <div style="font-size: 13px; font-weight: bold; color: #1971c2; margin-bottom: 4px;">📋 [3단계] 본문 HTML 소스코드 (클릭 시 자동 선택 ➔ 티스토리 [HTML 모드]에 붙여넣기):</div>
                <textarea readonly onclick="this.select();" style="width: 100%; height: 110px; background: #212529; color: #51cf66; font-family: monospace; font-size: 12px; padding: 10px; border-radius: 6px; border: 1px solid #ced4da; box-sizing: border-box; resize: vertical;">{escaped_html}</textarea>
            </div>
            <div style="font-size: 12px; color: #868e96; margin-top: 6px;">💡 위 상자들을 한 번만 클릭하면 전체 선택되므로 <strong>Ctrl+C</strong>로 바로 복사해서 붙여넣으실 수 있습니다.</div>
        </div>

        <div style="font-size: 14px; font-weight: bold; color: #495057; margin-bottom: 10px;">👇 [미리보기] 생성된 블로그 콘텐츠 서식:</div>
        """
        
        full_html_body = intro_text + html_content
        html_part = MIMEText(full_html_body, "html", "utf-8")
        msg.attach(html_part)

        # 1. 첨부파일(.html 리포트) 추가
        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                    msg.attach(part)
            except Exception as e:
                print(f"⚠️ 리포트 첨부파일 로드 실패: {e}")

        # 2. 첨부파일(대표 썸네일 이미지) 추가
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                with open(thumbnail_path, "rb") as f:
                    part_img = MIMEApplication(f.read(), Name=os.path.basename(thumbnail_path))
                    part_img["Content-Disposition"] = f'attachment; filename="{os.path.basename(thumbnail_path)}"'
                    msg.attach(part_img)
            except Exception as e:
                print(f"⚠️ 썸네일 첨부파일 로드 실패: {e}")

        # 메일 발송
        try:
            print(f"📧 이메일 발송 중... ({self.sender_email} ➔ {self.receiver_email})")
            if self.smtp_port == 465:
                # SSL 방식 (네이버 메일 기본)
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.sender_email, [self.receiver_email], msg.as_string())
            else:
                # TLS 방식 (Gmail 등 587 포트)
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15) as server:
                    server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.sender_email, [self.receiver_email], msg.as_string())

            print(f"🎉 [{self.receiver_email}]로 리포트 이메일 발송이 성공했습니다!")
            return True

        except Exception as e:
            print(f"❌ 이메일 발송 실패: {e}")
            return False
