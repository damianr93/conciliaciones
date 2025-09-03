# -*- coding: utf-8 -*-
"""
Exportación a Excel con hoja Resumen y hojas separadas por tabla.
"""

from io import BytesIO
import pandas as pd


def to_excel_with_sections(sections: list, extra_sheets: dict = None) -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        startrow = 0
        sheet = "Resumen"
        for title, df in sections:
            pd.DataFrame({"Sección": [title]}).to_excel(writer, sheet_name=sheet, startrow=startrow, index=False)
            startrow += 1
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.to_excel(writer, sheet_name=sheet, startrow=startrow, index=False)
                startrow += len(df) + 2
            else:
                pd.DataFrame({"(sin filas)": []}).to_excel(writer, sheet_name=sheet, startrow=startrow, index=False)
                startrow += 3

        if extra_sheets:
            for name, df in extra_sheets.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df.to_excel(writer, sheet_name=name[:31], index=False)
                else:
                    pd.DataFrame({"Info": ["(sin filas)"]}).to_excel(writer, sheet_name=name[:31], index=False)

    output.seek(0)
    return output
