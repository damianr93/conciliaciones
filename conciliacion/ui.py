# -*- coding: utf-8 -*-
"""
UI de la app (compatible con app.py)
- Autodetección de columnas del Sistema (Emisión, Vencimiento, Debe, Haber).
- Header del Sistema por defecto = fila 6.
- Filtro de conceptos con checklist (sin input de palabras clave).
- Sección mínima para elegir SOLO los decimales.
"""

import unicodedata
import streamlit as st
import pandas as pd
from datetime import date
from .utils import read_any_excel, list_sheets, normalize_text


# ---------- helpers de headers ----------
def _norm_hdr(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    for ch in [".", ":", ";", ","]:
        s = s.replace(ch, "")
    s = s.replace("VENCIM", "VENCIMIENTO").replace("VTO", "VENCIMIENTO")
    return s


def _find_col(cols, aliases):
    norm = [_norm_hdr(c) for c in cols]
    for i, n in enumerate(norm):
        for a in aliases:
            if a in n:
                return i
    return 0


# ---------- secciones esperadas por app.py ----------
def draw_header():
    st.title("Conciliación Extracto vs. Sistema Lince SA")
    st.caption("Match 1-1 por importe con signo (Debe→+, Haber→−) y fecha más cercana.")


def upload_files_section():
    c_up1, c_up2 = st.columns(2)
    with c_up1:
        f_ext = st.file_uploader("Extracto bancario", type=["xlsx", "xls", "csv"], key="ext")
    with c_up2:
        f_sys = st.file_uploader("Excel del sistema interno", type=["xlsx", "xls", "csv"], key="sys")
    return f_ext, f_sys


def sheet_and_header_section(f_ext, f_sys):
    sheets_ext = list_sheets(f_ext)
    sheets_sys = list_sheets(f_sys)

    c_sh1, c_sh2 = st.columns(2)
    with c_sh1:
        sh_ext = st.selectbox("Hoja (Extracto)", options=sheets_ext, index=0)
        hd_ext = st.number_input("Fila de encabezado (Extracto) [1 = primera fila]", min_value=1, value=1, step=1)
    with c_sh2:
        sh_sys = st.selectbox("Hoja (Sistema)", options=sheets_sys, index=0)
        hd_sys = st.number_input("Fila de encabezado (Sistema) [1 = primera fila] (por defecto: 6)", min_value=1, value=6, step=1)

    df_ext_raw = read_any_excel(f_ext, sheet_name=None if sheets_ext == ["(CSV)"] else sh_ext, header_row=hd_ext - 1)
    df_sys_raw = read_any_excel(f_sys, sheet_name=None if sheets_sys == ["(CSV)"] else sh_sys, header_row=hd_sys - 1)

    return sh_ext, hd_ext, sh_sys, hd_sys, df_ext_raw, df_sys_raw


def preview_tabs(df_ext_raw: pd.DataFrame, df_sys_raw: pd.DataFrame):
    st.markdown("### Vista previa")
    tab1, tab2 = st.tabs(["Extracto", "Sistema"])
    with tab1:
        st.dataframe(df_ext_raw.head(10), height=250, use_container_width=True)
        st.caption("Columnas: " + ", ".join(map(str, df_ext_raw.columns)))
    with tab2:
        st.dataframe(df_sys_raw.head(10), height=250, use_container_width=True)
        st.caption("Columnas: " + ", ".join(map(str, df_sys_raw.columns)))


def mapping_section(df_ext_raw: pd.DataFrame, df_sys_raw: pd.DataFrame):
    st.markdown("---")
    st.subheader("Mapeo de columnas")

    c1, c2 = st.columns(2)
    with c1:
        ext_col_fecha = st.selectbox("Extracto: FECHA", options=list(df_ext_raw.columns))
        ext_col_concepto = st.selectbox("Extracto: CONCEPTO", options=list(df_ext_raw.columns))
        ext_col_importe = st.selectbox("Extracto: IMPORTE (con signo)", options=list(df_ext_raw.columns))

    with c2:
        sys_cols = list(df_sys_raw.columns)
        idx_emision = _find_col(sys_cols, ["EMISION"])
        idx_venc    = _find_col(sys_cols, ["VENCIMIENTO"])
        idx_debe    = _find_col(sys_cols, ["DEBE"])
        idx_haber   = _find_col(sys_cols, ["HABER"])

        sys_col_emision = st.selectbox("Sistema: EMISIÓN", options=sys_cols, index=idx_emision)
        sys_col_venc    = st.selectbox("Sistema: VENCIMIENTO", options=sys_cols, index=idx_venc)

        modo_importe = st.radio("Sistema: ¿cómo obtener IMPORTE?", ["Columna única", "Debe/Haber"], horizontal=True, index=1)
        if modo_importe == "Columna única":
            sys_col_importe = st.selectbox("Sistema: IMPORTE", options=sys_cols)
            sys_col_debe = None
            sys_col_haber = None
        else:
            sys_col_importe = None
            sys_col_debe = st.selectbox("Sistema: DEBE", options=sys_cols, index=idx_debe)
            sys_col_haber = st.selectbox("Sistema: HABER", options=sys_cols, index=idx_haber)

    return (
        ext_col_fecha, ext_col_concepto, ext_col_importe,
        sys_col_emision, sys_col_venc, modo_importe,
        sys_col_importe, sys_col_debe, sys_col_haber
    )


# ----------- SOLO DECIMALES -----------
def decimals_section():
    st.markdown("---")
    col = st.columns(1)[0]
    with col:
        decimales = st.number_input("Decimales de importe", min_value=0, max_value=4, value=2, step=1)
    return decimales


# --------- Filtros (checklist) --------
def _concept_list_for_checklist(df_ext_raw: pd.DataFrame, col_concepto: str, top: int = 500):
    """Devuelvo una lista (ordenada por frecuencia desc) de conceptos normalizados para el checklist."""
    s = df_ext_raw[col_concepto].astype(str).map(normalize_text)
    counts = s.value_counts(dropna=False)
    opts = counts.index.tolist()[:top]
    return opts


def filters_section(df_ext_raw: pd.DataFrame, ext_col_concepto: str):
    """Filtros del extracto con checklist (multiselect). Sin palabras clave."""
    st.markdown("### Filtros del extracto")

    col1, col2 = st.columns([2, 1])

    with col1:
        opciones = _concept_list_for_checklist(df_ext_raw, ext_col_concepto)
        excluir_exact = st.multiselect(
            "Seleccioná conceptos a EXCLUIR (exactos, ya normalizados)",
            options=opciones,
            default=[]
        )
        st.caption("Sugerencias ordenadas por frecuencia. Podés buscar escribiendo en el cuadro.")

    with col2:
        fecha_corte = st.date_input("Fecha de corte para vencimientos", value=date.today())

    return excluir_exact, fecha_corte


# ----- Parámetros de matching -----
def matching_params_section():
    c8, c9 = st.columns(2)
    with c8:
        ventana_dias = st.number_input("Ventana máx. de días para matchear (0 = sin tope)", min_value=0, value=0, step=1)
    with c9:
        ordenar_por_emision = st.checkbox("Priorizar emisiones más antiguas primero", value=True)
    return ventana_dias, ordenar_por_emision
