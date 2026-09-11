import os
import re
import fitz
from datetime import date
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Motor nuevo: redacta y escribe sobre rects fijos (ver layout_pelayo.py),
# en vez de re-buscar texto con search_for() cada vez.
# Se lo importa con el mismo nombre viejo (procesar_seguro) para no tener
# que tocar nada más abajo en el archivo.
from motor_pdf import procesar_recibo as procesar_seguro

# --- FUNCIONES DE PROCESAMIENTO ---
# (la vieja función procesar_seguro() de acá abajo ya no se usa,
# queda comentada un tiempo por las dudas y después se puede borrar)

def _procesar_seguro_VIEJO_no_usar(ruta_pdf, carpeta_salida, porcentaje_aumento, cuotas_custom=None, importe_custom=None, pagar_todas=False):
    pdf = fitz.open(ruta_pdf)
    
    nuevo_nombre_archivo = None
    
    for numero, pagina in enumerate(pdf):
        # --- RECIBO NRO. ---
        busqueda_etiqueta_recibo = pagina.search_for("RECIBO NRO.:")
        if busqueda_etiqueta_recibo:
            r = busqueda_etiqueta_recibo[0]
            zona_recibo = fitz.Rect(r.x1, r.y0, r.x1 + 60, r.y1)
            texto_zona_recibo = pagina.get_text("text", clip=zona_recibo)
            match_recibo = re.search(r"[\d.]+", texto_zona_recibo)
            if match_recibo:
                numero_texto = match_recibo.group()
                busqueda = pagina.search_for(numero_texto)
                num = int(numero_texto.replace(".", ""))
                nuevo_numero = num + 1
                nuevo_numero_texto = f"{nuevo_numero:,}".replace(",", ".")
                for rect in busqueda:
                    # Se quita el fill=(1,1,1) para borrar de forma transparente
                    pagina.add_redact_annot(rect)
                pagina.apply_redactions()
                for rect in busqueda:
                    pagina.insert_text((rect.x0, rect.y1 - 1), nuevo_numero_texto, fontsize=10.5, fontname="hebo")

        # --- FECHA EMISIÓN ---
        busqueda_etiqueta_fecha = pagina.search_for("FECHA EMISIÓN:")
        if busqueda_etiqueta_fecha:
            r = busqueda_etiqueta_fecha[0]
            zona_fecha = fitz.Rect(r.x1, r.y0, r.x1 + 60, r.y1)
            texto_zona_fecha = pagina.get_text("text", clip=zona_fecha)
            match_fecha_vieja = re.search(r"\d{2}/\d{2}/\d{2}", texto_zona_fecha)
            if match_fecha_vieja:
                fecha_emision_texto = match_fecha_vieja.group()
                busqueda_fecha = pagina.search_for(fecha_emision_texto)
                hoy = date.today()
                fecha_nueva_texto = hoy.strftime("%d/%m/%y")
                for rect in busqueda_fecha:
                    pagina.add_redact_annot(rect)
                pagina.apply_redactions()
                for rect in busqueda_fecha:
                    pagina.insert_text((rect.x0, rect.y1 - 1), fecha_nueva_texto, fontsize=10.5, fontname="hebo")

        # --- CUOTA ---
        busqueda_encabezado_cuota = pagina.search_for("Cuota")
        if len(busqueda_encabezado_cuota) > 1:
            r = busqueda_encabezado_cuota[1]
            zona_cuota = fitz.Rect(r.x0 - 10, r.y1, r.x0 + 40, r.y1 + 20)
            texto_zona_cuota = pagina.get_text("text", clip=zona_cuota)
            match_cuota = re.search(r"\d+/\d+", texto_zona_cuota)
            if match_cuota:
                cuota_texto = match_cuota.group()
                busqueda_cuota = pagina.search_for(cuota_texto)
                partes = cuota_texto.split("/")
                cuota_actual = int(partes[0])
                cantidad_cuotas = int(partes[1])
                
                tamanio_fuente = 10.5
                desplazamiento_x = 0
                
                if cuotas_custom is not None:
                    cantidad_cuotas = cuotas_custom
                    nueva_cuota_actual = 1
                else:
                    if pagar_todas:
                        secuencia = ",".join(str(i) for i in range(1, cantidad_cuotas + 1))
                        nueva_cuota_actual = f"{secuencia}/{cantidad_cuotas}"
                        tamanio_fuente = 8.0
                        desplazamiento_x = 12
                    else:
                        nueva_cuota_actual = cuota_actual + 1
                        if nueva_cuota_actual > cantidad_cuotas:
                            nueva_cuota_actual = 1

                if not pagar_todas and cuotas_custom is None:
                    nueva_cuota_texto = f"{nueva_cuota_actual}/{cantidad_cuotas}"
                elif cuotas_custom is not None:
                    nueva_cuota_texto = f"{nueva_cuota_actual}/{cantidad_cuotas}"
                else:
                    nueva_cuota_texto = nueva_cuota_actual
                
                for rect in busqueda_cuota:
                    pagina.add_redact_annot(rect)
                pagina.apply_redactions()
                
                for rect in busqueda_cuota:
                    pos_x_final = rect.x0 - desplazamiento_x
                    pagina.insert_text((pos_x_final, rect.y1 - 1), str(nueva_cuota_texto), fontsize=tamanio_fuente, fontname="hebo")

        # --- IMPORTE ---
        busqueda_encabezado_importe = pagina.search_for("Importe Orig.")
        if busqueda_encabezado_importe:
            r = busqueda_encabezado_importe[0]
            zona_importe = fitz.Rect(r.x0 - 10, r.y1, r.x0 + 60, r.y1 + 20)
            texto_zona_importe = pagina.get_text("text", clip=zona_importe)
            match_importe = re.search(r"[\d.,]+", texto_zona_importe)
            if match_importe:
                importe_texto = match_importe.group()
                busqueda_importe = pagina.search_for(importe_texto)
                
                if importe_custom is not None and importe_custom != "":
                    importe_base = float(importe_custom.replace(".", "").replace(",", "."))
                    nuevo_importe = importe_base + (importe_base * porcentaje_aumento / 100)
                else:
                    importe_limpio = importe_texto.replace(".", "").replace(",", ".")
                    nuevo_importe = float(importe_limpio)
                
                nuevo_importe_texto = f"{nuevo_importe:.2f}".replace(".", ",")
                
                for rect in busqueda_importe:
                    pagina.add_redact_annot(rect)
                pagina.apply_redactions()

                palabras_pagina = pagina.get_text("words")

                for rect in busqueda_importe:
                    candidatos = [p for p in palabras_pagina if abs(p[1] - rect.y0) < 2 and p[2] <= rect.x0 + 1]
                    limite_izquierdo = max([p[2] for p in candidatos], default=rect.x0 - 100)

                    espacio_disponible = rect.x1 - limite_izquierdo - 2

                    tamanio_importe = 10.5
                    ancho_texto = fitz.get_text_length(nuevo_importe_texto, fontname="hebo", fontsize=tamanio_importe)

                    if ancho_texto > espacio_disponible:
                        tamanio_importe = max(tamanio_importe * (espacio_disponible / ancho_texto), 6.0)
                        ancho_texto = fitz.get_text_length(nuevo_importe_texto, fontname="hebo", fontsize=tamanio_importe)

                    x_posicion = rect.x1 - ancho_texto
                    pagina.insert_text((x_posicion, rect.y1 - 1), nuevo_importe_texto, fontsize=tamanio_importe, fontname="hebo")

        # --- FECHA VTO. (ahora se actualiza, debe ser igual a Fecha Emisión) ---
        busqueda_etiqueta_vto = pagina.search_for("Fecha Vto.")
        if busqueda_etiqueta_vto:
            r = busqueda_etiqueta_vto[0]
            zona_vto = fitz.Rect(r.x0 - 10, r.y1, r.x0 + 60, r.y1 + 20)
            texto_zona_vto = pagina.get_text("text", clip=zona_vto)
            match_fecha_vto_vieja = re.search(r"\d{2}/\d{2}/\d{4}", texto_zona_vto)
            if match_fecha_vto_vieja:
                fecha_vto_vieja_texto = match_fecha_vto_vieja.group()
                busqueda_fecha_vto = pagina.search_for(fecha_vto_vieja_texto)

                fecha_vto = hoy
                fecha_vto_nueva_texto = fecha_vto.strftime("%d/%m/%Y")

                for rect in busqueda_fecha_vto:
                    pagina.add_redact_annot(rect)
                pagina.apply_redactions()
                for rect in busqueda_fecha_vto:
                    pagina.insert_text((rect.x0, rect.y1 - 1), fecha_vto_nueva_texto, fontsize=9.0, fontname="hebo")

        # --- OBSERVACIONES (VALIDO HASTA) ---
        busqueda_etiqueta_obs = pagina.search_for("VALIDO HASTA")
        if busqueda_etiqueta_obs:
            r_obs = busqueda_etiqueta_obs[0]
            zona_obs = fitz.Rect(r_obs.x1, r_obs.y0, r_obs.x1 + 100, r_obs.y1)
            texto_zona_obs = pagina.get_text("text", clip=zona_obs)
            match_obs_vieja = re.search(r"\d{1,2} \d{1,2} \d{4}", texto_zona_obs)

            if match_obs_vieja:
                fecha_obs_vieja_texto = match_obs_vieja.group()
                texto_observaciones_viejo = "VALIDO HASTA " + fecha_obs_vieja_texto

                busqueda_observaciones = pagina.search_for(texto_observaciones_viejo)

                fecha_valido_hasta = fecha_vto + relativedelta(months=1)
                nuevas_observaciones_texto = "VALIDO HASTA " + fecha_valido_hasta.strftime("%d %m %Y")

                for rect in busqueda_observaciones:
                    pagina.add_redact_annot(rect)
                pagina.apply_redactions()
                for rect in busqueda_observaciones:
                    pagina.insert_text((rect.x0, rect.y1 - 1), nuevas_observaciones_texto, fontsize=10.5, fontname="hebo")

                # --- PRÓX. VENCIMIENTO ---
                busqueda_vencimiento = pagina.search_for("Prox. Vencimiento")
                nuevo_vencimiento_texto = fecha_valido_hasta.strftime("%d/%m/%Y")
                for rect in busqueda_vencimiento:
                    pagina.insert_text((rect.x0, rect.y1 + 12), nuevo_vencimiento_texto, fontsize=10.5, fontname="hebo")

                # --- RENOMBRAR SEGÚN FECHA "Válido Hasta" ---
                nuevo_nombre_fecha = fecha_valido_hasta.strftime("%d-%m-%y")
                base_actual = os.path.basename(ruta_pdf)

                match_nombre_fecha = re.match(r"^(\d{2}[-/]\d{2}[-/]\d{2,4})(.*)", base_actual)
                if match_nombre_fecha:
                    resto_nombre = match_nombre_fecha.group(2)
                    nuevo_nombre_archivo = f"{nuevo_nombre_fecha}{resto_nombre}"
                else:
                    nuevo_nombre_archivo = f"{nuevo_nombre_fecha}_{base_actual}"

    if not nuevo_nombre_archivo:
        nuevo_nombre_archivo = os.path.basename(ruta_pdf)

    ruta_salida = os.path.join(carpeta_salida, nuevo_nombre_archivo)
    
    # --- AQUÍ EMPIEZA LA CORRECCIÓN DEL GUARDADO TEMPORAL ---
    ruta_temporal = ruta_salida + ".tmp"
    pdf.save(ruta_temporal)
    pdf.close()

    if os.path.exists(ruta_pdf) and os.path.abspath(ruta_pdf) != os.path.abspath(ruta_salida):
        os.remove(ruta_pdf)
        
    if os.path.exists(ruta_salida):
        os.remove(ruta_salida)
        
    os.rename(ruta_temporal, ruta_salida)
    # --- AQUÍ TERMINA LA CORRECCIÓN ---


# --- INTERFAZ GRÁFICA (UI con Tkinter) ---

class AppGestorSeguros:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor y Actualizador de Seguros")
        self.root.geometry("650x480")
        
        self.carpeta_path = ""
        self.archivos_pendientes = []
        self.archivos_actualizados = []

        frame_top = tk.LabelFrame(root, text=" Configuración ", padx=10, pady=10)
        frame_top.pack(fill="x", padx=15, pady=10)

        btn_carpeta = tk.Button(frame_top, text="Seleccionar Carpeta de Seguros", command=self.seleccionar_carpeta)
        btn_carpeta.grid(row=0, column=0, padx=5, pady=5)

        self.lbl_ruta = tk.Label(frame_top, text="Ninguna carpeta seleccionada", fg="gray")
        self.lbl_ruta.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(frame_top, text="% Aumento Global (Opcional):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.txt_aumento = tk.Entry(frame_top, width=10)
        self.txt_aumento.insert(0, "15")
        self.txt_aumento.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        frame_center = tk.Frame(root)
        frame_center.pack(fill="both", expand=True, padx=15, pady=5)

        frame_pend = tk.LabelFrame(frame_center, text=" Pendientes de Actualización ", padx=5, pady=5)
        frame_pend.pack(side="left", fill="both", expand=True, padx=5)

        self.listbox_pend = tk.Listbox(frame_pend)
        self.listbox_pend.pack(fill="both", expand=True, pady=5)
        
        btn_actualizar = tk.Button(frame_pend, text="Actualizar Seleccionado...", bg="#d4edda", command=self.abrir_ventana_edicion)
        btn_actualizar.pack(fill="x")

        frame_act = tk.LabelFrame(frame_center, text=" Actualizados en el Mes ", padx=5, pady=5)
        frame_act.pack(side="right", fill="both", expand=True, padx=5)

        self.listbox_act = tk.Listbox(frame_act)
        self.listbox_act.pack(fill="both", expand=True, pady=5)

    def seleccionar_carpeta(self):
        self.carpeta_path = filedialog.askdirectory()
        if self.carpeta_path:
            self.lbl_ruta.config(text=self.carpeta_path, fg="black")
            self.cargar_archivos()

    def cargar_archivos(self):
        self.archivos_pendientes.clear()
        self.archivos_actualizados.clear()
        self.listbox_pend.delete(0, tk.END)
        self.listbox_act.delete(0, tk.END)

        mes_actual = date.today().month
        anio_actual = date.today().year

        for archivo in os.listdir(self.carpeta_path):
            if archivo.endswith(".pdf"):
                ruta_completa = os.path.join(self.carpeta_path, archivo)
                
                es_pendiente = True
                try:
                    pdf = fitz.open(ruta_completa)
                    texto_pagina = pdf[0].get_text("text")
                    pdf.close()
                    
                    match_fecha = re.search(r"EMISI[ÓO]N[:\s]*(\d{2}/\d{2}/\d{2,4})", texto_pagina, re.IGNORECASE)
                    if match_fecha:
                        partes_fecha = match_fecha.group(1).split("/")
                        dia = int(partes_fecha[0])
                        mes = int(partes_fecha[1])
                        anio = int(partes_fecha[2])
                        if anio < 100:
                            anio += 2000
                        
                        if anio > anio_actual or (anio == anio_actual and mes >= mes_actual):
                            es_pendiente = False
                    else:
                        tiempo_mod = os.path.getmtime(ruta_completa)
                        fecha_mod = date.fromtimestamp(tiempo_mod)
                        if fecha_mod.year > anio_actual or (fecha_mod.year == anio_actual and fecha_mod.month >= mes_actual):
                            es_pendiente = False
                except Exception:
                    pass

                if es_pendiente:
                    self.archivos_pendientes.append(archivo)
                    self.listbox_pend.insert(tk.END, archivo)
                else:
                    self.archivos_actualizados.append(archivo)
                    self.listbox_act.insert(tk.END, archivo)

    def abrir_ventana_edicion(self):
        try:
            seleccion = self.listbox_pend.curselection()
            if not seleccion:
                messagebox.showwarning("Aviso", "Por favor seleccione un seguro pendiente de la lista.")
                return
            
            archivo_seleccionado = self.archivos_pendientes[seleccion[0]]
            
            ven_edit = tk.Toplevel(self.root)
            ven_edit.title(f"Actualizar: {archivo_seleccionado}")
            ven_edit.geometry("380x300")
            ven_edit.grab_set()

            tk.Label(ven_edit, text=f"Modificando seguro:\n{archivo_seleccionado}", font=("Arial", 10, "bold")).pack(pady=10)

            tk.Label(ven_edit, text="Nuevo Importe (dejar vacío para mantener original sin aumento):").pack()
            txt_importe = tk.Entry(ven_edit, width=20)
            txt_importe.pack(pady=5)

            tk.Label(ven_edit, text="Cantidad de Cuotas (ej: 4 se pone como 1/4):").pack()
            txt_cuotas = tk.Entry(ven_edit, width=20)
            txt_cuotas.pack(pady=5)

            var_pagar_todas = tk.BooleanVar()
            chk_pagar_todas = tk.Checkbutton(ven_edit, text="Pagar todas (ej: 1,2,3/3 o 1,2,3,4/4)", variable=var_pagar_todas)
            chk_pagar_todas.pack(pady=5)

            def guardar_cambios():
                try:
                    porcentaje = float(self.txt_aumento.get())
                except ValueError:
                    porcentaje = 0.0

                imp_val = txt_importe.get().strip()
                cuo_val = txt_cuotas.get().strip()
                cuo_num = int(cuo_val) if cuo_val != "" else None
                pagar_todas_val = var_pagar_todas.get()

                ruta_pdf = os.path.join(self.carpeta_path, archivo_seleccionado)
                
                procesar_seguro(
                    ruta_pdf, 
                    self.carpeta_path, 
                    porcentaje, 
                    cuotas_custom=cuo_num, 
                    importe_custom=imp_val if imp_val != "" else None,
                    pagar_todas=pagar_todas_val
                )
                
                messagebox.showinfo("Éxito", "¡Seguro actualizado correctamente!")
                ven_edit.destroy()
                self.cargar_archivos()

            tk.Button(ven_edit, text="Guardar y Generar PDF", bg="#28a745", fg="white", font=("Arial", 10, "bold"), command=guardar_cambios).pack(pady=15)

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppGestorSeguros(root)
    root.mainloop()