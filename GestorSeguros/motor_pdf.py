"""
motor_pdf.py — Motor robusto por búsqueda de etiquetas (Pelayo / SSN)

Correcciones de diseño:
1. Importe: un solo "$ 25.000,00" (sin $ duplicado), alineado a la columna.
2. Textos dentro de su celda, sin tapar líneas divisorias.
3. Totales: etiqueta + número en la misma línea de base, prolijo.
"""

import os
import re
import calendar
from datetime import date
from typing import List, Optional, Tuple

import fitz
from dateutil.relativedelta import relativedelta

FUENTE = "hebo"
TAM_BASE = 9.5
TAM_MIN = 6.0
PADDING_X = 1.2
COLOR_NEGRO = (0, 0, 0)
COLOR_BLANCO = (1, 1, 1)
# Inset al redactar: no pinta las líneas negras del contenedor
INSET = 1.15


def _medir(texto: str, tam: float) -> float:
    return fitz.get_text_length(texto, fontname=FUENTE, fontsize=tam)


def _elegir_tam(texto: str, ancho: float, tam_base: float = TAM_BASE, tam_min: float = TAM_MIN) -> float:
    tam = tam_base
    while tam > tam_min:
        if _medir(texto, tam) <= ancho:
            return tam
        tam -= 0.5
    return tam_min


def _pos_x(rect: fitz.Rect, ancho_texto: float, align: str) -> float:
    if align == "right":
        return rect.x1 - PADDING_X - ancho_texto
    if align == "center":
        return rect.x0 + (rect.width - ancho_texto) / 2
    return rect.x0 + PADDING_X


def _base_y(rect: fitz.Rect, tam: float) -> float:
    # Baseline centrada verticalmente en la celda
    return rect.y0 + (rect.height + tam) / 2 - 1.2


def _inset(rect: fitz.Rect, m: float = INSET) -> fitz.Rect:
    return fitz.Rect(rect.x0 + m, rect.y0 + m * 0.55, rect.x1 - m, rect.y1 - m * 0.55)


def _escribir(pagina: fitz.Page, rect: fitz.Rect, texto: str,
              align: str = "left", tam_base: float = TAM_BASE, tam_min: float = TAM_MIN) -> None:
    r = _inset(rect)
    ancho = max(r.width - 2 * PADDING_X, 4)
    tam = _elegir_tam(texto, ancho, tam_base, tam_min)
    if _medir(texto, tam) > ancho:
        while texto and _medir(texto + "…", tam) > ancho:
            texto = texto[:-1]
        texto = (texto + "…") if texto else texto
    aw = _medir(texto, tam)
    pagina.insert_text((_pos_x(r, aw, align), _base_y(r, tam)), texto,
                       fontsize=tam, fontname=FUENTE, color=COLOR_NEGRO, render_mode=0)


def _redactar(pagina: fitz.Page, rects: List[fitz.Rect]) -> None:
    for r in rects:
        pagina.add_redact_annot(_inset(r), fill=COLOR_BLANCO)
    pagina.apply_redactions()


def _buscar(pagina: fitz.Page, t: str) -> List[fitz.Rect]:
    return sorted(pagina.search_for(t), key=lambda r: (r.y0, r.x0))


def _leer(pagina: fitz.Page, rect: fitz.Rect) -> str:
    return pagina.get_text("text", clip=rect).strip()


def _fmt(v: float) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parse(texto: str) -> Optional[float]:
    m = re.search(r"[\d.,]+", texto.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group().replace(".", "").replace(",", "."))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Zonas
# ---------------------------------------------------------------------------

def _z_recibo(pagina: fitz.Page) -> List[fitz.Rect]:
    return [fitz.Rect(e.x1 + 2, e.y0, e.x1 + 68, e.y1) for e in _buscar(pagina, "RECIBO NRO.:")]


def _z_fecha_em(pagina: fitz.Page) -> List[fitz.Rect]:
    return [fitz.Rect(e.x1 + 2, e.y0, e.x1 + 72, e.y1) for e in _buscar(pagina, "FECHA EMISIÓN:")]


def _z_tabla(pagina: fitz.Page) -> List[dict]:
    """
    Fila de valores bajo Cuota / Fecha Vto. / Importe.
    El $ original del PDF está ~x=500-505; el número ~535-569.
    La zona de importe DEBE cubrir ambos para no dejar un $ suelto.
    """
    headers_imp = [h for h in _buscar(pagina, "Importe")
                   if 145 < h.y0 < 165 or 565 < h.y0 < 585]
    headers_fv = _buscar(pagina, "Fecha Vto.")
    if not headers_imp:
        headers_imp = headers_fv

    filas = []
    for h_imp in headers_imp:
        # Celda de valor: deja margen respecto a la línea superior del header
        y0 = h_imp.y1 + 3.2
        y1 = y0 + 9.2

        # Importe: desde ~x=498 (cubre el $) hasta el borde derecho de la columna
        x0_imp = min(h_imp.x0 - 38, 498)
        x1_imp = min(h_imp.x1 + 14, 572)
        zona_imp = fitz.Rect(x0_imp, y0, x1_imp, y1)

        h_fv = next((c for c in headers_fv if abs(c.y0 - h_imp.y0) < 30), None)
        if h_fv:
            # Fecha centrada bajo su encabezado
            zona_fecha = fitz.Rect(h_fv.x0 + 0.5, y0, h_fv.x1 + 10, y1)
            # Cuota: se extiende hasta el inicio de Fecha Vto. para no dejar restos (ej: "0")
            zona_cuota = fitz.Rect(h_fv.x0 - 52, y0, h_fv.x0 - 1, y1)
        else:
            zona_fecha = fitz.Rect(h_imp.x0 - 95, y0, h_imp.x0 - 30, y1)
            zona_cuota = fitz.Rect(h_imp.x0 - 135, y0, h_imp.x0 - 100, y1)

        filas.append({
            "y_ref": h_imp.y0,
            "cuota": zona_cuota,
            "fecha_vto": zona_fecha,
            "importe": zona_imp,
        })
    return filas


def _z_y(pagina: fitz.Page, label: str, builder) -> List[Tuple[float, fitz.Rect]]:
    return [(e.y0, builder(e)) for e in _buscar(pagina, label)]


def _z_totales(pagina: fitz.Page) -> List[Tuple[float, fitz.Rect]]:
    """
    Número de Totales pegado a la etiqueta, misma línea de base,
    sin salirse del margen inferior del cuadro.
    """
    out = []
    for e in _buscar(pagina, "Totales:"):
        # Misma altura que la etiqueta; ancho justo para el número
        zona = fitz.Rect(e.x1 + 2, e.y0, e.x1 + 56, e.y1)
        out.append((e.y0, zona))
    return out


def _z_imp_orig(pagina: fitz.Page) -> List[Tuple[float, fitz.Rect]]:
    return _z_y(pagina, "Importe Orig",
                lambda e: fitz.Rect(e.x0 + 8, e.y1 + 2.5, e.x0 + 56, e.y1 + 12.5))


def _z_imp_conv(pagina: fitz.Page) -> List[Tuple[float, fitz.Rect]]:
    et = _buscar(pagina, "Importe Conv") or _buscar(pagina, "Importe Conv.")
    return [(e.y0, fitz.Rect(e.x0, e.y1 + 2.5, e.x0 + 52, e.y1 + 12.5)) for e in et]


def _z_total(pagina: fitz.Page) -> List[Tuple[float, fitz.Rect]]:
    """Reescribe toda la línea: TOTAL: $ XX.XXX,00"""
    return [(e.y0, fitz.Rect(e.x0, e.y0, e.x1 + 95, e.y1)) for e in _buscar(pagina, "TOTAL:")]


def _z_valido(pagina: fitz.Page) -> List[fitz.Rect]:
    return [fitz.Rect(e.x0, e.y0, e.x0 + 155, e.y1) for e in _buscar(pagina, "VALIDO HASTA")]


def _z_prox(pagina: fitz.Page) -> List[fitz.Rect]:
    return [fitz.Rect(e.x0 + 2, e.y1 + 2, e.x0 + 72, e.y1 + 14.5)
            for e in _buscar(pagina, "Prox. Vencimiento")]


def _asignar(pendientes, zonas, importes, align="right", tam=TAM_BASE, prefix=""):
    for y_zona, rect in zonas:
        mejor, dist = None, 9999
        for y_ref, txt in importes:
            d = abs(y_ref - y_zona)
            if d < dist:
                dist, mejor = d, txt
        if mejor is not None and dist < 250:
            pendientes.append((rect, f"{prefix}{mejor}" if prefix else mejor, align, tam))


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def procesar_recibo(ruta_pdf: str, carpeta_salida: str, porcentaje_aumento: float,
                    cuotas_custom=None, importe_custom=None, pagar_todas=False) -> str:
    pdf = fitz.open(ruta_pdf)
    nuevo_nombre = None
    hoy = date.today()
    fecha_base_vto = hoy  # Fallback por defecto

    for pagina in pdf:
        pendientes: List[Tuple[fitz.Rect, str, str, float]] = []
        importes: List[Tuple[float, str]] = []

        # 1. Recibo nro
        for zona in _z_recibo(pagina):
            valor = _leer(pagina, zona)
            m = re.search(r"[\d.]+", valor)
            if not m:
                continue
            orig = m.group()
            num = int(orig.replace(".", ""))
            n = len(orig.replace(".", ""))
            cuerpo = f"{num + 1:0{n}d}"
            if len(cuerpo) > 3:
                partes = []
                while cuerpo:
                    partes.append(cuerpo[-3:])
                    cuerpo = cuerpo[:-3]
                nuevo = ".".join(reversed(partes))
            else:
                nuevo = cuerpo
            pendientes.append((zona, nuevo, "left", TAM_BASE))

        # 2. Fecha emisión
        for zona in _z_fecha_em(pagina):
            pendientes.append((zona, hoy.strftime("%d/%m/%Y"), "left", TAM_BASE))

        # 3. Tabla
        for fila in _z_tabla(pagina):
            y_ref = fila["y_ref"]

            valor_cuota = _leer(pagina, fila["cuota"])
            m_cuota = re.search(r"\d+\s*/\s*\d+", valor_cuota)
            if m_cuota:
                partes = re.split(r"\s*/\s*", m_cuota.group())
                actual, cant = int(partes[0]), int(partes[1])
                if cuotas_custom is not None:
                    cant = cuotas_custom
                    nueva = f"1/{cant}"
                elif pagar_todas:
                    nueva = ",".join(str(i) for i in range(1, cant + 1)) + f"/{cant}"
                else:
                    n = actual + 1
                    if n > cant:
                        n = 1
                    nueva = f"{n}/{cant}"
                pendientes.append((fila["cuota"], nueva, "center", 9.0))

            # --- MODIFICACIÓN DE FECHA DE VENCIMIENTO ---
            # Ampliamos la zona SOLO para lectura para no cortar los números si están desfasados
            zona_lectura_fecha = fitz.Rect(
                fila["fecha_vto"].x0 - 15, 
                fila["fecha_vto"].y0 - 5, 
                fila["fecha_vto"].x1 + 25, 
                fila["fecha_vto"].y1 + 5
            )
            valor_fecha_vto = _leer(pagina, zona_lectura_fecha)
            m_fecha = re.search(r"(\d{1,2})[-/]\d{1,2}[-/]\d{2,4}", valor_fecha_vto)
            
            if m_fecha:
                dia_vto = int(m_fecha.group(1)) # Mantiene exactamente el mismo día original
                try:
                    fecha_base_vto = date(hoy.year, hoy.month, dia_vto)
                except ValueError:
                    # En caso de que el mes actual no contenga el día (ej. 31 en meses de 30 días)
                    _, ultimo_dia = calendar.monthrange(hoy.year, hoy.month)
                    fecha_base_vto = date(hoy.year, hoy.month, ultimo_dia)
            else:
                fecha_base_vto = hoy
                
            # Escribimos en la zona normal ajustada visualmente
            pendientes.append((fila["fecha_vto"], fecha_base_vto.strftime("%d/%m/%Y"), "center", 8.5))
            # --------------------------------------------

            # Importe: un solo "$ 25.000,00" (la zona ya cubre el $ original)
            valor_imp = _leer(pagina, fila["importe"])
            if importe_custom is not None and str(importe_custom).strip() != "":
                base = float(str(importe_custom).replace(".", "").replace(",", "."))
                nuevo_imp = base + (base * porcentaje_aumento / 100.0)
            else:
                parseado = _parse(valor_imp)
                if parseado is None:
                    continue
                nuevo_imp = parseado

            txt = _fmt(nuevo_imp)
            # Un solo símbolo $ y un espacio limpio
            pendientes.append((fila["importe"], f"$ {txt}", "right", 9.0))
            importes.append((y_ref, txt))

        if importes:
            _asignar(pendientes, _z_totales(pagina), importes, "right", 9.0)
            _asignar(pendientes, _z_imp_orig(pagina), importes, "right", 9.0)
            _asignar(pendientes, _z_imp_conv(pagina), importes, "right", 9.0)
            _asignar(pendientes, _z_total(pagina), importes, "left", 11.0, prefix="TOTAL: $ ")

        # --- MODIFICACIÓN DE VÁLIDO HASTA Y PRÓX VENCIMIENTO ---
        fecha_val = fecha_base_vto + relativedelta(months=1)
        
        for zona in _z_valido(pagina):
            pendientes.append((zona, "VALIDO HASTA " + fecha_val.strftime("%d-%m-%Y"), "left", TAM_BASE))
        for zona in _z_prox(pagina):
            pendientes.append((zona, fecha_val.strftime("%d/%m/%Y"), "left", TAM_BASE))
        # -------------------------------------------------------

        if nuevo_nombre is None:
            nf = fecha_val.strftime("%d-%m-%y")
            base = os.path.basename(ruta_pdf)
            m = re.match(r"^(\d{2}[-/]\d{2}[-/]\d{2,4})(.*)", base)
            nuevo_nombre = f"{nf}{m.group(2)}" if m else f"{nf}_{base}"

        if pendientes:
            _redactar(pagina, [r for r, _, _, _ in pendientes])
            for rect, texto, align, tam in pendientes:
                _escribir(pagina, rect, texto, align=align, tam_base=tam)

    if not nuevo_nombre:
        nuevo_nombre = os.path.basename(ruta_pdf)

    ruta_salida = os.path.join(carpeta_salida, nuevo_nombre)
    tmp = ruta_salida + ".tmp"
    pdf.save(tmp)
    pdf.close()

    if os.path.exists(ruta_pdf) and os.path.abspath(ruta_pdf) != os.path.abspath(ruta_salida):
        try:
            os.remove(ruta_pdf)
        except OSError:
            pass
    if os.path.exists(ruta_salida):
        try:
            os.remove(ruta_salida)
        except OSError:
            pass
    os.rename(tmp, ruta_salida)
    return ruta_salida