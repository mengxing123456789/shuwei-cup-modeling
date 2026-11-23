import sys
sys.path.insert(0,r"<skill>\scripts")
import gauntlet_check as G
P=G.find_paper(r"E:\数学建模\_swc2026\SWC2026_A")
c=G.G.check_compliance(P)
print("distinct_of",c.distinct_of,"contig",c._numbers_are_contiguous,"uni",c.university_hits,"placeholder",c.placeholder_team)
print([a for a in dir(c) if 'number' in a.lower() or 'page' in a.lower()])
print(getattr(c,"numerators",None))
