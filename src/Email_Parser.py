import re
from Email_Receiver import EmailReceiver
import email as email_module
import time
from bs4 import BeautifulSoup
from Decorators.Email_parser_decorator import auto_perf_logger
from email.header import decode_header

@auto_perf_logger
class EmailParser:
    def __init__(self,address,password):
        self.address = address
        self.password = password
        self.email_receiver = EmailReceiver(self.address,self.password)
        self.emails = self.email_receiver.fetch_mails(100)
        print("MAİL SAYISI:", len(self.emails))

    def parse(self):
        print("Parsing emails")
        start = time.time()
        for index,mail_item in enumerate(self.emails):
            #print("Parsing mail", index)
            #print("-------------------------------------------")
            #print("Subject:", self.parse_subject(mail_item))
            #print("Date:", mail_item['Date'])
            #print("From:", mail_item['From'])
            #print("To:", mail_item['To'])
            #print("Body:",self.parse_body(mail_item))
            full_text = f"Subject: {self.parse_subject(mail_item)}\nDate: {mail_item['Date']}\nTo: {self.parse_address(mail_item['To'])}\nFrom: {mail_item['From']}\nBody: {self.parse_body(mail_item)}"
            yield {
                "subject": self.parse_subject(mail_item),
                "date": mail_item['Date'],
                "from": mail_item['From'],
                "to": self.parse_address(mail_item["To"]),
                "body": self.parse_body(mail_item)
            }


        end = time.time()
        print(f"TIME ELAPSED {end-start}")

    def parse_address(self,header_value):
        try:
            decoded_parts = decode_header(header_value)
            parts = []
            for s, charset in decoded_parts:
                if isinstance(s, bytes):
                    charset = charset or "utf-8"
                    parts.append(s.decode(charset, errors="ignore"))
                else:
                    parts.append(s)
            return "".join(parts)
        except Exception:
            return header_value

    def parse_subject(self,mail_item):

        try:
            print("Parsing subjects")
            decoded_subject = email_module.header.decode_header(mail_item['Subject'])

            subject_parts = []
            for s, c in decoded_subject:
                # s'nin tipi bytes ise (b'...') çöz, değilse (string ise) direkt kullan.
                if isinstance(s, bytes):
                    # Charset yoksa 'utf-8' varsay
                    charset = c or 'utf-8'
                    subject_parts.append(s.decode(charset, errors='ignore'))
                else:
                    subject_parts.append(s)

            subject_str = "".join(subject_parts)

            return subject_str

        except Exception as e:
            print(f"Subject (Hata Çözülemedi): {mail_item.get('Subject', '(Yok)')}")

    def parse_body(self, mail_item):
        html_content = None
        plain_content = None

        if mail_item.is_multipart():
            for part in mail_item.walk():
                if part.get_content_maintype() == 'multipart':
                    continue

                # Content-Disposition kontrolü (ekleri atlamak için)
                cd = part.get('Content-Disposition')
                if cd:
                    if cd.startswith('attachment'):
                        continue

                content_type = part.get_content_type()

                try:
                    payload = part.get_payload(decode=True).decode("utf-8", errors="ignore").strip()
                except UnicodeDecodeError:
                    print("decode error")

                if content_type == "text/html":
                    html_content = payload

                elif content_type == "text/plain":
                    if not plain_content:
                        plain_content = payload

        if html_content:
            return self.html_to_clean_text(html_content)

        # 2. Öncelik: HTML yoksa, düz metni kullan.
        # NOT: Bazı e-postalarda düz metin parçası bile HTML kalıntıları içerebilir, bu yüzden ona da temizlik uygulayalım.
        if plain_content:
            # Düz metin parçasında HTML kalıntıları varsa temizler
            return self.html_to_clean_text(plain_content)

            # 3. Öncelik: Tek parçalı e-posta ise (multipart değilse)
        else:
            try:
                payload = mail_item.get_payload(decode=True).decode('utf-8', errors='ignore').strip()
                # Tek parça gövdeye de temizlik uygulayalım
                return self.html_to_clean_text(payload)
            except Exception:
                return "error"

    def html_to_clean_text(self,html):
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        # script/style gibi gereksiz şeyleri kaldır
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # tablolar, td, tr vs. tamamen text’e dönüşür
        text = soup.get_text(separator=" ")
        invisible_chars = r'[\xad\u200b\u200c\u200d\uFEFF]'
        text = re.sub(invisible_chars, '', text)

        # &nbsp; temizle
        text = text.replace("\xa0", " ")

        # fazla boşlukları düzelt
        text = re.sub(r"\s+", " ", text)


        return text.strip()



#start=time.time()
#email_parser = EmailParser("kaangulergs@gmail.com", "ioue gqpu aekc zcbj")
#for mail in email_parser.parse():
#    print(mail)
#end=time.time()
#print(f"TOTAL TIME ELAPSED {end-start}")
