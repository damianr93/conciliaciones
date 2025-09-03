# -*- coding: utf-8 -*-
"""
Utils: lectura de archivos, parseos robustos de número/fecha y helpers.
"""

import re
import numpy as np
import pandas as pd
import streamlit as st


# -----------------------------
# Lectura de archivos y hojas
# -----------------------------
def read_any_excel(uploaded, sheet_name=0, header_row=0):
    """Leo CSV/XLS/XLSX y devuelvo DataFrame."""
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    elif name.endswith(".xlsx"):
        return pd.read_excel(uploaded, sheet_name=sheet_name, engine="openpyxl", header=header_row)
    elif name.endswith(".xls"):
        return pd.read_excel(uploaded, sheet_name=sheet_name, engine="xlrd", header=header_row)
    else:
        st.error("Formato no soportado. Usa .xls, .xlsx, o .csv")
        st.stop()


def list_sheets(uploaded):
    """Devuelvo lista de hojas de XLS/XLSX; si es CSV, devuelvo ['(CSV)']."""
    name = uploaded.name.lower()
    try:
        if name.endswith(".xlsx"):
            xf = pd.ExcelFile(uploaded, engine="openpyxl")
        elif name.endswith(".xls"):
            xf = pd.ExcelFile(uploaded, engine="xlrd")
        else:
            return ["(CSV)"]
        return xf.sheet_names
    except Exception:
        return ["(CSV)"]


# -----------------------------
# Normalización de valores
# -----------------------------
def normalize_text(x):
    """Trim + upper; NaN -> ''. No toca signos."""
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def _normalize_minus_signs(s: str) -> str:
    """Unifico guiones unicode a '-'."""
    return (s
        .replace("\u2212", "-")  # minus
        .replace("\u2012", "-")  # figure dash
        .replace("\u2013", "-")  # en dash
        .replace("\u2014", "-")  # em dash
    )


def parse_number_locale(s_raw: str, decimals=2):
    """
    Parseo robusto de números con signo y separadores:
      "$ -1200000", "ARS −1.200.000,00", "(1,200,000.00)", "1.200,00-", "+ 3.456,78"
    Decide el decimal según la última aparición entre ',' y '.'
    Devuelve float redondeado o NaN.
    """
    try:
        s = str(s_raw)
        if not s or s.strip() == "":
            return np.nan

        s = _normalize_minus_signs(s).replace("\xa0", " ").strip()

        # paréntesis contables
        neg_paren = s.startswith("(") and s.endswith(")")
        if neg_paren:
            s = s[1:-1].strip()

        # saco símbolos de moneda / letras (dejo + y -)
        s = re.sub(r"[A-Za-z$€£¥₱₡₲₵₴₦₹]", "", s)
        s = s.replace(" ", "")

        # sufijo negativo '1234-'
        suf_neg = s.endswith("-")
        if suf_neg:
            s = s[:-1]

        # si hay '-' en medio, lo muevo a leading
        if "-" in s and not s.startswith("-"):
            s = "-" + s.replace("-", "")

        # si viene con '+' leading lo quito
        if s.startswith("+"):
            s = s[1:]

        # decidir decimal
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")

        # asegurarse que cualquier '-' quede leading
        if "-" in s and not s.startswith("-"):
            s = "-" + s.replace("-", "")

        val = float(s)
        if neg_paren or suf_neg:
            val = -val

        return round(val, decimals)
    except Exception:
        return np.nan


def normalize_amount(x, decimals=2, use_abs=False):
    """Parseo de importe: respeta signo; opcional abs()."""
    v = parse_number_locale(x, decimals)
    if use_abs and pd.notna(v):
        v = abs(v)
    return v


def normalize_date(x):
    """Fecha robusta con dayfirst=True; NaT si no se puede."""
    try:
        return pd.to_datetime(x, dayfirst=True, errors="coerce").date()
    except Exception:
        return pd.NaT
