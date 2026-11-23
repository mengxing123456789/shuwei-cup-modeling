import sys
sys.path.insert(0,r"E:\数学建模\.agents\skills\mathmodeling\scripts")
import gauntlet_check as G
P=G.find_paper(r"E:\数学建模\_swc2026\SWC2026_A")
c=G.G.check_compliance(P)
print(c._header_numbers[:40], len(c._header_numbers))
