
(function () {
  "use strict";

  /* ---------- 1. Yol ağı şeması ---------- */

  // Kavşak noktaları
  var dugumler = [
    { id: "n1",  x:  55, y:  55 }, { id: "n2",  x: 175, y:  48 },
    { id: "n3",  x: 300, y:  58 }, { id: "n4",  x: 430, y:  50 },
    { id: "n5",  x:  62, y: 165 }, { id: "n6",  x: 182, y: 158 },
    { id: "n7",  x: 305, y: 168 }, { id: "n8",  x: 438, y: 160 },
    { id: "n9",  x:  70, y: 278 }, { id: "n10", x: 190, y: 285 },
    { id: "n11", x: 312, y: 276 }, { id: "n12", x: 445, y: 282 }
  ];

  // Yol segmentleri. y = yoğunluk (0 akıcı … 1 sıkışık)
  //   base: mevcut durum · mud: müdahale sonrası
  var kenarlar = [
    { a: "n1",  b: "n2",  base: .30, mud: .34 },
    { a: "n2",  b: "n3",  base: .55, mud: .48 },
    { a: "n3",  b: "n4",  base: .40, mud: .44 },
    { a: "n5",  b: "n6",  base: .82, mud: .30 },   // müdahale edilen arter
    { a: "n6",  b: "n7",  base: .95, mud: .28 },   // müdahale edilen arter
    { a: "n7",  b: "n8",  base: .88, mud: .35 },
    { a: "n9",  b: "n10", base: .35, mud: .62 },   // yük buraya kayar
    { a: "n10", b: "n11", base: .30, mud: .78 },   // yeni darboğaz
    { a: "n11", b: "n12", base: .38, mud: .58 },
    { a: "n1",  b: "n5",  base: .45, mud: .40 },
    { a: "n5",  b: "n9",  base: .28, mud: .52 },
    { a: "n2",  b: "n6",  base: .72, mud: .42 },
    { a: "n6",  b: "n10", base: .40, mud: .68 },
    { a: "n3",  b: "n7",  base: .85, mud: .38 },
    { a: "n7",  b: "n11", base: .33, mud: .60 },
    { a: "n4",  b: "n8",  base: .50, mud: .45 },
    { a: "n8",  b: "n12", base: .30, mud: .44 },
    { a: "n2",  b: "n7",  base: .62, mud: .36 }
  ];

  // Yeni darboğazın işaretleneceği kavşak
  var UYARI_DUGUM = "n10";

  var olcumler = {
    base: { gecikme: "45 sn", sure: "1.284 dk", sikisik: "7 / 18" },
    mud:  { gecikme: "28 sn", sure: "1.121 dk", sikisik: "2 / 18" }
  };

  var svg = document.getElementById("ag");
  if (!svg) return;

  var kenarKat = document.getElementById("kenarlar");
  var dugumKat = document.getElementById("dugumler");
  var rozetKat = document.getElementById("rozet");
  var NS = "http://www.w3.org/2000/svg";

  function bul(id) {
    for (var i = 0; i < dugumler.length; i++) {
      if (dugumler[i].id === id) return dugumler[i];
    }
    return null;
  }

  // Yoğunluğu renge çevirir: yeşil - amber - koyu kırmızı
  function renk(y) {
    if (y < 0.45) return "#1B8E63";
    if (y < 0.70) return "#D99A0B";
    return "#B93B26";
  }

  // Kenarları çiz
  var cizgiler = [];
  kenarlar.forEach(function (k) {
    var a = bul(k.a), b = bul(k.b);
    var l = document.createElementNS(NS, "line");
    l.setAttribute("x1", a.x); l.setAttribute("y1", a.y);
    l.setAttribute("x2", b.x); l.setAttribute("y2", b.y);
    l.setAttribute("class", "kenar");
    l.setAttribute("stroke", renk(k.base));
    kenarKat.appendChild(l);
    cizgiler.push({ el: l, veri: k });
  });

  // Düğümleri çiz
  dugumler.forEach(function (d) {
    var c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", d.x); c.setAttribute("cy", d.y);
    c.setAttribute("r", 5.5);
    c.setAttribute("class", "dugum");
    dugumKat.appendChild(c);
  });

  // Kural tabanlı uyarı pini 
  var up = bul(UYARI_DUGUM);
  var pin = document.createElementNS(NS, "g");
  pin.setAttribute("class", "uyari-pin");

  var halka = document.createElementNS(NS, "circle");
  halka.setAttribute("cx", up.x); halka.setAttribute("cy", up.y - 26);
  halka.setAttribute("r", 11);
  halka.setAttribute("class", "uyari-halka");

  var daire = document.createElementNS(NS, "circle");
  daire.setAttribute("cx", up.x); daire.setAttribute("cy", up.y - 26);
  daire.setAttribute("r", 10);

  var yazi = document.createElementNS(NS, "text");
  yazi.setAttribute("x", up.x); yazi.setAttribute("y", up.y - 22);
  yazi.textContent = "!";

  var baslik = document.createElementNS(NS, "title");
  baslik.textContent =
    "Darboğaz uyarısı: bu kavşakta yoğunluk %30 eşiğini aştı.";

  pin.appendChild(halka); pin.appendChild(daire);
  pin.appendChild(yazi);  pin.appendChild(baslik);
  rozetKat.appendChild(pin);

  // Senaryo değiştir
  var alanGecikme = document.getElementById("m-gecikme");
  var alanSure    = document.getElementById("m-sure");
  var alanSikisik = document.getElementById("m-sikisik");

  function uygula(durum) {
    var mud = durum === "mudahale";

    cizgiler.forEach(function (c) {
      var y = mud ? c.veri.mud : c.veri.base;
      c.el.setAttribute("stroke", renk(y));
      c.el.setAttribute("stroke-width", (5.5 + y * 4).toFixed(1));
    });

    pin.classList.toggle("gorunur", mud);

    var o = mud ? olcumler.mud : olcumler.base;
    alanGecikme.textContent = o.gecikme;
    alanSure.textContent    = o.sure;
    alanSikisik.textContent = o.sikisik;

    [alanGecikme, alanSure, alanSikisik].forEach(function (el) {
      el.classList.toggle("iyilesme", mud);
    });
  }

  uygula("base");

  var dugmeler = document.querySelectorAll(".anahtar-dugme");
  Array.prototype.forEach.call(dugmeler, function (d) {
    d.addEventListener("click", function () {
      Array.prototype.forEach.call(dugmeler, function (x) {
        x.classList.remove("etkin");
        x.setAttribute("aria-pressed", "false");
      });
      d.classList.add("etkin");
      d.setAttribute("aria-pressed", "true");
      uygula(d.dataset.durum);
    });
  });

  /* ---------- 2. Mobil menü ---------- */

  var acKapa = document.querySelector(".menu-dugme");
  var menu = document.querySelector(".menu");

  if (acKapa && menu) {
    acKapa.addEventListener("click", function () {
      var acik = menu.classList.toggle("acik");
      acKapa.setAttribute("aria-expanded", acik ? "true" : "false");
      acKapa.setAttribute("aria-label", acik ? "Menüyü kapat" : "Menüyü aç");
    });

    menu.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        menu.classList.remove("acik");
        acKapa.setAttribute("aria-expanded", "false");
        acKapa.setAttribute("aria-label", "Menüyü aç");
      }
    });
  }
})();
