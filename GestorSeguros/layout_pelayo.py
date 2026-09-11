"""
layout_pelayo.py
-----------------
Define, de una vez y para siempre, DONDE va cada dato dentro del recibo
"Pelayo / SSN". Estos rects se midieron con PyMuPDF directamente sobre
un recibo original (16-09-19_ovelar_jacinto_.pdf), tomando las
coordenadas reales de las etiquetas ("RECIBO NRO.:", "Cuota", etc.)
y dejando margen de seguridad hacia las columnas vecinas.

Cada recibo en PDF trae DOS comprobantes idénticos en la misma hoja
(uno arriba, uno abajo), por eso cada campo tiene una lista de 2 rects
(bloque_top, bloque_bottom) en vez de uno solo.

IMPORTANTE: estos números son un punto de partida ya calibrado sobre
un PDF real, no una plantilla teórica. Igual, antes de usar en
producción, correr debug_layout.py una vez y mirar el PDF resultante
con los rectángulos dibujados: si alguna caja se ve corrida un par de
puntos, se ajusta acá y listo (se ajusta UNA sola vez).
"""

from dataclasses import dataclass, field
import fitz


@dataclass(frozen=True)
class FieldSpec:
    nombre: str
    # un Rect fijo por cada comprobante (arriba, abajo)
    rects: tuple  # tuple[fitz.Rect, fitz.Rect]
    align: str = "left"          # "left" | "right" | "center"
    fuente: str = "hebo"         # Helvetica-Bold
    tam_base: float = 10.5
    tam_min: float = 6.0
    color_fondo: tuple = (1, 1, 1)  # blanco, para tapar el valor viejo


def _r(x0, y0, x1, y1):
    return fitz.Rect(x0, y0, x1, y1)


# Offset medido entre comprobante superior e inferior: x+3, y+425.551
# (no se usa directamente, los rects de abajo ya están tomados de la
# medición real de cada bloque para evitar arrastrar error de redondeo)

CAMPOS = [
    FieldSpec(
        nombre="recibo_nro",
        rects=(_r(353.5, 25.5, 430.0, 40.5), _r(356.5, 451.0, 433.0, 466.0)),
        align="left",
    ),
    FieldSpec(
        nombre="fecha_emision",
        rects=(_r(526.0, 25.5, 594.0, 40.5), _r(529.0, 451.0, 594.0, 466.0)),
        align="left",
    ),
    FieldSpec(
        nombre="cuota",
        rects=(_r(390.0, 136.5, 432.0, 148.5), _r(393.0, 562.0, 435.0, 574.0)),
        align="center",
        tam_min=5.5,  # para cuando se listan varias cuotas ("1,2,3,4/4")
    ),
    FieldSpec(
        nombre="fecha_vto",
        rects=(_r(436.0, 136.5, 497.0, 148.5), _r(439.0, 562.0, 500.0, 574.0)),
        align="left",
        tam_base=9.0,
    ),
    FieldSpec(
        nombre="importe",
        rects=(_r(500.0, 136.5, 570.0, 148.5), _r(503.0, 562.0, 573.0, 574.0)),
        align="right",
    ),
    # --- Campos que deben reflejar el MISMO importe que "importe" ---
    FieldSpec(
        nombre="total_cuotas",
        rects=(_r(539.0, 156.0, 569.0, 168.5), _r(542.0, 581.5, 572.0, 594.0)),
        align="right",
    ),
    FieldSpec(
        nombre="importe_orig",
        rects=(_r(401.0, 206.5, 444.0, 218.0), _r(403.0, 632.0, 446.0, 643.5)),
        align="right",
    ),
    FieldSpec(
        nombre="importe_conv",
        rects=(_r(511.0, 206.5, 555.0, 218.0), _r(513.0, 632.0, 556.0, 643.5)),
        align="right",
    ),
    FieldSpec(
        nombre="total",
        rects=(_r(521.0, 223.5, 561.0, 240.0), _r(523.5, 649.0, 563.5, 665.5)),
        align="right",
        tam_base=13.5,
        tam_min=7.0,
    ),
    FieldSpec(
        # OJO: "VALIDO HASTA" es parte del VALOR dinámico, no de la
        # etiqueta fija (la etiqueta fija es solo "Observaciones:").
        # El rect tiene que tapar la frase completa "VALIDO HASTA DD MM YYYY".
        nombre="observaciones_valido_hasta",
        rects=(_r(72.0, 249.5, 300.0, 261.5), _r(74.0, 675.5, 302.5, 687.5)),
        align="left",
    ),
    FieldSpec(
        nombre="prox_vencimiento",
        rects=(_r(388.0, 286.0, 460.0, 299.0), _r(388.5, 711.5, 461.0, 724.5)),
        align="left",
    ),
]

CAMPOS_POR_NOMBRE = {c.nombre: c for c in CAMPOS}