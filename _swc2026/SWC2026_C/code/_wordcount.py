# -*- coding: utf-8 -*-
import re
import pymupdf
d = pymupdf.open("main.pdf")
words = 0
for i in range(2, 25):
    words += len(re.findall(r"[A-Za-z][A-Za-z'-]*", d[i].get_text()))
print("body words", words)
