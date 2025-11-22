import imaplib
import ssl

from Decorators.Email_decorators import auto_perf_logger
import email
import time
import socket
from concurrent.futures import ThreadPoolExecutor
import threading
DNS_CACHE={}

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

def resolve_imap_host(hostname: str) -> str:
    if hostname not in DNS_CACHE:
        socket.gethostbyname(hostname)   # çöz ama IP'yi kullanma
        DNS_CACHE[hostname] = hostname   # cache'e hostname koy
    return DNS_CACHE[hostname]

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
        print(f"Bağlanılıyor: {self.host} (IPv4 Zorlanmış)...")

        start = time.time()

        try:
            self.mail = ForceIPv4IMAP(self.host, ssl_context=context, timeout=10)
        except Exception as e:
            print(f"Bağlantı hatası: {e}")
            return

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

    def fetch_mails(self, limit=10,from_email=None, to_email=None,date=None):
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

                if status != 'OK':
                    for response_part in data:
                        if isinstance(response_part, tuple):
                            try:
                                msg=email.message_from_bytes(response_part[1])
                                emails.append(msg)
                            except Exception as e:
                                print("parse hatası",e)

            return emails
        except Exception as e:
            print(f"Fetch error: {e}")
            return emails

    def close_connection(self):
        if self.mail:
            self.mail.close()
            self.mail.logout()



