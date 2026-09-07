# Math Diagram Vectorizer

把题目中的模糊数学图重绘成可无限放大的、文字可编辑的 SVG。默认不改变原图结构。

## 安装

该目录已经是 Codex Skill 安装目录。首次使用前，在本目录运行：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Geometry DSL 已固定在 `third_party/geometry-dsl`，并已安装本地 PNG 渲染依赖。

## 日常使用

在支持 Skills 的环境中上传图片并说“高清重绘这张图”即可。Skill 会先识图并建立 MDIR，再自动调用本地渲染脚本。

命令行仅供排查或批量运行：

```bash
bin/math-vectorize input.png --mdir diagram.json --mode faithful
```

输出位于 `output/job_xxx/`：`semantic.json`、MDIR、`diagram.svg`、
`check_report.md`，以及原图副本、裁剪图、Geometry DSL 诊断、PNG、overlay
和 `report.json`。

## 模式

- `faithful`：默认，优先复刻原图布局和线型。
- `clean`：不改数学关系，仅统一线条与标签留白。
- `editable`：保留全部中间资产，便于后续说“把 D 往右移”“把 AD 改虚线”。

## 兼容性与限制

生成的是标准 SVG，自动检查 XML、可编辑图元和本地 PNG 渲染。Chrome 和 Safari
可直接打开。Word、WPS、PowerPoint、Illustrator、Inkscape 应按目标版本人工插入检查；
项目不对未实际检查的办公软件版本作兼容性承诺。

MVP 覆盖常规平面几何：点、线、三角形、四边形、圆、虚线、直角、角弧、等长刻痕、
平行标记和标签。复杂立体图、函数自动识别、Word/PPT 自动替图、TikZ 与 GeoGebra
不属于第一版。

所有裁剪、渲染与比较在本机执行；不会调用未知的第三方图片服务。
