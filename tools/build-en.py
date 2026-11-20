"""Собирает en/index.html из русского index.html.

Тексты берутся из атрибутов data-en, остальное задаётся ниже.
Запуск из корня репозитория: python tools/build-en.py
"""
import html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
DST = ROOT / "en" / "index.html"
SITE = "https://gregory-bondarenko.ru"

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

ATTR_EN = {
    "Сертификат": "Certificate",
    "Разделы": "Sections",
    "Меню": "Menu",
    "Мобильное меню": "Mobile menu",
    "Ключевые навыки": "Key skills",
    "Следующее фото": "Next photo",
    "Григорий Бондаренко": "Gregory Bondarenko",
    "Фото 1": "Photo 1",
    "Фото 2": "Photo 2",
    "Фото 3": "Photo 3",
}

HEAD = {
    "title": "Gregory Bondarenko — Data Analyst | RANEPA | IT",
    "author": "Gregory Bondarenko",
    "description": "Gregory Bondarenko, data analyst at MTS Web Services, Moscow. Python, SQL, PySpark, BI, A/B testing. RANEPA student (Applied Informatics, Data Science), Changellenge Cup IT finalist",
    "keywords": "Gregory Bondarenko, data analyst, data analyst Moscow, data analyst portfolio, RANEPA, MTS, Python, SQL, PySpark, BI, A/B testing",
    "og_title": "Gregory Bondarenko — Data Analyst",
    "og_desc": "Data analyst at MTS Web Services. Python, SQL, BI, A/B. RANEPA student, Changellenge Cup IT finalist",
    "tw_desc": "Data analyst at MTS Web Services. Python, SQL, BI, A/B. Changellenge Cup IT finalist",
}

JSONLD_EN = {
    "name": "Gregory Bondarenko",
    "alternateName": "Григорий Бондаренко",
    "alumniOf": {"@type": "CollegeOrUniversity", "name": "RANEPA, Russian Presidential Academy of National Economy and Public Administration"},
    "url": SITE + "/en/",
    "address": {"@type": "PostalAddress", "addressLocality": "Moscow", "addressCountry": "RU"},
}


class Spans(HTMLParser):
    """Находит внутренние диапазоны элементов с data-en."""

    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.lines = [0]
        for line in text.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(line))
        self.stack, self.spans = [], []

    def abspos(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        start = self.abspos() + len(self.get_starttag_text())
        self.stack.append((tag, start, dict(attrs).get("data-en")))

    def handle_endtag(self, tag):
        while self.stack:
            t, start, en = self.stack.pop()
            if t == tag:
                if en is not None:
                    self.spans.append((start, self.abspos(), en))
                break


def sub1(pattern, repl, text, flags=0):
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n != 1:
        sys.exit(f"Не найдено: {pattern}")
    return new


def main():
    s = SRC.read_text(encoding="utf-8")

    p = Spans(s)
    p.feed(s)
    for start, end, en in sorted(p.spans, reverse=True):
        s = s[:start] + en + s[end:]
    s = re.sub(r'\s+data-(?:ru|en)="[^"]*"', "", s)

    for ru, en in ATTR_EN.items():
        s = s.replace(f'"{ru}"', f'"{en}"')

    s = sub1(r'<html lang="ru">', '<html lang="en">', s)
    s = sub1(r"<title>.*?</title>", f"<title>{HEAD['title']}</title>", s)
    s = sub1(r'(<meta name="author" content=")[^"]*', r"\g<1>" + HEAD["author"], s)
    s = sub1(r'(<meta name="description" content=")[^"]*', r"\g<1>" + HEAD["description"], s)
    s = sub1(r'(<meta name="keywords" content=")[^"]*', r"\g<1>" + HEAD["keywords"], s)
    s = sub1(r'(<meta property="og:title" content=")[^"]*', r"\g<1>" + HEAD["og_title"], s)
    s = sub1(r'(<meta property="og:description" content=")[^"]*', r"\g<1>" + HEAD["og_desc"], s)
    s = sub1(r'(<meta name="twitter:title" content=")[^"]*', r"\g<1>" + HEAD["og_title"], s)
    s = sub1(r'(<meta name="twitter:description" content=")[^"]*', r"\g<1>" + HEAD["tw_desc"], s)
    s = sub1(r'<meta property="og:url" content="[^"]*"', f'<meta property="og:url" content="{SITE}/en/"', s)
    s = sub1(r'<meta property="og:locale" content="ru_RU"/>\n<meta property="og:locale:alternate" content="en_US"/>',
             '<meta property="og:locale" content="en_US"/>\n<meta property="og:locale:alternate" content="ru_RU"/>', s)
    s = s.replace(f"{SITE}/og-preview.png", f"{SITE}/og-preview-en.png")
    s = sub1(r'<link rel="canonical" href="[^"]*"', f'<link rel="canonical" href="{SITE}/en/"', s)

    def fix_ld(m):
        data = json.loads(m.group(1))
        data.update(JSONLD_EN)
        return '<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False, indent=2) + "\n</script>"
    s = sub1(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', fix_ld, s, re.S)

    s = sub1(r'<a class="lang-btn" id="langToggle"[^>]*>EN</a>',
             '<a class="lang-btn" id="langToggle" href="/" hreflang="ru" lang="ru" aria-label="Русская версия">RU</a>', s)

    s = s.replace('href="cv.pdf"', 'href="/cv-en.pdf"')
    s = re.sub(r'(href|src)="(img|fonts)/', r'\1="/\2/', s)
    s = re.sub(r"url\(fonts/", "url(/fonts/", s)
    s = re.sub(r"'img/", "'/img/", s)
    s = s.replace('href="favicon.ico"', 'href="/favicon.ico"')

    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)
    left = [m.strip() for m in re.findall(r">([^<]*[А-Яа-яЁё][^<]*)<", body)]
    left += re.findall(r'(?:alt|title|aria-label|content)="([^"]*[А-Яа-яЁё][^"]*)"', body)
    allowed = {"Русская версия"}
    left = [x for x in left if x not in allowed]
    if left:
        sys.exit("Остался русский текст:\n" + "\n".join(left))

    DST.parent.mkdir(exist_ok=True)
    DST.write_text(s, encoding="utf-8")
    print(f"Готово: {DST.relative_to(ROOT)}, {len(s.encode()) // 1024} КБ")


if __name__ == "__main__":
    main()
