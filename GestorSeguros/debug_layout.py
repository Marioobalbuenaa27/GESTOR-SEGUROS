"""
debug_layout.py
----------------
Uso: python debug_layout.py entrada.pdf salida_debug.pdf

Dibuja un rectángulo rojo alrededor de cada campo definido en
layout_pelayo.py, para poder ABRIR el PDF resultante y verificar a
ojo que cada caja efectivamente rodea al dato que tiene que
reemplazar (y a ningún otro). Si alguna caja está corrida, se ajusta
el número correspondiente en layout_pelayo.py y se vuelve a correr.
"""

import sys
import fitz
from layout_pelayo import CAMPOS


def generar_debug(ruta_entrada: str, ruta_salida: str) -> None:
    pdf = fitz.open(ruta_entrada)
    for pagina in pdf:
        for spec in CAMPOS:
            for rect in spec.rects:
                pagina.draw_rect(rect, color=(1, 0, 0), width=0.7)
                pagina.insert_text((rect.x0, rect.y0 - 1), spec.nombre,
                                    fontsize=5, color=(1, 0, 0))
    pdf.save(ruta_salida)
    pdf.close()


if __name__ == "__main__":
    entrada = sys.argv[1] if len(sys.argv) > 1 else "original.pdf"
    salida = sys.argv[2] if len(sys.argv) > 2 else "debug.pdf"
    generar_debug(entrada, salida)
    print(f"Listo: {salida}")
