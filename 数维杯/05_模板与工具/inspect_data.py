#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Inspect an Excel workbook: sheets, shape, dtypes, head, missing counts."""
import sys, pathlib
import pandas as pd

def main():
    path = pathlib.Path(sys.argv[1])
    xls = pd.ExcelFile(path)
    print(f"FILE {path.name} size={path.stat().st_size}")
    print("SHEETS", xls.sheet_names)
    for sh in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sh, header=None, nrows=12)
        full = pd.read_excel(path, sheet_name=sh, header=None)
        print(f"\n--- sheet={sh} shape={full.shape}")
        print(full.head(12).to_string(max_cols=14))
        print("missing_by_col(first 14):", full.iloc[:, :14].isna().sum().tolist())
        print("tail:")
        print(full.tail(3).to_string(max_cols=14))

if __name__ == "__main__":
    main()