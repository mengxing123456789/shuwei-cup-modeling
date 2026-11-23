import io

P = "main.tex"
t = io.open(P, encoding="utf-8").read()

pairs = []

# Section 6: two sentences folded into one
pairs.append((
r"""Handing the rule the true duration lifts S2 from 0.8667 to 0.9000 and S3 from 0.8448:""",
r"""Handing the rule the true duration lifts S2 from 0.8667 to 0.9000 and S3 from 0.8448,"""))

# P3 discussion: drop the redundant pointer to Appendix C
pairs.append((
r"""Failure conditions are concrete and stated so a reader can check them.""",
r"""Failure conditions are concrete."""))

# P2 discussion: compress the closing sentence
old = r"""the wait time is what the free strategy spends, and the paid look shortens the wait without
improving the forecast"""
new = r"""wait time is what the free strategy spends, and the paid look shortens it without improving
the forecast"""
pairs.append((old, new))

for old, new in pairs:
    if old not in t:
        print("MISS:", old[:50].replace("\n", " "))
    else:
        t = t.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="").write(t)
print("done")
