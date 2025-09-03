# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd

from conciliacion.ui import (
    draw_header,
    upload_files_section,
    sheet_and_header_section,
    preview_tabs,
    mapping_section,
    filters_section,            # checklist de conceptos
    matching_params_section,    # ventana_dias y ordenar_por_emision
    decimals_section,           # << NUEVO: solo selector de decimales
)
from conciliacion.transform import (
    apply_extract_transformations,
    apply_system_transformations,
    split_system_unmatched_by_due,
    build_views_for_output,
)
from conciliacion.matching import match_one_to_one_by_amount_and_date
from conciliacion.export import to_excel_with_sections


# ==============================
# App principal (Streamlit)
# ==============================
st.set_page_config(page_title="Conciliacion Bancaria - 1 a 1 por fecha", layout="wide")

draw_header()

# 1) Subida de archivos
f_ext, f_sys = upload_files_section()
if not (f_ext and f_sys):
    st.info("Subí ambos archivos para configurar la conciliación.")
    st.stop()

# 2) Selección de hojas + fila de encabezado
sh_ext, hd_ext, sh_sys, hd_sys, df_ext_raw, df_sys_raw = sheet_and_header_section(f_ext, f_sys)

# 3) Previsualización
preview_tabs(df_ext_raw, df_sys_raw)

# 4) Mapeo de columnas
(
    ext_col_fecha, ext_col_concepto, ext_col_importe,
    sys_col_emision, sys_col_venc, modo_importe,
    sys_col_importe, sys_col_debe, sys_col_haber
) = mapping_section(df_ext_raw, df_sys_raw)

# 5) Decimales (único parámetro de normalización visible)
DECIMALES = decimals_section()

# Flags fijos (no se muestran más en UI)
NORMALIZAR_TEXTO = True
USAR_ABS = False

# 6) Filtros (SOLO checklist de conceptos)
excluir_exact, fecha_corte = filters_section(
    df_ext_raw=df_ext_raw,
    ext_col_concepto=ext_col_concepto,
)

# 7) Parámetros de matching (ventana por defecto = 0)
ventana_dias, ordenar_por_emision = matching_params_section()

# 8) Transformaciones
df_ext, df_ext_excl = apply_extract_transformations(
    df_ext_raw=df_ext_raw,
    col_fecha=ext_col_fecha,
    col_concepto=ext_col_concepto,
    col_importe=ext_col_importe,
    excluir_exact=excluir_exact,
    normalizar_texto=NORMALIZAR_TEXTO,
    decimales=DECIMALES,
)

df_sys = apply_system_transformations(
    df_sys_raw=df_sys_raw,
    col_emision=sys_col_emision,
    col_venc=sys_col_venc,
    modo_importe=modo_importe,
    col_importe=sys_col_importe,
    col_debe=sys_col_debe,
    col_haber=sys_col_haber,
    decimales=DECIMALES,
    usar_abs=USAR_ABS,
)

# 9) Emparejamiento 1-1 (importe con signo + fecha más cercana)
pairs, used_sys, used_ext = match_one_to_one_by_amount_and_date(
    df_sys=df_sys,
    df_ext=df_ext,
    ventana_dias=ventana_dias,
    ordenar_por_emision=ordenar_por_emision,
)

# 10) Tablas de salida
correctos, solo_ext, solo_sys = build_views_for_output(
    pairs=pairs,
    df_ext=df_ext,
    df_sys=df_sys,
    ext_cols=(ext_col_fecha, ext_col_concepto, ext_col_importe),
    sys_cols=(sys_col_emision, sys_col_venc, sys_col_importe, sys_col_debe, sys_col_haber),
    modo_importe=modo_importe,
    used_ext=used_ext,
    used_sys=used_sys,
)

# 11) Partición sistema sin extracto
solo_sistema_vencidos, solo_sistema_diferidos = split_system_unmatched_by_due(
    solo_sys=solo_sys,
    col_emision=sys_col_emision,
    col_venc=sys_col_venc,
    col_importe=sys_col_importe,
    col_debe=sys_col_debe,
    col_haber=sys_col_haber,
    fecha_corte=fecha_corte,
    modo_importe=modo_importe,
)

# 12) Resumen de DESCARTADOS (si hay)
descartados_resumen = pd.DataFrame()
if df_ext_excl is not None and not df_ext_excl.empty:
    descartados_resumen = (
        df_ext_excl
        .groupby("_CONCEPTO_", dropna=False)["_IMPORTE_SIGNED_"]
        .agg(Cantidad="count", Total="sum")
        .reset_index()
        .rename(columns={"_CONCEPTO_": "Concepto"})
        .sort_values("Total", ascending=True)
    )

# 13) UI de resultados
st.markdown("---")
st.subheader("Resultados (emparejamiento 1-1)")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Correctos (en ambos)", len(correctos))
m2.metric("Solo Extracto", len(solo_ext))
m3.metric("Sistema sin Extracto (VENCIDOS)", len(solo_sistema_vencidos))
m4.metric("Sistema sin Extracto (DIFERIDOS)", len(solo_sistema_diferidos))

with st.expander("Correctos (en ambos)"):
    st.dataframe(correctos, use_container_width=True, height=320)
with st.expander("En Extracto y NO en Sistema"):
    st.dataframe(solo_ext, use_container_width=True, height=320)
with st.expander("En Sistema y NO en Extracto — VENCIDOS"):
    st.dataframe(solo_sistema_vencidos, use_container_width=True, height=320)
with st.expander("En Sistema y NO en Extracto — POSIBLE PAGO DIFERIDO"):
    st.dataframe(solo_sistema_diferidos, use_container_width=True, height=320)

if not descartados_resumen.empty:
    with st.expander("Descartados (resumen por concepto)"):
        st.dataframe(descartados_resumen, use_container_width=True, height=320)
    total_desc = descartados_resumen["Total"].sum()
    st.caption(f"Total descartado (suma de importes): {total_desc:,.2f}")

# 14) Exportación a Excel (incluye hoja 'Descartados')
sections = [
    ("Correctos (en ambos)", correctos),
    ("Solo en Extracto", solo_ext),
    ("Sistema sin Extracto — Vencidos", solo_sistema_vencidos),
    ("Sistema sin Extracto — Diferidos", solo_sistema_diferidos),
]
if not descartados_resumen.empty:
    sections.append(("Descartados (resumen por concepto)", descartados_resumen))

extra = {
    "Correctos": correctos,
    "Solo_Extracto": solo_ext,
    "Sistema_Sin_Extracto_Vencidos": solo_sistema_vencidos,
    "Sistema_Sin_Extracto_Diferidos": solo_sistema_diferidos,
}
if df_ext_excl is not None and not df_ext_excl.empty:
    detalle = df_ext_excl.copy()
    detalle = detalle[["_FECHA_", "_CONCEPTO_", "_IMPORTE_SIGNED_", "_MOTIVO_"]].rename(columns={
        "_FECHA_": "Fecha",
        "_CONCEPTO_": "Concepto",
        "_IMPORTE_SIGNED_": "Importe",
        "_MOTIVO_": "Motivo"
    })
    extra["Descartados_Detalle"] = detalle
    extra["Descartados_Resumen"] = descartados_resumen

excel_bytes = to_excel_with_sections(sections, extra_sheets=extra)

st.download_button(
    "Descargar reporte (Excel)",
    data=excel_bytes,
    file_name="conciliacion_lince.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
