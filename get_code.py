import logging
import requests

logging.basicConfig(level=logging.INFO)

def log_info(message):
    logging.info(message)

def log_success(message):
    logging.info(message)

def log_warning(message):
    logging.warning(message)

def log_error(message):
    logging.error(message)

def extract_tokens(account_info):
    try:
        # Determine the delimiter
        delimiter = '|' if '|' in account_info else ':'
        
        # Split the account info using the determined delimiter
        parts = account_info.split(delimiter)
        
        # Identify email by the presence of '@'
        email_address = next(part for part in parts if "@" in part)
        
        # Find the index of the email to locate the password
        email_index = parts.index(email_address)
        mailpass = parts[email_index + 1] if (email_index + 1) < len(parts) else None
        
        # Ensure ref token is the 5th and clientid is the 6th
        refreshtoken = parts[-2] if len(parts) > 5 else None
        clientid = parts[-1] if len(parts) > 5 else None
        
        if None in [email_address, mailpass, refreshtoken, clientid]:
            raise ValueError("Некорректный формат")

        return email_address, mailpass, refreshtoken, clientid
    except (IndexError, StopIteration, ValueError):
        return None, None, None, None

def get_access_token(refreshtoken, clientid):
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    post_data = {
        "client_id": clientid,
        "refresh_token": refreshtoken,
        "grant_type": "refresh_token",
        "scope": "https://outlook.office.com/IMAP.AccessAsUser.All offline_access"
    }

    try:
        response = requests.post(token_url, data=post_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        response.raise_for_status()

        response_data = response.json()
        access_token = response_data.get("access_token")
        log_success(f"Access token получен: {access_token[:30]}...")
        return access_token

    except Exception as e:
        log_error(f"Ошибка при обновлении токена: {e}")
        return None

def get_code_from_email_hotmail(email_address, access_token):
    """Получение кода подтверждения из почты Hotmail"""
    import imaplib
    import time
    from datetime import datetime, timedelta
    from email import message_from_bytes
    from email.header import decode_header
    import re

    imap_server = "imap-mail.outlook.com"
    imap_port = 993

    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.authenticate("XOAUTH2", lambda x: f"user={email_address}\1auth=Bearer {access_token}\1\1".encode())
    except Exception as e:
        log_error(f"Ошибка подключения к почте: {e}")
        return None

    try:
        mail.select("inbox")
        
        # Получаем текущую дату и дату 7 дней назад
        today = datetime.today()
        since_date = (today - timedelta(days=7)).strftime("%d-%b-%Y")

        for _ in range(10):  # Максимум 10 попыток
            status, messages = mail.search(None, f'(FROM "register@account.tiktok.com" SINCE {since_date})')
            if status != "OK" or not messages[0]:
                time.sleep(3)
                continue

            email_ids = messages[0].split()
            latest_email_id = email_ids[-1]
            status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
            
            if not msg_data or not isinstance(msg_data[0], tuple):
                time.sleep(3)
                continue

            email_body = msg_data[0][1]
            if not isinstance(email_body, bytes):
                email_body = str(email_body).encode('utf-8')

            msg = message_from_bytes(email_body)
            
            # Поиск кода в теме
            subject = decode_email_subject(msg)
            code_match = re.search(r'(\d{6})', subject)
            if code_match:
                code = code_match.group(1)
                log_success(f"Код найден: {code}")
                mail.logout()
                return code

            # Поиск кода в теле письма
            body = get_email_body(msg)
            code_match = re.search(r'<p style="margin-bottom:20px;color: rgb\(22,24,35\);font-weight: bold;">(\d{6})</p>', body)
            if code_match:
                code = code_match.group(1)
                log_success(f"Код найден: {code}")
                mail.logout()
                return code

            time.sleep(3)

        mail.logout()
        return None

    except Exception as e:
        log_error(f"Ошибка при получении кода: {e}")
        try:
            mail.logout()
        except:
            pass
        return None

def decode_email_subject(msg):
    """Декодирование темы письма"""
    subject_header = msg.get("Subject", "")
    decoded_subject = decode_header(subject_header)
    subject = ""
    for part, enc in decoded_subject:
        if isinstance(part, bytes):
            subject += part.decode(enc if enc else "utf-8", errors="ignore")
        else:
            subject += part
    return subject

def get_email_body(msg):
    """Получение тела письма"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ["text/plain", "text/html"]:
                charset = part.get_content_charset()
                try:
                    payload = part.get_payload(decode=True)
                    body += payload.decode(charset if charset else "utf-8", errors="ignore")
                except Exception:
                    continue
    else:
        charset = msg.get_content_charset()
        try:
            payload = msg.get_payload(decode=True)
            body = payload.decode(charset if charset else "utf-8", errors="ignore")
        except Exception:
            pass
    return body
