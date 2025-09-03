# -*- coding: utf-8 -*-
"""
Transformaciones: normalización de DF de Extracto y Sistema,
y construcción de vistas de salida.
"""

from typing import Optional, List, Set
import numpy as np
import pandas as pd
from datetime import date
from .utils import normalize_text, normalize_amount, normalize_date


# --------------------------------------
# EXTRACTO: normalización y clave entera
# --------------------------------------
def apply_extract_transformations(
    df_ext_raw: pd.DataFrame,
    col_fecha: str,
    col_concepto: str,
    col_importe: str,
    excluir_exact: List[str],
    normalizar_texto: bool,
    decimales: int,
    excluir_contains: Optional[List[str]] = None,   # ← ahora es opcional
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    - Normalizo extracto (fecha, concepto, importe con signo).
    - Genero clave ENTERA en centavos (_AMT_KEY_) para evitar problemas de floats.
    - Aplico filtros:
        * excluir_exact: lista de conceptos exactos a quitar
        * excluir_contains: lista de palabras clave (contiene) a quitar (opcional)

    Devuelve:
      (df_ext_filtrado, df_ext_excluidos_con_detalle)
    """
    df_ext = df_ext_raw.copy()

    df_ext["_FECHA_"] = df_ext[col_fecha].apply(normalize_date)

    # Concepto normalizado (siempre normalizamos para que el checklist sea consistente)
    df_ext["_CONCEPTO_"] = df_ext[col_concepto].apply(normalize_text) if normalizar_texto \
                           else df_ext[col_concepto].astype(str).fillna("")

    # Importe con signo (no uso abs acá)
    df_ext["_IMPORTE_SIGNED_"] = df_ext[col_importe].apply(lambda v: normalize_amount(v, decimales, use_abs=False))

    # Clave entera (centavos)
    scale = 10 ** int(decimales)

    def to_key(v):
        try:
            if pd.isna(v):
                return pd.NA
            return int(round(float(v) * scale))
        except Exception:
            return pd.NA

    df_ext["_AMT_KEY_"] = df_ext["_IMPORTE_SIGNED_"].apply(to_key)

    # ---- Filtros ----
    excluir_exact_set = set((normalize_text(x) if normalizar_texto else str(x).strip()) for x in (excluir_exact or []))
    excluir_contains_list = excluir_contains or []

    def exclusion_reason(concepto: str) -> str | None:
        if concepto in excluir_exact_set:
            return f"EXACTO:{concepto}"
        for kw in excluir_contains_list:
            # si normalizar_texto=False, no tocamos el caso; en nuestra app viene siempre normalizado
            if (kw in concepto) if normalizar_texto else (kw in concepto):
                return f"CONTIENTE:{kw}"
        return None

    reasons = df_ext["_CONCEPTO_"].apply(exclusion_reason)
    mask_keep = reasons.isna()

    df_ext_kept = df_ext[mask_keep].copy()
    df_ext_excl = df_ext[~mask_keep].copy()
    if not df_ext_excl.empty:
        df_ext_excl["_MOTIVO_"] = reasons[~mask_keep].values

    return df_ext_kept, df_ext_excl


# --------------------------------------
# SISTEMA: normalización y claves enteras
# --------------------------------------
def apply_system_transformations(
    df_sys_raw: pd.DataFrame,
    col_emision: str,
    col_venc: str,
    modo_importe: str,
    col_importe: Optional[str],
    col_debe: Optional[str],
    col_haber: Optional[str],
    decimales: int,
    usar_abs: bool,
) -> pd.DataFrame:
    """
    Normalizo el sistema:
    - _EMISION_ y _VENC_ como fechas.
    - Si modo = "Columna única": _IMPORTE_MATCH_KEY_ respeta usar_abs.
    - Si modo = "Debe/Haber": Debe -> +abs, Haber -> -abs y claves enteras:
        _AMT_KEY_DEBE_POS, _AMT_KEY_HABER_NEG
    - _AMT_KEY_PRIMARY_ desde _IMPORTE_MATCH_KEY_ (fallback)
    """
    df_sys = df_sys_raw.copy()
    df_sys["_EMISION_"] = df_sys[col_emision].apply(normalize_date)
    df_sys["_VENC_"] = df_sys[col_venc].apply(normalize_date)

    df_sys["_DEBE_NORM_"] = np.nan
    df_sys["_HABER_NORM_"] = np.nan

    if modo_importe == "Columna única":
        df_sys["_IMPORTE_MATCH_KEY_"] = df_sys[col_importe].apply(lambda v: normalize_amount(v, decimales, usar_abs))
    else:
        df_sys["_DEBE_NORM_"] = df_sys[col_debe].apply(lambda v: normalize_amount(v, decimales, use_abs=False))
        df_sys["_HABER_NORM_"] = df_sys[col_haber].apply(lambda v: normalize_amount(v, decimales, use_abs=False))
        df_sys["_DEBE_NORM_"] = df_sys["_DEBE_NORM_"].abs()
        df_sys["_HABER_NORM_"] = df_sys["_HABER_NORM_"].abs()

        def signed_primary(row):
            d = row["_DEBE_NORM_"]
            h = row["_HABER_NORM_"]
            if pd.notna(d) and d != 0:  # Debe = +
                return +d
            if pd.notna(h) and h != 0:  # Haber = -
                return -h
            return np.nan

        df_sys["_IMPORTE_MATCH_KEY_"] = df_sys.apply(signed_primary, axis=1)

    # claves enteras (centavos)
    scale = 10 ** int(decimales)

    def to_key(v):
        try:
            if pd.isna(v):
                return pd.NA
            return int(round(float(v) * scale))
        except Exception:
            return pd.NA

    df_sys["_AMT_KEY_PRIMARY_"] = df_sys["_IMPORTE_MATCH_KEY_"].apply(to_key)
    df_sys["_AMT_KEY_DEBE_POS"] = pd.NA
    df_sys["_AMT_KEY_HABER_NEG"] = pd.NA

    if modo_importe != "Columna única":
        df_sys["_AMT_KEY_DEBE_POS"]  = df_sys["_DEBE_NORM_"].apply(lambda v: to_key(+v))
        df_sys["_AMT_KEY_HABER_NEG"] = df_sys["_HABER_NORM_"].apply(lambda v: to_key(-v))

    return df_sys


# --------------------------------------
# Vistas de salida
# --------------------------------------
def build_views_for_output(
    pairs: list,
    df_ext: pd.DataFrame,
    df_sys: pd.DataFrame,
    ext_cols: tuple,
    sys_cols: tuple,
    modo_importe: str,
    used_ext: Set[int],
    used_sys: Set[int],
):
    ext_col_fecha, ext_col_concepto, ext_col_importe = ext_cols
    sys_col_emision, sys_col_venc, sys_col_importe, sys_col_debe, sys_col_haber = sys_cols

    correctos_rows = []
    for s, e, delta in pairs:
        row = {
            "Emisión (Sistema)": s[sys_col_emision],
            "Vencimiento (Sistema)": s[sys_col_venc],
        }
        if modo_importe == "Columna única":
            row["Importe (Sistema)"] = s.get(sys_col_importe)
        else:
            row["Debe (Sistema)"] = s.get(sys_col_debe)
            row["Haber (Sistema)"] = s.get(sys_col_haber)
        row.update({
            "Fecha (Extracto)": e[ext_col_fecha],
            "Concepto (Extracto)": e[ext_col_concepto],
            "Importe (Extracto, ±)": e[ext_col_importe],
            "Δ días |fecha ext − emisión/venc|": delta
        })
        correctos_rows.append(row)
    correctos = pd.DataFrame(correctos_rows)

    ext_idx = df_ext.reset_index().rename(columns={"index": "_EXT_ID_"})
    solo_ext = ext_idx[~ext_idx["_EXT_ID_"].isin(used_ext)][[ext_col_fecha, ext_col_concepto, ext_col_importe]].copy()
    solo_ext.columns = ["Fecha", "Concepto", "Importe"]

    sys_idx = df_sys.reset_index().rename(columns={"index": "_SYS_ID_"})
    solo_sys = sys_idx[~sys_idx["_SYS_ID_"].isin(used_sys)].copy()

    return correctos, solo_ext, solo_sys


def split_system_unmatched_by_due(
    solo_sys: pd.DataFrame,
    col_emision: str,
    col_venc: str,
    col_importe: Optional[str],
    col_debe: Optional[str],
    col_haber: Optional[str],
    fecha_corte: date,
    modo_importe: str,
):
    solo_sys_venc = solo_sys[solo_sys["_VENC_"].apply(lambda d: pd.notna(d) and d <= fecha_corte)]
    solo_sys_dif = solo_sys[solo_sys["_VENC_"].apply(lambda d: pd.notna(d) and d > fecha_corte)]

    def sys_view(df):
        cols = [col_emision, col_venc]
        if modo_importe == "Columna única":
            cols.append(col_importe)
        else:
            cols.extend([col_debe, col_haber])
        out = df[cols].copy()
        out.rename(columns={
            col_emision: "Emisión",
            col_venc: "Vencimiento",
            **({col_importe: "Importe"} if modo_importe == "Columna única" else {col_debe: "Debe", col_haber: "Haber"})
        }, inplace=True)
        return out

    return sys_view(solo_sys_venc), sys_view(solo_sys_dif)
