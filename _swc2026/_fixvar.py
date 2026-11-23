import pathlib
P = pathlib.Path("audit/verify_claims.py"); s = P.read_text(encoding="utf-8")
n = s.count("in tex")
s = s.replace("in tex", "in main_text")
P.write_text(s, encoding="utf-8", newline="\n")
print("replaced", n, "occurrences of 'in tex'")
