import imaplib
import ssl

from Decorators.perf_logger import auto_perf_logger
import email
import email.utils
from email.header import decode_header
import re
import time
import socket
from datetime import datetime, timezone

IMAP_PROVIDERS = {
    "gmail.com": "imap.gmail.com",
    "outlook.com": "imap-mail.outlook.com",
    "hotmail.com": "imap-mail.outlook.com",
    "live.com": "imap-mail.outlook.com",
    "office365.com": "outlook.office365.com",
    "yahoo.com": "imap.mail.yahoo.com",
    "yandex.com": "imap.yandex.com",
    "icloud.com": "imap.mail.me.com",
}

SENT_FOLDERS = {
    "gmail.com": "[Gmail]/Sent Mail",
    "outlook.com": "Sent",
    "hotmail.com": "Sent",
    "live.com": "Sent",
    "office365.com": "Sent Items",
    "yahoo.com": "Sent",
    "yandex.com": "Sent",
    "icloud.com": "Sent Messages",
}


class ForceIPv4IMAP(imaplib.IMAP4_SSL):
    def _create_socket(self, timeout=None):
        # 1. Adım: Hostname'i zorla IPv4'e çevir (20sn gecikmeyi önler)
        target_ip = socket.gethostbyname(self.host)

        # 2. Adım: IP adresine TCP bağlantısı kur
        sock = socket.create_connection((target_ip, self.port), timeout)

        # 3. Adım: SSL Sarmalama (KRİTİK NOKTA)
        # Bağlantı IP'ye yapıldı ama sertifika kontrolü "host" (örn: gmail.com) için yapılır.
        if self.ssl_context:
            return self.ssl_context.wrap_socket(sock, server_hostname=self.host)
        else:
            return ssl.wrap_socket(sock, self.keyfile, self.certfile,
                                   server_hostname=self.host)

@auto_perf_logger
class EmailReceiver:
    def __init__(self, username, password,ip_cache=True):
        self.username = username
        self.password = password
        self.mail = None
        self.provider = username.split("@")[-1]
        self.host = IMAP_PROVIDERS.get(self.provider)
        self.ip_cache = ip_cache

        if not self.host:
            raise RuntimeError("Invalid provider.")
        self.connect()

    def connect(self):
        context = ssl.create_default_context()
        print(f"Connecting: {self.host} (IPv4 forced)...")

        start = time.time()

        try:
            self.mail = ForceIPv4IMAP(self.host, ssl_context=context, timeout=10)
        except Exception as e:
            raise ConnectionError(f"IMAP connection error ({self.host}): {e}") from e

        end = time.time()
        print(f"SSL connect (IPv4 Forced): {end - start:.2f}s")

        start = time.time()
        self.mail.login(self.username, self.password)
        end = time.time()
        print(f"Login time: {end - start:.2f}s")

        start = time.time()
        self.mail.select('inbox')
        end = time.time()
        print(f"select: {end - start:.2f}s")

        print("Connected successfully")

    def fetch_mails(self, limit=10, from_email=None):
        emails = []
        try:
            if from_email:
                #uid based
                status, data = self.mail.uid('search', None, from_email)
            else:
                status, data = self.mail.uid('search', None, "ALL")
            if status != 'OK':
                return emails

            mail_uids = data[0].split()

            if not from_email:
                mail_uids = mail_uids[-limit:]

            mail_uids.reverse()

            batch_size=20

            for i in range(0,len(mail_uids),batch_size):
                batch_uids = mail_uids[i:i+batch_size]
                uid_str=b",".join(batch_uids)

                status, data = self.mail.uid('fetch', uid_str,"(RFC822)")

                if status == 'OK':
                    for response_part in data:
                        if isinstance(response_part, tuple):
                            try:
                                msg=email.message_from_bytes(response_part[1])
                                emails.append(msg)
                            except Exception as e:
                                print(f"Parse error: {e}")

            return emails
        except Exception as e:
            print(f"Fetch error: {e}")
            return emails

    def _find_sent_folder(self):
        """Dynamically detect the sent folder by listing IMAP folders."""
        if hasattr(self, '_cached_sent_folder'):
            return self._cached_sent_folder

        known_sent_names = {
            "[gmail]/sent mail", "[gmail]/gönderilmiş postalar",
            "[gmail]/gönderilmi&av8- postalar",
            "sent", "sent mail", "sent items", "sent messages",
            "[gmail]/enviados", "[gmail]/envoyés",
        }

        try:
            status, folder_list = self.mail.list()
            if status == 'OK' and folder_list:
                for item in folder_list:
                    if item is None:
                        continue
                    try:
                        decoded = item.decode('utf-8') if isinstance(item, bytes) else str(item)
                    except Exception:
                        decoded = str(item)

                    # Check for \Sent flag (most reliable)
                    if '\\Sent' in decoded:
                        # Extract folder name: format is (flags) "delimiter" "name"
                        parts = decoded.split('"')
                        if len(parts) >= 4:
                            folder_name = parts[-2]
                        else:
                            folder_name = decoded.rsplit(' ', 1)[-1].strip('"')
                        print(f"Found sent folder via \\Sent flag: '{folder_name}'")
                        self._cached_sent_folder = folder_name
                        return folder_name

                # Fallback: match by known names
                for item in folder_list:
                    if item is None:
                        continue
                    try:
                        decoded = item.decode('utf-8') if isinstance(item, bytes) else str(item)
                    except Exception:
                        decoded = str(item)
                    parts = decoded.split('"')
                    if len(parts) >= 4:
                        folder_name = parts[-2]
                    else:
                        folder_name = decoded.rsplit(' ', 1)[-1].strip('"')

                    if folder_name.lower() in known_sent_names:
                        print(f"Found sent folder by name match: '{folder_name}'")
                        self._cached_sent_folder = folder_name
                        return folder_name

        except Exception as e:
            print(f"Error listing IMAP folders: {e}")

        # Last resort: use static mapping
        fallback = SENT_FOLDERS.get(self.provider, "Sent")
        print(f"Sent folder detection failed, using fallback: '{fallback}'")
        self._cached_sent_folder = fallback
        return fallback

    def _fetch_uids(self, search_criteria, limit=None):
        """Search with criteria and return UIDs (list of bytes for fetch)."""
        status, data = self.mail.uid('search', None, search_criteria)
        if status != 'OK' or not data or data[0] is None:
            return []
        raw = data[0]
        if isinstance(raw, bytes):
            uids = [u for u in raw.split() if u]
        else:
            uids = [u for u in str(raw).split() if u]
        if limit:
            uids = uids[-limit:]
        return [u if isinstance(u, bytes) else u.encode("ascii") for u in uids]

    def _fetch_messages(self, uids):
        """Fetch email messages by UIDs."""
        messages = []
        if not uids:
            return messages
        batch_size = 20
        for i in range(0, len(uids), batch_size):
            batch = uids[i:i + batch_size]
            uid_str = b",".join(b if isinstance(b, bytes) else str(b).encode() for b in batch)
            status, data = self.mail.uid('fetch', uid_str, "(RFC822)")
            if status == 'OK':
                for part in data:
                    if isinstance(part, tuple):
                        try:
                            messages.append(email.message_from_bytes(part[1]))
                        except Exception as e:
                            print(f"Parse error: {e}")
        return messages

    def fetch_mails_by_contact(self, contact_email, limit=15):
        """Fetch last N emails exchanged with a specific contact (inbox + sent)."""
        all_emails = []

        try:
            # Inbox: emails FROM the contact
            self.mail.select("inbox")
            inbox_uids = self._fetch_uids(f'(FROM "{contact_email}")')
            for msg in self._fetch_messages(inbox_uids):
                all_emails.append({"message": msg, "direction": "gelen"})

            # Sent folder: emails TO the contact
            sent_folder = self._find_sent_folder()
            try:
                status, _ = self.mail.select(f'"{sent_folder}"')
            except Exception as e:
                print(f"Sent folder select error ({sent_folder}): {e}")
                status = "NO"

            if status == 'OK':
                sent_uids = self._fetch_uids(f'(TO "{contact_email}")')
                for msg in self._fetch_messages(sent_uids):
                    all_emails.append({"message": msg, "direction": "giden"})
            else:
                print(f"Could not open sent folder '{sent_folder}', status: {status}")

            # Switch back to inbox
            self.mail.select("inbox")

        except Exception as e:
            print(f"Contact fetch error: {e}")
            return all_emails

        # Sort by date (newest first), take last N
        all_emails.sort(
            key=lambda x: email.utils.parsedate_to_datetime(
                x["message"].get("Date", "")
            ) if x["message"].get("Date") else email.utils.parsedate_to_datetime("1 Jan 1970 00:00:00 +0000"),
            reverse=True
        )

        return all_emails[:limit]

    def _extract_email_address(self, header_value):
        """Extract raw email address from a header like 'Name <addr@x.com>'."""
        if not header_value:
            return None
        try:
            decoded_parts = []
            for s, charset in decode_header(header_value):
                if isinstance(s, bytes):
                    decoded_parts.append(s.decode(charset or "utf-8", errors="ignore"))
                else:
                    decoded_parts.append(s)
            full = "".join(decoded_parts)
        except Exception:
            full = str(header_value)

        match = re.search(r'<([^>]+)>', full)
        if match:
            return match.group(1).lower().strip()
        if "@" in full:
            return full.strip().lower()
        return None

    def _extract_email_addresses(self, header_value):
        """Extract all email addresses from a header that may contain 'a@x.com, B <b@y.com>'."""
        if not header_value:
            return []
        try:
            decoded_parts = []
            for s, charset in decode_header(header_value):
                if isinstance(s, bytes):
                    decoded_parts.append(s.decode(charset or "utf-8", errors="ignore"))
                else:
                    decoded_parts.append(s)
            full = "".join(decoded_parts)
        except Exception:
            full = str(header_value)
        out = []
        for segment in full.split(","):
            segment = segment.strip()
            m = re.search(r'<([^>]+)>', segment)
            if m:
                out.append(m.group(1).lower().strip())
            elif "@" in segment:
                out.append(segment.lower().strip())
        return out

    def _parse_date_for_sort(self, date_str):
        """Parse Date header to naive UTC datetime for sorting (so all are comparable)."""
        if not date_str:
            return (datetime.min, date_str)
        try:
            dt = email.utils.parsedate_to_datetime(date_str)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return (dt, date_str)
        except Exception:
            return (datetime.min, date_str)

    def fetch_recent_contacts(self, scan_limit=50, contact_count=10):
        """Scan last N emails; return unique contacts sorted by most recent activity (newest first)."""
        try:
            self.mail.select("inbox")
            uids = self._fetch_uids("ALL")
            uids = uids[-(scan_limit):]
            uids.reverse()

            messages = self._fetch_messages(uids)
            me = self.username.lower()
            # email -> { name, last_date, last_dt, direction }
            by_email = {}

            for msg in messages:
                from_addr = self._extract_email_address(msg.get("From") or "")
                to_addresses = self._extract_email_addresses(msg.get("To") or "")
                date_str = msg.get("Date") or ""
                last_dt, _ = self._parse_date_for_sort(date_str)

                if from_addr and from_addr != me and from_addr not in by_email:
                    from_name = msg.get("From", from_addr)
                    try:
                        parts = []
                        for s, c in decode_header(from_name):
                            if isinstance(s, bytes):
                                parts.append(s.decode(c or "utf-8", errors="ignore"))
                            else:
                                parts.append(s)
                        from_name = "".join(parts)
                    except Exception:
                        from_name = from_addr
                    by_email[from_addr] = {
                        "email": from_addr,
                        "name": from_name,
                        "last_date": date_str,
                        "last_dt": last_dt,
                        "direction": "gelen",
                    }

                for to_addr in to_addresses:
                    if to_addr and to_addr != me and to_addr not in by_email:
                        by_email[to_addr] = {
                            "email": to_addr,
                            "name": to_addr,
                            "last_date": date_str,
                            "last_dt": last_dt,
                            "direction": "giden",
                        }

            # En son mail tarihine göre sırala (yeni önce), sonra ilk contact_count kadar döndür
            sorted_contacts = sorted(
                by_email.values(),
                key=lambda c: c["last_dt"],
                reverse=True,
            )[:contact_count]

            result = [{k: c[k] for k in ("email", "name", "last_date", "direction")} for c in sorted_contacts]
            if not result and messages:
                print(f"Recent contacts: {len(messages)} messages scanned but 0 contacts (check From/To parsing)")
            return result

        except Exception as e:
            import traceback
            print(f"Recent contacts error: {e}")
            traceback.print_exc()
            return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()
        return False

    def close_connection(self):
        if self.mail:
            try:
                self.mail.close()
            except Exception:
                pass
            finally:
                try:
                    self.mail.logout()
                except Exception:
                    pass
                self.mail = None



