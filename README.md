# Auris — Proje Tanıtım Sitesi

Akıllı Trafik Akış Simülasyonu ve Yol Tasarım Karar Destek Sistemi projesinin
kamuya açık tanıtım sitesi. Statik site: derleme adımı yok, bağımlılık yok.

## Dosya düzeni

```
index.html          Tüm içerik tek sayfada
styles.css          Stiller
script.js           Ağ şeması etkileşimi + mobil menü
vercel.json         Vercel yapılandırması
assets/             Mimari diyagramlar
assets/takim/       Takım fotoğrafları (siz ekleyeceksiniz)
raporlar/           Rapor PDF/DOCX dosyaları (siz ekleyeceksiniz)
```

## Yayına almadan önce yapılacaklar

1. **Raporları ekleyin** — `raporlar/` klasörüne, o klasördeki not dosyasında
   yazan adlarla PDF ve DOCX dosyalarını koyun.
2. **Takım fotoğraflarını ekleyin** — `assets/takim/` klasörüne `beril.jpg`,
   `kaan.jpg`, `duygu.jpg`, `yanki.jpg`. Fotoğraf yoksa site baş harfleri gösterir.
3. **LinkedIn bağlantılarını doldurun** — `index.html` içinde `class="uye-link"`
   olan dört bağlantının `href="#"` değerini kendi profil adreslerinizle değiştirin.
4. **Danışman adını yazın** — `index.html` içinde `class="danisman-ad"` olan
   satırdaki `—` işaretini danışmanınızın adıyla değiştirin.
5. **E-posta ve GitHub adresini güncelleyin** — İletişim bölümündeki
   `mailto:` adresini ve GitHub bağlantısını kendi adreslerinizle değiştirin.

## Yerelde önizleme

```bash
python3 -m http.server 8000
```

Ardından tarayıcıdan `http://localhost:8000` adresini açın.

## Vercel ile yayına alma

1. Bu klasörü bir GitHub deposuna yükleyin.
2. [vercel.com](https://vercel.com) adresinde GitHub hesabınızla giriş yapın.
3. **Add New → Project** deyip depoyu seçin.
4. Framework Preset: **Other**. Build ve Output ayarlarına dokunmayın.
5. **Deploy** deyin.

Vercel otomatik olarak HTTPS'li bir adres verir
(`proje-adi.vercel.app`). Depoya her `git push` yaptığınızda site kendini günceller.
