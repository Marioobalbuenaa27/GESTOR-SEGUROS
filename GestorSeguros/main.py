import fitz
import re
import os
from datetime import date
from dateutil.relativedelta import relativedelta

entrada_porcentaje = input("Ingresá el porcentaje de aumento (0 o enter si no hay aumento): ")

if entrada_porcentaje.strip() == "":
    porcentaje_aumento = 0.0
else:
    porcentaje_aumento = float(entrada_porcentaje)

carpeta = input("Ingresá la ruta de la carpeta con los PDFs: ")

archivos_pdf = []

for archivo in os.listdir(carpeta):
    if archivo.endswith(".pdf"):
        archivos_pdf.append(archivo)

print("PDFs encontrados:", archivos_pdf)

for archivo in archivos_pdf:
    ruta_pdf = os.path.join(carpeta, archivo)

    pdf = fitz.open(ruta_pdf)

    print("\n=== Procesando:", archivo, "===")
    print("Cantidad de páginas:", len(pdf))

    for numero, pagina in enumerate(pdf):
        print("\n--- PÁGINA", numero + 1, "---")

        # --- RECIBO NRO. ---

        busqueda_etiqueta_recibo = pagina.search_for("RECIBO NRO.:")
        r = busqueda_etiqueta_recibo[0]

        zona_recibo = fitz.Rect(r.x1, r.y0, r.x1 + 60, r.y1)
        texto_zona_recibo = pagina.get_text("text", clip=zona_recibo)

        match_recibo = re.search(r"[\d.]+", texto_zona_recibo)
        numero_texto = match_recibo.group()

        print("Recibo encontrado en el PDF:", numero_texto)

        busqueda = pagina.search_for(numero_texto)

        numero = int(numero_texto.replace(".", ""))
        nuevo_numero = numero + 1
        nuevo_numero_texto = f"{nuevo_numero:,}".replace(",", ".")

        print("Recibo nuevo:", nuevo_numero_texto)

        for rect in busqueda:
            pagina.add_redact_annot(rect, fill=(1, 1, 1))
        pagina.apply_redactions()
        for rect in busqueda:
            pagina.insert_text((rect.x0, rect.y1 - 1), nuevo_numero_texto, fontsize=10.5, fontname="hebo")

        # --- FECHA EMISIÓN ---

        busqueda_etiqueta_fecha = pagina.search_for("FECHA EMISIÓN:")
        r = busqueda_etiqueta_fecha[0]

        zona_fecha = fitz.Rect(r.x1, r.y0, r.x1 + 60, r.y1)
        texto_zona_fecha = pagina.get_text("text", clip=zona_fecha)

        match_fecha_vieja = re.search(r"\d{2}/\d{2}/\d{2}", texto_zona_fecha)
        fecha_emision_texto = match_fecha_vieja.group()

        print("Fecha emisión encontrada en el PDF:", fecha_emision_texto)

        busqueda_fecha = pagina.search_for(fecha_emision_texto)

        hoy = date.today()
        fecha_nueva_texto = hoy.strftime("%d/%m/%y")

        print("Fecha emisión nueva:", fecha_nueva_texto)

        for rect in busqueda_fecha:
            pagina.add_redact_annot(rect, fill=(1, 1, 1))
        pagina.apply_redactions()
        for rect in busqueda_fecha:
            pagina.insert_text((rect.x0, rect.y1 - 1), fecha_nueva_texto, fontsize=10.5, fontname="hebo")

        # --- CUOTA ---

        busqueda_encabezado_cuota = pagina.search_for("Cuota")
        r = busqueda_encabezado_cuota[1]

        zona_cuota = fitz.Rect(r.x0 - 10, r.y1, r.x0 + 40, r.y1 + 20)
        texto_zona_cuota = pagina.get_text("text", clip=zona_cuota)

        match_cuota = re.search(r"\d+/\d+", texto_zona_cuota)
        cuota_texto = match_cuota.group()

        print("Cuota encontrada en el PDF:", cuota_texto)

        busqueda_cuota = pagina.search_for(cuota_texto)

        partes = cuota_texto.split("/")
        cuota_actual = int(partes[0])
        cantidad_cuotas = int(partes[1])

        nueva_cuota_actual = cuota_actual + 1
        if nueva_cuota_actual > cantidad_cuotas:
            nueva_cuota_actual = 1

        nueva_cuota_texto = f"{nueva_cuota_actual}/{cantidad_cuotas}"

        print("Cuota nueva:", nueva_cuota_texto)

        for rect in busqueda_cuota:
            pagina.add_redact_annot(rect, fill=(1, 1, 1))
        pagina.apply_redactions()
        for rect in busqueda_cuota:
            pagina.insert_text((rect.x0, rect.y1 - 1), nueva_cuota_texto, fontsize=10.5, fontname="hebo")

        # --- IMPORTE ---

        busqueda_encabezado_importe = pagina.search_for("Importe Orig.")
        r = busqueda_encabezado_importe[0]

        zona_importe = fitz.Rect(r.x0 - 10, r.y1, r.x0 + 60, r.y1 + 20)
        texto_zona_importe = pagina.get_text("text", clip=zona_importe)

        match_importe = re.search(r"[\d.,]+", texto_zona_importe)
        importe_texto = match_importe.group()

        print("Importe encontrado en el PDF:", importe_texto)

        busqueda_importe = pagina.search_for(importe_texto)

        importe = float(importe_texto.replace(",", "."))
        nuevo_importe = importe + (importe * porcentaje_aumento / 100)
        nuevo_importe_texto = f"{nuevo_importe:.2f}".replace(".", ",")

        print("Importe nuevo:", nuevo_importe_texto)

        for rect in busqueda_importe:
            pagina.add_redact_annot(rect, fill=(1, 1, 1))
        pagina.apply_redactions()
        for rect in busqueda_importe:
            pagina.insert_text((rect.x0, rect.y1 - 1), nuevo_importe_texto, fontsize=10.5, fontname="hebo")

        # --- OBSERVACIONES (VALIDO HASTA) ---

        busqueda_etiqueta_vto = pagina.search_for("Fecha Vto.")
        r = busqueda_etiqueta_vto[0]

        zona_vto = fitz.Rect(r.x0 - 10, r.y1, r.x0 + 60, r.y1 + 20)
        texto_zona_vto = pagina.get_text("text", clip=zona_vto)

        match_fecha_vto = re.search(r"\d{2}/\d{2}/\d{4}", texto_zona_vto)
        fecha_vto_texto = match_fecha_vto.group()

        print("Fecha Vto. encontrada en el PDF:", fecha_vto_texto)

        busqueda_etiqueta_obs = pagina.search_for("VALIDO HASTA")
        r_obs = busqueda_etiqueta_obs[0]

        zona_obs = fitz.Rect(r_obs.x1, r_obs.y0, r_obs.x1 + 100, r_obs.y1)
        texto_zona_obs = pagina.get_text("text", clip=zona_obs)

        match_obs_vieja = re.search(r"\d{1,2} \d{1,2} \d{4}", texto_zona_obs)
        fecha_obs_vieja_texto = match_obs_vieja.group()

        texto_observaciones_viejo = "VALIDO HASTA " + fecha_obs_vieja_texto

        busqueda_observaciones = pagina.search_for(texto_observaciones_viejo)

        partes_fecha = fecha_vto_texto.split("/")
        dia = int(partes_fecha[0])
        mes = int(partes_fecha[1])
        anio = int(partes_fecha[2])

        fecha_vto = date(anio, mes, dia)
        fecha_valido_hasta = fecha_vto + relativedelta(months=1)
        nuevas_observaciones_texto = "VALIDO HASTA " + fecha_valido_hasta.strftime("%d %m %Y")

        print("Observaciones nuevas:", nuevas_observaciones_texto)

        for rect in busqueda_observaciones:
            pagina.add_redact_annot(rect, fill=(1, 1, 1))
        pagina.apply_redactions()
        for rect in busqueda_observaciones:
            pagina.insert_text((rect.x0, rect.y1 - 1), nuevas_observaciones_texto, fontsize=10.5, fontname="hebo")

        # --- PRÓX. VENCIMIENTO ---

        busqueda_vencimiento = pagina.search_for("Prox. Vencimiento")

        nuevo_vencimiento_texto = fecha_valido_hasta.strftime("%d/%m/%Y")

        print("Próx. Vencimiento nuevo:", nuevo_vencimiento_texto)

        for rect in busqueda_vencimiento:
            pagina.insert_text((rect.x0, rect.y1 + 12), nuevo_vencimiento_texto, fontsize=10.5, fontname="hebo")

    ruta_salida = os.path.join(carpeta, "actualizado_" + archivo)
    pdf.save(ruta_salida)
    print("PDF guardado en:", ruta_salida)
    pdf.close()