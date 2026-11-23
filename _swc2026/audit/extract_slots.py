import re, json, sys
from pathlib import Path
p = Path(r"E:\数学建模\_swc2026\audit\slots_20261120_1951.tex")
t = p.read_text(encoding="utf-8")
d = {}
for m in re.finditer(r"\\newcommand\{\\slot([A-Za-z0-9]+)\}\{([^\n]*)\}", t):
    d[m.group(1)] = m.group(2)
keys = """MaskA MaskB MaskC MaskD ConfLevel
PSegGPUARI PSegGPUValARI PSegGPUFOne PSegGPUBMae PSegGPUParams PSegGPUHeight PSegGPUDistance
PSegWardARI PSegWardFOne PSegWardBMae PSegRawARI PSegRawFOne PSegRawBMae
PEconOptT PEconOptJ PEconOptRMSE PEconCZero PEconCOne PEconLambda PEconHalfJ PEconOneJ
PDurFreeMAE PDurMidMAE PDurLongMAE PDurFreeBaseMAE PDurSelTestMAE
PStochSTwoOracleETA PStochSThreeOracleETA PStochSOneOracleETA
PStochSTwoSlackOldETA PStochSThreeSlackOldETA PStochSOneSlackOldETA
PStochSTwoRiskFusionETA PStochSThreeRiskFusionETA PStochSTwoSlackFusionETA PStochSThreeSlackFusionETA
PStochSTwoEDFOldETA PStochSThreeEDFOldETA PStochSOneEDFOldETA
PImpSTwoAllCand PImpSThreeAllCand PImpSTwoAllBase PImpSThreeAllBase
PImpMixedHoldDelta PImpMixedHoldCI
PInfoFamSTwo PInfoFamSThree PInfoFamSOne PInfoFamPCSThree PInfoFamPCSOne PInfoFamPCSTwo
PInfoGapSTwo PInfoGapSThree PInfoGapSOne
PCFMeanErr PCFMaxErr PCFBrier PCFBrierConst PCFSkill PCFECE PCFShiftTrain PCFShiftAll PCFJobs
AlphaNom BetaNom AlphaLow AlphaHigh BetaLow BetaHigh
OnTimeFloor OnTimeFloorPct PStochSTwoSlackOldReviews PStochSThreeSlackOldReviews
PStochSTwoRiskFusionReviews PStochSThreeRiskFusionReviews
PSegGPUSeconds PTCNAUC PTCNValAUC PTCNAPLift PRelTCNTestAUC PRelTCNAPLift PRelSeconds
PGPUAWristRMSE PGPUAWristMedian PGPUAWristWithinTwo PGPUBSTwoRMSE PGPUCBothRMSE PGPUDBothRMSE PGpuRatio
PConAQNine PConDQNine PConMeanCoverage
PStochPairSTwoRiskFusionDiff PStochPairSTwoRiskFusionCI PStochPairSThreeRiskFusionDiff PStochPairSThreeRiskFusionCI
PStochPairSTwoEDFOldDiff PStochPairSThreeEDFOldDiff
PVisDurBase PVisDurSel PVisDurRel PVisSchedSTwoD PVisSchedSThreeD PVisOracleSThreeD""".split()
out = {k: d.get(k) for k in keys}
print(json.dumps(out, ensure_ascii=False, indent=2))
print("TOTAL_MACROS", len(d))