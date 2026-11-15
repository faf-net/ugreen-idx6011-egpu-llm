/* Textgrafik für den Seitenkopf: NAS, OCuLink-Kabel, Dock mit Karte. Mit Licht gemalt, dann gerastert (Baustein textgrafik.js). */
function Anlage(canvas, s) {
  var tg = Textgrafik.erzeuge({ spalten: 344, zeilen: 112, palette: Textgrafik.PALETTEN.workbench, grund: '0d0c0b', koernung: false });
  tg.neu();
  var S = tg.szene.getContext('2d'), Li = tg.licht.getContext('2d'), W = 688, H = 224;
  function verlauf(x0, y0, x1, y1, stufen) { var g = S.createLinearGradient(x0, y0, x1, y1); stufen.forEach(function (p) { g.addColorStop(p[0], p[1]); }); return g; }
  function kasten(x, y, w, h, a, b, senkrecht) { S.fillStyle = verlauf(x, y, senkrecht ? x : x + w, senkrecht ? y + h : y, [[0, a], [1, b]]); S.fillRect(x, y, w, h); }
  function leuchte(x, y, r, farbe, staerke) { var g = Li.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, farbe); g.addColorStop(1, 'rgba(0,0,0,0)'); Li.globalAlpha = staerke; Li.fillStyle = g; Li.fillRect(x - r, y - r, 2 * r, 2 * r); Li.globalAlpha = 1; }

  // Raum und Boden
  S.fillStyle = verlauf(0, 0, 0, H, [[0, '#0d0c0b'], [.55, '#151413'], [.77, '#1a1918'], [.78, '#2b2827'], [1, '#151413']]); S.fillRect(0, 0, W, H);
  S.strokeStyle = '#3a3634'; S.lineWidth = 1;
  for (var i = -8; i <= 20; i++) { S.beginPath(); S.moveTo(W / 2 + (i - 6) * 26, 175); S.lineTo(W / 2 + (i - 6) * 70, H); S.stroke(); }
  for (var j = 0; j < 4; j++) { S.beginPath(); S.moveTo(0, 182 + j * j * 5 + j * 6); S.lineTo(W, 182 + j * j * 5 + j * 6); S.stroke(); }

  // NAS: Gehäuse, sechs Einschübe, Anzeige
  kasten(58, 54, 196, 122, '#6f6961', '#3a3634');
  kasten(58, 54, 196, 6, '#a49c90', '#6f6961');
  kasten(254, 60, 10, 116, '#3a3634', '#1a1918');
  for (var e = 0; e < 6; e++) {
    var x = 70 + e * 28;
    kasten(x, 68, 23, 88, '#2b2827', '#151413', true);
    kasten(x + 2, 70, 19, 4, '#6f6961', '#4f4a46');
    S.fillStyle = '#3a3634'; for (var r = 0; r < 9; r++) S.fillRect(x + 4, 82 + r * 7, 15, 2);
    S.fillStyle = '#bccaa0'; S.fillRect(x + 9, 148, 5, 4); leuchte(x + 11, 150, 9, '#93a373', .9);
  }
  kasten(70, 160, 108, 10, '#151413', '#0d0c0b'); S.fillStyle = '#cc9166'; S.fillRect(74, 163, 46, 4); leuchte(98, 165, 22, '#cc9166', .7);
  S.fillStyle = '#7d97ab'; S.fillRect(236, 162, 6, 6); leuchte(239, 165, 10, '#7d97ab', .8);

  // Dock: offener Rahmen, Netzteil, Karte mit drei Lüftern
  kasten(408, 150, 232, 26, '#4f4a46', '#2b2827');
  kasten(408, 66, 8, 86, '#6f6961', '#3a3634'); kasten(632, 66, 8, 86, '#4f4a46', '#2b2827'); kasten(408, 62, 232, 6, '#a49c90', '#4f4a46');
  kasten(424, 154, 70, 18, '#232120', '#151413'); S.fillStyle = '#3a3634'; for (var v = 0; v < 8; v++) S.fillRect(430 + v * 8, 158, 4, 10);
  kasten(424, 84, 200, 54, '#3a3634', '#151413', true);
  kasten(424, 84, 200, 5, '#e3b48e', '#9a6b45'); leuchte(524, 86, 150, '#cc9166', .55);
  for (var f = 0; f < 3; f++) {
    var cx = 458 + f * 66, cy = 113;
    S.fillStyle = verlauf(cx - 24, cy - 24, cx + 24, cy + 24, [[0, '#4f4a46'], [1, '#1a1918']]); S.beginPath(); S.arc(cx, cy, 23, 0, 7); S.fill();
    S.strokeStyle = '#6f6961'; S.lineWidth = 2; S.beginPath(); S.arc(cx, cy, 23, 0, 7); S.stroke();
    S.strokeStyle = '#2b2827'; S.lineWidth = 3; for (var b = 0; b < 9; b++) { var w = b * .7 + f; S.beginPath(); S.moveTo(cx + Math.cos(w) * 6, cy + Math.sin(w) * 6); S.lineTo(cx + Math.cos(w + .5) * 20, cy + Math.sin(w + .5) * 20); S.stroke(); }
    S.fillStyle = '#9a6b45'; S.beginPath(); S.arc(cx, cy, 5, 0, 7); S.fill(); leuchte(cx, cy, 16, '#cc9166', .5);
  }
  kasten(424, 138, 200, 4, '#6b4a30', '#3e2a1c');

  // OCuLink: Kabel mit laufenden Lichtpunkten
  function kabel(ctx, breite, farbe) { ctx.strokeStyle = farbe; ctx.lineWidth = breite; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(264, 140); ctx.bezierCurveTo(310, 196, 360, 196, 408, 162); ctx.stroke(); }
  kabel(S, 5, '#3a3634'); kabel(S, 2, '#9a6b45');
  [[.18, 1], [.42, .8], [.66, 1], [.86, .7]].forEach(function (p) {
    var t = p[0], u = 1 - t, px = u * u * u * 264 + 3 * u * u * t * 310 + 3 * u * t * t * 360 + t * t * t * 408, py = u * u * u * 140 + 3 * u * u * t * 196 + 3 * u * t * t * 196 + t * t * t * 162;
    S.fillStyle = '#f3d6bb'; S.fillRect(px - 2, py - 2, 5, 4); leuchte(px, py, 14, '#e3b48e', p[1]);
  });

  tg.zeichne(canvas, s);
  // Schrift scharf über das Ergebnis
  var C = canvas.getContext('2d'), k = s / 3;
  C.font = '500 ' + Math.round(11 * k) + 'px "JetBrains Mono", Consolas, monospace'; C.textBaseline = 'alphabetic';
  function marke(text, x, y, farbe) { C.fillStyle = farbe; C.fillText(text, Math.round(x * s), Math.round(y * s)); }
  marke('iDX6011 PRO · 64 GB', 29, 21, '#a49c90'); marke('OCULINK · PCIE 4.0 X4', 133, 106, '#cc9166'); marke('RX 7900 XTX · 24 GB', 204, 26, '#a49c90');
}
