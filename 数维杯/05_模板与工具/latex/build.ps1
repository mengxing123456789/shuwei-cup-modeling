<#
  数维杯论文 LaTeX 一键构建（英文赛道，官方 swmcmthesis.cls）
  用法：
    .\build.ps1                 # 编 main_en（默认）
    .\build.ps1 -Clean          # 清中间文件（out\*.pdf 保留）
    .\build.ps1 -MaxPages 20    # 页数上限（默认 25）
    .\build.ps1 -Target zh      # 备用：编中文 ctexart 骨架
  产出：out\main_en.pdf + 页数/超限/警告摘要
#>
param(
  [ValidateSet('en','zh')][string]$Target = 'en',
  [switch]$Clean,
  [int]$MaxPages = 25
)

$ErrorActionPreference = 'Continue'
$mik    = 'E:\MIKTEX\miktex\miktex\bin\x64'
$envdir = 'E:\Mini\envs\mathmodel'
$python = Join-Path $envdir 'python.exe'
$root   = $PSScriptRoot
$out    = Join-Path $root 'out'
$fig    = Join-Path $root 'figures'

# conda 环境必须进 PATH：直接调 python.exe 时 Library\bin 缺失会让 matplotlib
# 在 savefig 阶段抛 0xC06D007F(delay-load failure)，整只进程直接被 kill
$env:PATH = "$mik;$envdir;$envdir\Library\mingw-w64\bin;$envdir\Library\usr\bin;" +
            "$envdir\Library\bin;$envdir\Scripts;$envdir\bin;" + $env:PATH

if ($Clean) {
  foreach ($pat in '*.aux','*.log','*.out','*.toc','*.fls','*.fdb_latexmk','*.bbl','*.blg','*.xdv','*.synctex.gz','*.lof','*.lot') {
    Get-ChildItem $root -Filter $pat -ErrorAction SilentlyContinue | Remove-Item -Force
  }
  Write-Host '中间文件已清理（out\*.pdf 保留）' -ForegroundColor DarkGray
  if ($PSBoundParameters.Keys.Count -eq 1) { return }
}

# ---------- 0) 官方类文件必须在 .tex 同目录 ----------
# MiKTeX 的 TEXINPUTS 不含本目录，cls 放 official\ 子目录会报
#   ! LaTeX Error: File `swmcmthesis.cls' not found.
foreach ($f in 'swmcmthesis.cls','swmcmthesis.cfg') {
  $src = Join-Path $root "official\$f"
  if ((Test-Path $src) -and -not (Test-Path (Join-Path $root $f))) {
    Copy-Item $src $root -Force
    Write-Host "  · 从 official\ 补 $f" -ForegroundColor DarkGray
  }
}

# ---------- 1) 图 ----------
if (Test-Path (Join-Path $fig 'fig_convergence.pdf')) {
  Write-Host '[1/3] 图已存在，跳过（改数据后删 figures\ 重跑）' -ForegroundColor DarkGray
} else {
  Write-Host '[1/3] 生成图 ...' -ForegroundColor Cyan
  & $python (Join-Path $root 'gen_figures.py')
  if ($LASTEXITCODE -ne 0) { Write-Host "  ✗ 出图失败 exit=$LASTEXITCODE" -ForegroundColor Red }
}

New-Item -ItemType Directory -Force -Path $out | Out-Null

# ---------- 2) 编译 ----------
# en: 官方 swmcmthesis.cls 声明 !TeX program = pdflatex，且用 newtxtext/newtxmath；
#     xelatex 会因 newtx 的 T1 编码路径出问题，所以固定 pdflatex，跑 3 遍
#     （目录 + LastPage 交叉引用）。参考文献是手写 thebibliography，不需要 bibtex。
# zh: 备用 ctexart 骨架，xelatex + biber。
#     biblatex 需要三轮：1 出 .bcf → biber → 2 读 .bbl → 3 定稿交叉引用
$cfg = @{
  en = @{ Tex = 'main_en'; Engine = 'pdflatex'; Passes = 3; Bib = 'none' }
  zh = @{ Tex = 'main_zh'; Engine = 'xelatex';  Passes = 3; Bib = 'biber' }
}
$c = $cfg[$Target]
$d = $c.Tex
if (-not (Test-Path (Join-Path $root "$d.tex"))) {
  Write-Host "缺 $d.tex" -ForegroundColor Red; exit 1
}

Push-Location $root
Write-Host "[2/3] 编译 $d.tex（$($c.Engine) ×$($c.Passes)）..." -ForegroundColor Cyan
$sw = [Diagnostics.Stopwatch]::StartNew()

& $c.Engine -interaction=nonstopmode -file-line-error "$d.tex" 2>&1 | Out-Null
$rc = $LASTEXITCODE

if ($rc -eq 0 -and $c.Bib -eq 'biber' -and (Test-Path "$d.bcf")) {
  & biber $d 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Host '  ⚠ biber 报错（见 .blg）' -ForegroundColor Yellow }
}

for ($i = 2; $i -le $c.Passes; $i++) {
  & $c.Engine -interaction=nonstopmode -file-line-error "$d.tex" 2>&1 | Out-Null
  $rc = $LASTEXITCODE
}
$sw.Stop()
Pop-Location

if ($rc -ne 0 -or -not (Test-Path "$root\$d.pdf")) {
  Write-Host "  ✗ 编译失败" -ForegroundColor Red
  if (Test-Path "$root\$d.log") {
    Select-String -Path "$root\$d.log" -Pattern '^\S+\.\w+:\d+:|^! ' | Select-Object -First 12 |
      ForEach-Object { '    ' + $_.Line.Trim() }
  }
  exit 1
}

Copy-Item "$root\$d.pdf" (Join-Path $out "$d.pdf") -Force

# ---------- 3) 体检 ----------
$pages = & $python -c "import pymupdf,sys; print(pymupdf.open(sys.argv[1]).page_count)" (Join-Path $out "$d.pdf")
if ($LASTEXITCODE -ne 0) { $pages = '?' }
$kb  = [math]::Round((Get-Item (Join-Path $out "$d.pdf")).Length / 1KB, 1)
$bad = ($pages -ne '?') -and ([int]$pages -gt $MaxPages)
Write-Host ("  ✓ {0}：{1} 页 / {2} KB / {3:N1}s{4}" -f $d, $pages, $kb, $sw.Elapsed.TotalSeconds,
            $(if ($bad) { "  ⚠ 超 $MaxPages 页上限" } else { '' })) `
  -ForegroundColor $(if ($bad) { 'Yellow' } else { 'Green' })

if (Test-Path "$root\$d.log") {
  $issues = Select-String -Path "$root\$d.log" -Pattern 'LaTeX Warning: (Reference|Citation|There were undefined)|Missing character' |
            ForEach-Object { $_.Line.Trim() } | Select-Object -Unique
  if ($issues) {
    Write-Host "  警告 $($issues.Count) 条（前 6）：" -ForegroundColor Yellow
    $issues | Select-Object -First 6 | ForEach-Object { '    ' + $_ }
  } else {
    Write-Host '  无未定义引用 / 缺字符' -ForegroundColor DarkGray
  }
}

# 占位符计数：交稿前必须归零
$ph = (Select-String -Path "$root\$d.tex" -Pattern '\[[A-Za-z][^\]]{2,80}\]' -AllMatches).Matches.Count
Write-Host "  占位符 [..] 剩余：$ph 处（交稿前清零）" -ForegroundColor $(if ($ph -gt 0) { 'Yellow' } else { 'Green' })

Write-Host "`n完成。PDF：$out" -ForegroundColor Cyan