/* Textgrafik für den Seitenkopf: NAS, OCuLink-Kabel, Dock mit Karte. Mit Licht gemalt, dann gerastert (Baustein textgrafik.js).
   Das NAS ist nach der Frontansicht des iDX6011 Pro gezeichnet: sechs nummerierte Einschübe, Anzeige rechts, Leiste mit Anschlüssen. */
function Anlage(canvas, s) {
  // Tonleitern Grund, Bernstein und Stahl, dazu vier Töne für die Anzeige. Salbei fehlt mit Absicht: mittlere Grautöne fielen sonst ins Grünliche.
  var P = Textgrafik.PALETTEN.workbench, palette = P.slice(0, 17).concat(P.slice(22, 27), ['c7a854', 'e4cd85', '9a5b50', 'c07f73']);
  var tg = Textgrafik.erzeuge({ spalten: 344, zeilen: 112, palette: palette, grund: '0d0c0b', koernung: false });
  tg.neu();
  var S = tg.szene.getContext('2d'), Li = tg.licht.getContext('2d'), W = 688, H = 224;
  function verlauf(x0, y0, x1, y1, stufen) { var g = S.createLinearGradient(x0, y0, x1, y1); stufen.forEach(function (p) { g.addColorStop(p[0], p[1]); }); return g; }
  function kasten(x, y, w, h, a, b, senkrecht) { S.fillStyle = verlauf(x, y, senkrecht ? x : x + w, senkrecht ? y + h : y, [[0, a], [1, b]]); S.fillRect(x, y, w, h); }
  function leuchte(x, y, r, farbe, staerke) { var g = Li.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, farbe); g.addColorStop(1, 'rgba(0,0,0,0)'); Li.globalAlpha = staerke; Li.fillStyle = g; Li.fillRect(x - r, y - r, 2 * r, 2 * r); Li.globalAlpha = 1; }

  // Raum und Boden
  S.fillStyle = verlauf(0, 0, 0, H, [[0, '#0d0c0b'], [.55, '#151413'], [.80, '#1a1918'], [.81, '#2b2827'], [1, '#151413']]); S.fillRect(0, 0, W, H);
  S.strokeStyle = '#3a3634'; S.lineWidth = 1;
  for (var i = -8; i <= 20; i++) { S.beginPath(); S.moveTo(W / 2 + (i - 6) * 26, 182); S.lineTo(W / 2 + (i - 6) * 70, H); S.stroke(); }
  for (var j = 0; j < 4; j++) { S.beginPath(); S.moveTo(0, 188 + j * j * 4 + j * 5); S.lineTo(W, 188 + j * j * 4 + j * 5); S.stroke(); }

  // ── NAS (Frontansicht) ──
  var NX = 60, NY = 44, NW = 218, NH = 126;                                                // schmaler: die Einschübe füllen die Blende
  kasten(NX + 14, NY + NH, NW - 28, 10, '#232120', '#151413', true);                       // Sockel
  kasten(NX + 22, NY + NH + 8, 26, 4, '#151413', '#0d0c0b'); kasten(NX + NW - 48, NY + NH + 8, 26, 4, '#151413', '#0d0c0b');
  S.fillStyle = verlauf(NX, NY, NX, NY + NH, [[0, '#a49c90'], [.06, '#6f6961'], [.62, '#4f4a46'], [1, '#3a3634']]); S.fillRect(NX, NY, NW, NH);  // Gehäuse
  kasten(NX, NY, 3, NH, '#a49c90', '#6f6961', true); kasten(NX + NW - 3, NY, 3, NH, '#a49c90', '#4f4a46', true);                              // helle Kanten
  kasten(NX + 10, NY + 9, NW - 20, 82, '#151413', '#0d0c0b', true);                         // schwarze Blende
  var TB = 22, TA = 27, TX = NX + NW - 42 - (5 * TA + TB);   // Einschübe ein Viertel schmaler, rechts an die Anzeige gerückt wie am Gerät                                                      // Einschübe
  kasten(TX - 6, NY + 13, 6 * TA + 6, 74, '#0d0c0b', '#151413', true);
  for (var e = 0; e < 6; e++) {
    var x = TX + e * TA;
    kasten(x, NY + 16, TB, 68, '#6f6961', '#6f6961');                                      // Flächen in genauen Palettentönen, sonst kippt das Raster ins Bläuliche
    kasten(x, NY + 16, TB, 30, '#a49c90', '#a49c90'); kasten(x, NY + 46, TB, 8, '#a49c90', '#6f6961', true); kasten(x, NY + 66, TB, 18, '#6f6961', '#4f4a46', true);
    kasten(x, NY + 16, TB, 3, '#e9e3d8', '#a49c90');                                       // Glanzkante oben
    kasten(x, NY + 81, TB, 3, '#3a3634', '#232120');
    S.fillStyle = '#1a1918'; S.beginPath(); S.arc(x + TB / 2, NY + 70, 4, 0, 7); S.fill();  // Schloss
    S.fillStyle = '#6f6961'; S.fillRect(x + TB / 2 - 1, NY + 67, 2, 3);
  }
  var DX = NX + NW - 34;                                                                    // Anzeige
  kasten(DX, NY + 14, 22, 72, '#0d0c0b', '#151413', true);
  var wellen = [['#c7a854', 0], ['#cc9166', 7], ['#c07f73', 14], ['#9a5b50', 20], ['#5a7385', 26], ['#7d97ab', 31]];
  S.save(); S.beginPath(); S.rect(DX + 1, NY + 44, 20, 41); S.clip();
  wellen.forEach(function (wl) { S.strokeStyle = wl[0]; S.lineWidth = 6; S.beginPath(); S.moveTo(DX - 4, NY + 62 + wl[1]); S.bezierCurveTo(DX + 6, NY + 50 + wl[1], DX + 14, NY + 60 + wl[1], DX + 28, NY + 40 + wl[1]); S.stroke(); });
  S.restore();
  leuchte(DX + 11, NY + 62, 26, '#cc9166', .55); leuchte(DX + 11, NY + 78, 18, '#7d97ab', .45);
  // untere Leiste: Taster, Leuchtdioden, Kartenleser, zweimal USB-C, USB blau
  kasten(NX + 22, NY + 104, 10, 6, '#a49c90', '#6f6961'); kasten(NX + 24, NY + 106, 6, 2, '#3a3634', '#3a3634');
  for (var d = 0; d < 8; d++) { S.fillStyle = '#f5f1eb'; S.fillRect(NX + 42 + d * 9, NY + 106, 2, 2); leuchte(NX + 43 + d * 9, NY + 107, 6, d < 2 ? '#7d97ab' : '#93a373', .8); }
  kasten(NX + 124, NY + 106, 18, 2, '#151413', '#151413');
  kasten(NX + 152, NY + 105, 9, 4, '#1a1918', '#1a1918'); kasten(NX + 167, NY + 105, 9, 4, '#1a1918', '#1a1918');
  kasten(NX + 186, NY + 104, 10, 6, '#a9bfcf', '#5a7385'); leuchte(NX + 191, NY + 107, 9, '#7d97ab', .6);

  // ── Dock: offener Rahmen, Netzteil, Karte mit drei Lüftern ──
  // Die Karte nach dem Original (RX 7900 XTX, Frontansicht): Seitenverhältnis 2,9 : 1, schwarzes Gehäuse mit Silberkanten,
  // drei große Lüfter, die fast die ganze Höhe füllen und sich beinahe berühren, je ein Silberring, gebogene schwarze Blätter
  // vor hellen Kühlrippen, Nabe halb silbern; links das Slotblech, unten die goldenen PCIe-Kontakte.
  var DX0 = 416, DW = 212, DR = DX0 + DW;                                                   // Dock 20 Einheiten schmaler als zuvor
  kasten(DX0, 150, DW, 26, '#4f4a46', '#2b2827');                                           // Sockel mit Netzteil
  kasten(DX0, 66, 8, 86, '#6f6961', '#3a3634'); kasten(DR - 8, 66, 8, 86, '#4f4a46', '#2b2827'); kasten(DX0, 62, DW, 6, '#a49c90', '#4f4a46');
  kasten(DX0 + 14, 154, 62, 18, '#232120', '#151413'); S.fillStyle = '#3a3634'; for (var v = 0; v < 7; v++) S.fillRect(DX0 + 20 + v * 8, 158, 4, 10);
  leuchte(DX0 + DW / 2, 70, 150, '#cc9166', .38);                                           // warmes Licht von oben, schwächer: die Karte bleibt schwarz und silbern
  var CX = 432, CY = 76, CW = 180, CH = 62;                                                 // Kartenkörper
  kasten(CX - 6, 70, 5, 82, '#e9e3d8', '#6f6961', true); kasten(CX - 5, 132, 3, 8, '#151413', '#0d0c0b');   // Slotblech mit Anschlüssen
  [[.11, .15], [.165, .43]].forEach(function (g) { kasten(CX + g[0] * CW, CY + CH, (g[1] - g[0]) * CW, 4, '#e4cd85', '#8d7524', true); });  // PCIe-Kontakte
  kasten(CX, CY, CW, CH, '#1a1918', '#0d0c0b', true);                                       // Gehäuse
  kasten(CX, CY, CW, 2, '#a49c90', '#4f4a46'); kasten(CX, CY + CH - 2, CW, 2, '#4f4a46', '#2b2827');   // Silberkanten oben und unten
  kasten(CX + CW - 4, CY, 4, CH, '#e9e3d8', '#6f6961', true);                               // Silberkappe am Ende
  for (var f = 0; f < 3; f++) {
    var cx = CX + [.185, .50, .815][f] * CW, cy = CY + CH / 2, R = 27;
    S.save(); S.beginPath(); S.arc(cx, cy, R - 1, 0, 7); S.clip();
    S.fillStyle = '#2b2827'; S.fillRect(cx - R, cy - R, 2 * R, 2 * R);                     // Kühlrippen hinter den Blättern, gedämpft
    S.fillStyle = '#4f4a46'; for (var r = -R; r < R; r += 4) S.fillRect(cx + r, cy - R, 2, 2 * R);
    for (var b = 0; b < 13; b++) {                                                          // 13 gebogene Blätter
      var a = b * 2 * Math.PI / 13 + f * .4;
      S.fillStyle = '#0d0c0b'; S.beginPath();
      S.moveTo(cx + Math.cos(a) * 8, cy + Math.sin(a) * 8);
      S.quadraticCurveTo(cx + Math.cos(a + .55) * 17, cy + Math.sin(a + .55) * 17, cx + Math.cos(a + .95) * (R - 1), cy + Math.sin(a + .95) * (R - 1));
      S.lineTo(cx + Math.cos(a + 1.28) * (R - 1), cy + Math.sin(a + 1.28) * (R - 1));
      S.quadraticCurveTo(cx + Math.cos(a + .8) * 15, cy + Math.sin(a + .8) * 15, cx + Math.cos(a + .32) * 8, cy + Math.sin(a + .32) * 8);
      S.fill();
      S.strokeStyle = '#3a3634'; S.lineWidth = 1; S.beginPath();                            // Lichtkante am Blatt
      S.moveTo(cx + Math.cos(a) * 8, cy + Math.sin(a) * 8);
      S.quadraticCurveTo(cx + Math.cos(a + .55) * 17, cy + Math.sin(a + .55) * 17, cx + Math.cos(a + .95) * (R - 1), cy + Math.sin(a + .95) * (R - 1)); S.stroke();
    }
    S.restore();
    S.strokeStyle = verlauf(cx - R, cy - R, cx + R, cy + R, [[0, '#f5f1eb'], [.45, '#a49c90'], [1, '#4f4a46']]); S.lineWidth = 3;
    S.beginPath(); S.arc(cx, cy, R - 1, 0, 7); S.stroke();                                  // Silberring
    S.fillStyle = '#0d0c0b'; S.beginPath(); S.arc(cx, cy, 10, 0, 7); S.fill();              // Nabe: Rand dunkel, links silbern, rechts schwarz
    S.fillStyle = verlauf(cx - 8, cy, cx + 8, cy, [[0, '#e9e3d8'], [.44, '#a49c90'], [.5, '#151413'], [1, '#0d0c0b']]);
    S.beginPath(); S.arc(cx, cy, 8, 0, 7); S.fill();
    S.strokeStyle = '#a49c90'; S.lineWidth = 1.5; S.beginPath(); S.arc(cx, cy, 10, 0, 7); S.stroke();
    leuchte(cx - 10, cy - 14, 12, '#e9e3d8', .18);                                          // Glanz auf dem Ring
  }
  // Typenschild im Sockel: leicht erhabene Platte, Lichtkante oben, Schatten unten
  var PX = DR - 70, PY = 155, PW = 54, PH = 15;
  kasten(PX + 1, PY + 1, PW, PH, '#0d0c0b', '#0d0c0b');                                    // Schlagschatten
  kasten(PX, PY, PW, PH, '#a49c90', '#6f6961', true);                                       // Platte, gebürstetes Metall
  kasten(PX, PY, PW, 1, '#e9e3d8', '#a49c90'); kasten(PX, PY, 1, PH, '#a49c90', '#6f6961', true);   // Lichtkanten
  kasten(PX, PY + PH - 1, PW, 1, '#232120', '#151413'); kasten(PX + PW - 1, PY, 1, PH, '#4f4a46', '#232120', true);
  leuchte(PX + PW - 8, PY + PH / 2, 14, '#cc9166', .35);                                   // Schein des Cursors

  // ── OCuLink: Kabel mit laufenden Lichtpunkten ──
  var K = [[NX + NW, 156], [326, 206], [368, 206], [DX0, 164]];
  function kabel(ctx, breite, farbe) { ctx.strokeStyle = farbe; ctx.lineWidth = breite; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(K[0][0], K[0][1]); ctx.bezierCurveTo(K[1][0], K[1][1], K[2][0], K[2][1], K[3][0], K[3][1]); ctx.stroke(); }
  kabel(S, 5, '#3a3634'); kabel(S, 2, '#9a6b45');
  [[.16, 1], [.42, .8], [.66, 1], [.88, .7]].forEach(function (p) {
    var t = p[0], u = 1 - t, c = [u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t], px = 0, py = 0;
    for (var n = 0; n < 4; n++) { px += c[n] * K[n][0]; py += c[n] * K[n][1]; }
    S.fillStyle = '#f3d6bb'; S.fillRect(px - 2, py - 2, 5, 4); leuchte(px, py, 14, '#e3b48e', p[1]);
  });

  tg.zeichne(canvas, s);
  // Schrift scharf über das Ergebnis (Szenenkoordinaten / 2 = Zeichenspalte, * s = Gerätepixel)
  var C = canvas.getContext('2d'), k = s / 3, m = s / 2;
  C.textBaseline = 'alphabetic';
  C.font = '500 ' + Math.round(11 * k) + 'px "JetBrains Mono", Consolas, monospace';
  function marke(text, x, y, farbe) { C.fillStyle = farbe; C.fillText(text, Math.round(x * m), Math.round(y * m)); }
  marke('iDX6011 PRO · 64 GB LPDDR5X', NX, NY - 12, '#a49c90'); marke('RX 7900 XTX · 24 GB GDDR6', DX0, 50, '#a49c90');
  C.textAlign = 'center'; marke('OCULINK · PCIE 4.0 X4', (K[0][0] + K[3][0]) / 2, 144, '#cc9166');   // mittig über dem Kabel
  // FAF.NET eingeprägt ins Typenschild (Mono wie früher), dahinter ein Block-Cursor wie im Terminal
  C.font = '700 ' + Math.round(10 * k) + 'px "JetBrains Mono", Consolas, monospace'; C.textAlign = 'start';
  var o = Math.max(1, Math.round(s / 3)), tx = PX + 6, ty = PY + 11;
  C.fillStyle = '#e9e3d8'; C.globalAlpha = .45; C.fillText('FAF.NET', Math.round(tx * m) + o, Math.round(ty * m) + o); C.globalAlpha = 1;   // Lichtkante unter der Prägung
  marke('FAF.NET', tx, ty, '#1a1918');                                                                  // eingeprägte Schrift
  var cw = C.measureText('FAF.NET').width;
  C.fillStyle = '#cc9166'; C.fillRect(Math.round(tx * m + cw + 3 * k), Math.round((ty - 8) * m), Math.round(5 * k), Math.round(8 * m));   // Block-Cursor
  C.font = '700 ' + Math.round(12 * k) + 'px "JetBrains Mono", Consolas, monospace'; C.textAlign = 'center';
  for (var z = 0; z < 6; z++) marke('0' + (z + 1), TX + z * TA + TB / 2, NY + 40, '#0d0c0b');
  C.font = '700 ' + Math.round(8 * k) + 'px "JetBrains Mono", Consolas, monospace';
  marke('70', DX + 11, NY + 27, '#f5f1eb');
  C.font = '500 ' + Math.round(6 * k) + 'px "JetBrains Mono", Consolas, monospace';
  marke('T/s', DX + 11, NY + 37, '#a49c90');
  C.textAlign = 'start';
}
