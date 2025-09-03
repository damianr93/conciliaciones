# -*- coding: utf-8 -*-
"""
Matching 1-1 por monto con signo (clave entera) y fecha cercana.
Delta de fecha = mínimo(|ext - EMISION|, |ext - VENC|).
"""

import pandas as pd
from collections import defaultdict


def _to_ordinal_safe(x):
    """Ordena fechas sin romper por NaT/None/valores raros."""
    if isinstance(x, pd.Timestamp):
        try:
            x = x.date()
        except Exception:
            return 10**12
    if x is None:
        return 10**12
    try:
        if pd.isna(x):
            return 10**12
    except Exception:
        pass
    try:
        return x.toordinal()
    except Exception:
        try:
            ts = pd.to_datetime(x, errors="coerce")
            if pd.isna(ts):
                return 10**12
            return ts.date().toordinal()
        except Exception:
            return 10**12


def _days_diff_min(ext_fecha, emision, venc):
    """Delta mínimo en días contra Emisión y Vencimiento (ignora inválidas)."""
    def _delta(a, b):
        try:
            ta = pd.to_datetime(a, errors="coerce")
            tb = pd.to_datetime(b, errors="coerce")
            if pd.isna(ta) or pd.isna(tb):
                return 999_999
            return abs((ta - tb).days)
        except Exception:
            return 999_999
    de = _delta(ext_fecha, emision)
    dv = _delta(ext_fecha, venc)
    return min(de, dv)


def match_one_to_one_by_amount_and_date(
    df_sys: pd.DataFrame,
    df_ext: pd.DataFrame,
    ventana_dias: int,
    ordenar_por_emision: bool,
):
    """
    Claves enteras (centavos):
      - Extracto: _AMT_KEY_
      - Sistema: _AMT_KEY_DEBE_POS (positivo), _AMT_KEY_HABER_NEG (negativo),
                 _AMT_KEY_PRIMARY_ (fallback)
    """
    ext_idx = df_ext.reset_index().rename(columns={"index": "_EXT_ID_"})
    sys_idx = df_sys.reset_index().rename(columns={"index": "_SYS_ID_"})

    # index del extracto por clave entera
    ext_by_key = defaultdict(list)
    for _, r in ext_idx.iterrows():
        ext_by_key[r["_AMT_KEY_"]].append(r)

    used_ext = set()
    used_sys = set()
    pairs = []

    sys_rows = list(sys_idx.to_dict("records"))
    if ordenar_por_emision:
        sys_rows.sort(key=lambda r: _to_ordinal_safe(r.get("_EMISION_")))

    for s in sys_rows:
        if s["_SYS_ID_"] in used_sys:
            continue

        keys = []
        if pd.notna(s.get("_AMT_KEY_DEBE_POS", pd.NA)):
            keys.append(int(s["_AMT_KEY_DEBE_POS"]))
        if pd.notna(s.get("_AMT_KEY_HABER_NEG", pd.NA)):
            keys.append(int(s["_AMT_KEY_HABER_NEG"]))
        if not keys and pd.notna(s.get("_AMT_KEY_PRIMARY_", pd.NA)):
            keys = [int(s["_AMT_KEY_PRIMARY_"])]

        best_delta = None
        best_e = None

        for k in keys:
            pool = [e for e in ext_by_key.get(k, []) if e["_EXT_ID_"] not in used_ext]
            if not pool:
                continue
            for e in pool:
                min_delta = _days_diff_min(e.get("_FECHA_"), s.get("_EMISION_"), s.get("_VENC_"))
                if ventana_dias > 0 and min_delta > ventana_dias:
                    continue
                if best_delta is None or min_delta < best_delta:
                    best_delta = min_delta
                    best_e = e

        if best_e is not None:
            pairs.append((s, best_e, best_delta if best_delta is not None else 0))
            used_sys.add(s["_SYS_ID_"])
            used_ext.add(best_e["_EXT_ID_"])

    return pairs, used_sys, used_ext
