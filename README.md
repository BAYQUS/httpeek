<p align="center">
  <img src="assets/logo.png" alt="httpeek logo" width="680">
</p>

<h1 align="center">httpeek</h1>
<p align="center">
  No rainbow gradients. No fireworks. Just a practical HTTP checker that tells you what's up.
</p>

<p align="center">
  <a href="#en--english">English</a> ·
  <a href="#tr--türkçe">Türkçe</a> ·
  <a href="#az--azərbaycanca">Azərbaycanca</a> ·
  <a href="#ru--русский">Русский</a> ·
  <a href="#ar--العربية">العربية</a>
</p>

---

## EN · English

### What is this?
**httpeek** is a small, fast HTTP probe. It figures out: status codes, page titles, sizes, redirect chains, and (optionally) TLS certificate bits. It also gives you a strong hint when Cloudflare sits in front of a host—using DNS (NS/CNAME) and HTTP headers. Think “signal first, glitter later.”

> Part of something bigger: this is one module of a much larger security recon framework I’m building. **httpeek** is the “HTTP scanner” piece. The framework will orchestrate modules (subdomain, port, HTTP, content, report…) into one workflow. Baby steps; big plans.

**Author:** Bayqus · **Email:** <bayqussec@gmail.com> · **GitHub:** <https://github.com/BAYQUS>

### What it can do (today)
- Check many hosts concurrently (threads).
- Follow redirects and summarize the chain (with manual fallback up to 10 hops when needed).
- Filter by **status code**, **content length**, **title/body regex**.
- Resolve IP, show content size, show last redirect host.
- Optional **TLS** certificate info (`--tls-info`).
- Cloudflare detection via **DNS + headers** (no brittle IP-range lists).
- Export to **JSON/CSV** for your pipelines. Proxies & random UA supported.

### Install
**System-wide installer**
```bash
sudo bash scripts/install.sh
# Installs code + venv to /usr/share/httpeek and a wrapper to /usr/bin/httpeek
```

**pipx (user-level)**
```bash
pipx install .
httpeek --help
```

**Dev (venv)**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

> Debian/Kali note (PEP 668): prefer **venv** or **pipx** over system pip.

### Usage (snacks)
```bash
# One target
httpeek -u https://example.com

# List with more threads
httpeek -l hosts.txt --threads 200

# From stdin, export JSON
cat hosts.txt | httpeek --stdin --json
```

**Flags you’ll actually use**
```
-u/--url | -l/--list | --stdin
--threads N (default 50) | --timeout S | --retries N
--random-agent | --proxy http://127.0.0.1:8080
--method {GET,HEAD} | --no-redirect
-sc 2xx,301-302 | -cl 1024-4096
--title-match REGEX | --body-match REGEX
--only-active | --tls-info | --json | --csv
```

### Output (short tour)
Columns: **URL** · **IP** · **Status** · **Title** (adds `[CF]` when likely) · **Redirect** (`→ hops • final-host`).  
`--json` prints one object per line; `--csv` prints `url,ip,status,length,"title"`.

### Planned for v1.1.1 (soon-ish)
- HTTP/2/ALPN hints and response time column.
- Optional screenshot probe (headless, opt‑in; useful for triage).
- SQLite export (because grepping giant JSON hurts).
- Smarter title/body extraction on JS-heavy pages.
- Rate limit/backoff knobs (be a good netizen).

### Troubleshooting
- Banner on help/usage is intentional. We like a little flair before facts.  
- “No module named httpeek”? Use a wrapper that runs the file directly:
```bash
sudo tee /usr/bin/httpeek >/dev/null <<'WRAP'
#!/usr/bin/env bash
exec /usr/share/httpeek/.venv/bin/python /usr/share/httpeek/httpeek.py "$@"
WRAP
sudo chmod +x /usr/bin/httpeek
```
- Kali / PEP 668: use **venv** or **pipx**. Your OS will thank you.

---

## TR · Türkçe

### Bu ne işe yarıyor?
**httpeek** küçük ve hızlı bir HTTP yoklayıcısı. Durum kodu, sayfa başlığı, içerik boyutu, yönlendirme zinciri ve istersen TLS sertifika bilgilerini çıkarır. Ayrıca DNS (NS/CNAME) ve HTTP başlıklarına bakarak **Cloudflare** önde mi değil mi, ona dair kuvvetli bir ipucu verir. Kısaca: **süs değil, bilgi**.

> Daha büyük resim: Bu araç aslında geliştirmekte olduğum **daha kapsamlı bir güvenlik keşif çerçevesinin** tek bir modülü. httpeek o çerçevenin “HTTP tarayıcı” parçası. Hedef; alt alan, port, HTTP, içerik ve raporlama modüllerini tek akışta birleştirmek. Adım adım, sağlam ilerliyoruz.

**Yazar:** Bayqus · **E‑posta:** <bayqussec@gmail.com> · **GitHub:** <https://github.com/BAYQUS>

### Şu an neler yapıyor?
- Bir sürü hedefi aynı anda kontrol eder (thread’ler).
- Yönlendirmeleri takip edip zinciri özetler (gerekirse 10 adıma kadar manuel fallback).
- **Durum kodu**, **içerik uzunluğu**, **başlık/gövde regex** filtreleri.
- IP çözümleme, içerik boyutu, son yönlendirilen host bilgisi.
- İsteğe bağlı **TLS** sertifika bilgisi (`--tls-info`).
- **Cloudflare** tespiti için **DNS + başlık** ipuçları (IP blok listesi yok).
- **JSON/CSV** çıktı; proxy ve rastgele User‑Agent desteği.

### Kurulum
**Sistem geneli kurulum**
```bash
sudo bash scripts/install.sh
# Kod + venv: /usr/share/httpeek, kısayol: /usr/bin/httpeek
```

**pipx (kullanıcı)**
```bash
pipx install .
httpeek --help
```

**Geliştirme (venv)**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

> Debian/Kali: sistem pip yerine **venv** ya da **pipx** kullanın.

### Kullanım (kısaca)
```bash
httpeek -u https://example.com
httpeek -l hosts.txt --threads 200
cat hosts.txt | httpeek --stdin --json
```

**Sık kullanılan bayraklar**
```
-u/--url | -l/--list | --stdin
--threads N (varsayılan 50) | --timeout S | --retries N
--random-agent | --proxy http://127.0.0.1:8080
--method {GET,HEAD} | --no-redirect
-sc 2xx,301-302 | -cl 1024-4096
--title-match REGEX | --body-match REGEX
--only-active | --tls-info | --json | --csv
```

### Çıktı (kısa tur)
Sütunlar: **URL** · **IP** · **Status** · **Title** (Cloudflare olasıysa `[CF]`) · **Redirect** (`→ adım • son-host`).  
`--json` satır başına bir nesne; `--csv` `url,ip,status,length,"title"`.

### v1.1.1 için planlananlar
- HTTP/2/ALPN ipuçları ve yanıt süresi sütunu.
- İsteğe bağlı ekran görüntüsü alma (headless, triage için faydalı).
- SQLite’a dışa aktarma.
- JS ağırlıklı sayfalarda daha akıllı başlık/gövde çıkarımı.
- Hız sınırlama/geri çekilme ayarları (rate limit/backoff).

### Sorun giderme
- Yardım/usage ekranında banner bilerek görünüyor—önce küçük selam, sonra iş.  
- “No module named httpeek”? Dosyayı doğrudan çalıştıran kısayolu kullanın (yukarıdaki blok).  
- Kali / PEP 668: **venv** veya **pipx** iyi arkadaşınız.

---

## AZ · Azərbaycanca

### Bu nədir?
**httpeek** sürətli və yüngül HTTP yoxlayıcıdır. Status kodlarını, səhifə başlığını, kontentin ölçüsünü, yönləndirmə zəncirini çıxarır; istəyə bağlı **TLS** sertifikat məlumatını göstərir. **Cloudflare** önündədirsə, bunu **DNS (NS/CNAME)** və **HTTP başlıqları** əsasında güclü ehtimalla bildirir. Qısası: bəzək yox, **faydalı məlumat**.

> Daha böyük layihənin hissəsi: **httpeek** qurmaqda olduğum daha geniş təhlükəsizlik kəşfiyyat çərçivəsinin tək bir moduludur. Bu modul “HTTP skaneri”dir. Məqsəd — alt domen, port, HTTP, məzmun və hesabat modullarını tək axında birləşdirmək. Addım‑addım, amma məqsəd böyükdür.

**Müəllif:** Bayqus · **E‑poçt:** <bayqussec@gmail.com> · **GitHub:** <https://github.com/BAYQUS>

### Nələri bacarır?
- Çoxlu hədəfi eyni anda yoxlayır (thread‑lər).
- Yönləndirmələri izləyib zənciri xülasə edir (lazım olsa 10 “hop”a qədər manual fallback).
- **Status**, **content‑length**, **title/body regex** filtrləri.
- IP, kontent ölçüsü, son yönləndirilən host göstərilir.
- İstəyə bağlı **TLS** məlumatı (`--tls-info`).
- **Cloudflare** aşkarlanması **DNS + başlıqlar** ilə (IP diapazon siyahıları yoxdur).
- **JSON/CSV** çıxışı; proxy və təsadüfi User‑Agent dəstəyi.

### Quraşdırma
**Sistem səviyyəsində**
```bash
sudo bash scripts/install.sh
# Kod + venv: /usr/share/httpeek, qısayol: /usr/bin/httpeek
```

**pipx (istifadəçi)**
```bash
pipx install .
httpeek --help
```

**İnkişaf (venv)**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

> Debian/Kali: sistem pip əvəzinə **venv** və ya **pipx** istifadə edin.

### İstifadə (qısa)
```bash
httpeek -u https://example.com
httpeek -l hosts.txt --threads 200
cat hosts.txt | httpeek --stdin --json
```

**Lazımlı bayraqlar**
```
-u/--url | -l/--list | --stdin
--threads N (susmaya görə 50) | --timeout S | --retries N
--random-agent | --proxy http://127.0.0.1:8080
--method {GET,HEAD} | --no-redirect
-sc 2xx,301-302 | -cl 1024-4096
--title-match REGEX | --body-match REGEX
--only-active | --tls-info | --json | --csv
```

### Çıxış
Sütunlar: **URL** · **IP** · **Status** · **Title** (Cloudflare ehtimalı varsa `[CF]`) · **Redirect** (`→ addım • son host`).  
`--json` hər sətrə bir obyekt; `--csv` `url,ip,status,length,"title"`.

### v1.1.1 üçün planlar
- HTTP/2/ALPN ipucları və cavab vaxtı sütunu.
- Seçimli ekran görüntüsü (headless) — ilkin baxış üçün faydalı.
- SQLite ixracı.
- JS‑ə bağlı səhifələrdə daha ağıllı başlıq/mətn çıxarışı.
- Sürət məhdudiyyəti/geri çəkilmə (rate limit/backoff) tənzimləmələri.

### Problemlərin həlli
- Help/usage ekranında banner məqsədlidir — əvvəl salam, sonra iş.  
- “No module named httpeek”? Faylı birbaşa işlədən qısayoldan istifadə edin (yuxarıdakı blok).  
- Kali / PEP 668: **venv** və ya **pipx** əlverişlidir.

---

## RU · Русский

### Что это?
**httpeek** — небольшой и быстрый HTTP‑проверщик. Он получает коды состояния, заголовок страницы, размер, цепочку редиректов и при желании данные TLS‑сертификата. Также по DNS (NS/CNAME) и HTTP‑заголовкам подсказывает, стоит ли перед сайтом Cloudflare. Ставим на первое место полезную информацию, а не «фейерверки».

> Часть большего проекта: это один модуль большого фреймворка для рекогносцировки, над которым я работаю. **httpeek** — модуль «HTTP‑сканер». Идея — связать модули (сабдомены, порты, HTTP, контент, отчёты) в единый конвейер. Медленно, но верно.

**Автор:** Bayqus · **Почта:** <bayqussec@gmail.com> · **GitHub:** <https://github.com/BAYQUS>

### Что умеет сейчас
- Параллельные проверки (threads).
- Следует за редиректами и кратко показывает цепочку (fallback до 10 шагов).
- Фильтры по **коду**, **длине**, **regex** для title/body.
- IP, размер, конечный хост редиректа.
- Опциональные данные **TLS** (`--tls-info`).
- Обнаружение **Cloudflare** по **DNS + заголовкам** (без списков IP‑диапазонов).
- Вывод **JSON/CSV**, поддержка прокси и случайного User‑Agent.

### Установка
```bash
sudo bash scripts/install.sh
pipx install .
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e .
```

### Использование
```bash
httpeek -u https://example.com
httpeek -l hosts.txt --threads 200
cat hosts.txt | httpeek --stdin --json
```

### План на v1.1.1
См. EN/TR/AZ — пункты идентичны.

---

## AR · العربية
<div dir="rtl">

### ما هذا؟
**httpeek** أداة خفيفة وسريعة لفحص HTTP. تعرض كود الحالة، عنوان الصفحة، الحجم، سلسلة التحويلات، وبشكل اختياري معلومات شهادة TLS. كما تُلمّح لوجود **Cloudflare** بالاعتماد على **DNS (NS/CNAME)** ورؤوس **HTTP**. الفكرة بسيطة: معلومات مفيدة أولاً، بلا زينة زائدة.

> جزء من مشروع أكبر: هذه الأداة مجرد وحدة من إطار عمل أكبر للاستطلاع الأمني أعمل عليه. **httpeek** هي وحدة “فحص HTTP”. الهدف ربط وحدات (النطاقات الفرعية، المنافذ، HTTP، المحتوى، التقارير) في خط واحد. خطوة بخطوة، لكن بخطة كبيرة.

**المؤلف:** Bayqus · **البريد:** <a href="mailto:bayqussec@gmail.com">bayqussec@gmail.com</a> · **GitHub:** <a href="https://github.com/BAYQUS">github.com/BAYQUS</a>

### ماذا تفعل الآن؟
- فحص متوازي لعدد كبير من العناوين.
- متابعة التحويلات مع تلخيص السلسلة (حتى 10 قفزات عند الحاجة).
- مرشحات للكود، طول المحتوى، و regex للعنوان/المحتوى.
- إظهار IP والحجم والمضيف النهائي في التحويل.
- معلومات **TLS** اختيارية (`--tls-info`).
- ترجيح **Cloudflare** عبر **DNS + الرؤوس** (دون قوائم نطاقات IP).
- مخرجات **JSON/CSV**، ودعم الوكيل و User‑Agent عشوائي.

### التثبيت والاستخدام
```bash
sudo bash scripts/install.sh
pipx install .
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e .
httpeek -l hosts.txt --threads 200
```

### المخطط لـ v1.1.1
- تلميحات HTTP/2/ALPN وعمود زمن الاستجابة.
- التقاط لقطة للشاشة (headless، اختياري).
- تصدير إلى SQLite.
- استخراج أذكى للعنوان/المحتوى في الصفحات الثقيلة بـ JS.
- إعدادات للـ rate‑limit/backoff.

</div>

---

### License
MIT • Please keep attribution when redistributing.

### Contact
**Bayqus** — <bayqussec@gmail.com> — <https://github.com/BAYQUS>

