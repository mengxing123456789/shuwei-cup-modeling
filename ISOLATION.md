# 独立性与隔离性自证（2026-11-18）

这份文件回答两个问题：**还需不需要那套外部商业工作台**，以及**这套东西会不会漏到别的工作区**。
每条结论后面都带可复算的命令，照抄就能自己验。

---

## 0 一句话结论

- **不需要了**：技能树里已经 0 处外部产品名、0 处它的安装路径；把 PATH 里含该产品名的 65 段全部剔除后，八步流水线与十九道门照跑，结果不变。
- **不会漏**：所有可执行物都在 `E:\数学建模\.agents\skills\` 下（工作区级，只在打开这个工作区时被加载）。唯一的宿主机级足迹是**两条小队名册**（见 §3），它们没有数据、也不写入任何别的工作区。

---

## 1 依赖断干净了：逐条证据

### 1.1 字样归零

```powershell
# 技能树（唯一会被加载的代码）
Get-ChildItem 'E:\数学建模\.agents\skills' -Recurse -File -Include *.py,*.md,*.mjs |
  Select-String -Pattern 'modex|Modex|MODEX'      # → 0 行
```

本轮清掉的最后四处：`WORKFLOW.md:15/271/273/282`（改写成「上一代商业工作台」与「外部工作台」）、
`scripts/pipeline.py:17`、`scripts/submission_gate.py:10`。

### 1.2 安装路径归零

```powershell
Get-ChildItem 'E:\数学建模\.agents\skills' -Recurse -File -Include *.py,*.md |
  Select-String -Pattern 'modex-mh-agent|ModexData|resources\\app|runtime\\python'   # → 0 行
```

### 1.3 取证目录已删

`E:\数学建模\_modex_re\`（146 文件 / 2,255,547 B）连同 `数维杯\05_模板与工具\latex\_modexenv_test.png`
与 `.mh\vision_ledger.json` 里那条指向它的缓存，一并删除。删的是**取证副本**，交付物在
`skills\paper-kit\` 里另有一份，功能不受影响。

### 1.4 运行时不摸它的任何组件

```powershell
$clean = ($env:PATH -split ';' | Where-Object { $_ -and $_ -notmatch 'modex' }) -join ';'
$env:PATH = $clean            # 65 段，含该产品名的 0 段
& E:\Mini\envs\mathmodel\python.exe scripts\pipeline.py . --status
& E:\Mini\envs\mathmodel\python.exe scripts\pipeline.py . --skip-dispatch --only s6 --force s6
```

实测结果与清 PATH 之前**逐门一致**：s1 G1/G2 PASS，s2 G3 PASS，s3 G4/G5 PASS + G10 软闸门，
s5 G6 PASS + G11 软闸门，s6 G7/G12/G17 全 PASS，s7 G8/G13/G15/G18/G19 全 PASS + G14 软闸门，
`gauntlet 16/16`，venue `0 项要你处理`。

### 1.5 解释器与外部依赖只剩本机的三样

| 依赖 | 用处 | 缺了会怎样 |
|---|---|---|
| `E:\Mini\envs\mathmodel\python.exe` | 全部脚本（numpy/scipy/pymupdf/python-docx… 174 包） | 换 `sys.executable`，脚本自己找 |
| `E:\MIKTEX\...\xelatex.exe` | 编译（两遍） | s7 的 compile 门判 FAIL，其余不受影响 |
| `node`（PATH 里任意一个） | 只在**派单**时驱动宿主；已随技能内置 `vendor\discover.mjs` | 退化成 `--skip-dispatch` 离线跑门 |

写死的 `D:\Python\python.exe` 与 `C:\Program Files\nodejs\node.exe` 这轮已改成运行时解析
（`sys.executable` / `shutil.which("node")` + 候选表），`crew.RUNNER` 现在优先取
`scripts\..\vendor\discover.mjs`，拿不到才退回用户级的 `squad-runner`。改完 `Ran 47 tests, OK`。

---

## 2 为什么不做成插件（做了反而更脏）

DSH 的插件是**按 profile 安装、在每个工作区都加载的**。把数学建模打包成插件，等于让它出现在
你所有工作区的工具面里 —— 与「只应用于该工作区」正好相反。

现在这套的落地方式是更窄的一档：

| 档位 | 作用域 | 本项目用没用 |
|---|---|---|
| profile 插件（`plugin_manager`） | 该 profile 的**每个**工作区 | 没用 |
| 用户级技能 `C:\Users\29900\.agents\skills\` | 每个工作区都可见 | 没用（`paper-kit`/`mathmodeling` 都不在这里） |
| **工作区级技能 `E:\数学建模\.agents\skills\`** | **只有这个工作区加载** | **全部内容在这里** |

所以「插件只应用于该工作区」这个诉求，已经被目录位置满足了，不需要额外打包。

---

## 3 唯一的宿主级足迹：两条小队名册

小队存在 `C:\Users\29900\.dsh\dsh-agents\ledger.json`，是**宿主机级**的，因此在任何工作区的小队面板里都能看到
`数学建模小队`（17 人）与 `数学建模评审小队`（13 人）。

- 它们**不含任何工作区数据**，只是一份名字 + brief 的名册；派单时才建会话，会话落在派单时传入的目录。
- 这套 DSH 的 `ledger.json` 里 `teams[*]` 的字段是
  `['createdAt','description','id','leadPreset','name','updatedAt']` —— **没有 `workspaceId`**，
  也就是说这一版**无法**把小队绑到某个工作区。想要零足迹，只能删名册、用的时候再建。
- 如果你要「别的工作区完全看不到」，说一句我就把这两队删掉，`squads\_push.py` 一条命令能原样重建。

其余宿主级写入为零：没有注册全局技能、没有改 `cordis.patch.yml`、没有装插件、没有改环境变量。

---

## 4 会写哪些路径（全部落在本工作区内）

| 写什么 | 落在哪 |
|---|---|
| 八步产物（`out/*.md`、`data/*.json`、`figures/*`） | `<论文目录>`，例 `E:\数学建模\APMCM2026_C\` |
| 流水线状态与备份 | `<论文目录>\logs\pipeline_state.json`（改版时旧文件备份成 `.v1.bak`） |
| 临时目录视图（闸门用） | `%TEMP%\gate_*`，跑完 `cleanup()` |
| 技能自身 | 只读；`vendor\discover.mjs` 是唯一新增的静态文件 |

代码里没有任何跨工作区写入路径：脚本内的绝对路径只剩 `E:\数学建模…`、`E:\Mini\envs\mathmodel…`、
`E:\MIKTEX…` 三类，其余全是相对路径或运行时解析。

---

## 5 一条命令自检

```powershell
$py = 'E:\Mini\envs\mathmodel\python.exe'
$K  = 'E:\数学建模\.agents\skills\mathmodeling\scripts'

# ① 字样与路径归零
(Get-ChildItem 'E:\数学建模\.agents\skills' -Recurse -File -Include *.py,*.md,*.mjs |
  Select-String -Pattern 'modex-mh-agent|ModexData|modex|Modex').Count      # 期望 0

# ② 清 PATH 后仍能跑
$env:PATH = (($env:PATH -split ';' | Where-Object { $_ -notmatch 'modex' }) -join ';')
& $py "$K\pipeline.py" E:\数学建模\APMCM2026_C --status

# ③ 单测
Push-Location "$K\..\scripts"; & $py -m unittest discover -s tests; Pop-Location  # 期望 Ran 47 tests, OK
```

---

## 6 还留着的外部字样（历史快照，不影响运行）

`APMCM2026_C\out\_num\snap2|3|4\code\fig_l10n.py`、`out\_num\mut\code\_py2.py`、`code\_backup\_py2.py`
里还有该产品名 —— 那是校验器留下的**冻结快照**（用来比对历史改动的），删了会丢掉「改稿前后可比」这条证据链。
`review\01-compliance.md`、`review\06-code.md` 里也有，那是评审报告当时的原文。两者都不参与运行。
要不要一起清掉，你说一声即可。