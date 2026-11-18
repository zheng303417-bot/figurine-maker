# Figurine Maker

Figurine Maker 是一套 Windows 本地手办工作流。它把单张参考图或已有网格转换为可检查的 STL、GLB 和 BLEND，也可用 Bambu Studio 生成带支撑的切片。

- 用本地 Hunyuan3D 重建五官和复杂装备，用 TripoSR 快速起稿。
- 用 Blender 检查闭合性、调整到目标尺寸并添加底座。
- 从正面及侧面对照参考图，分别记录外观、几何和切片结果。
- 可选 Meshy API，需要用户自己的密钥和积分。

## 快速开始

安装 Python 和 Blender 后，从仓库根目录用 PowerShell 7 验证随附的合成样例。替换命令中的 Blender 路径。

```powershell
. .\scripts\initialize.ps1 -Blender 'C:\tools\Blender\blender.exe'
python -m figurine_runtime run --job examples/mock_figurine/job.json
python -m figurine_runtime verify --job examples/mock_figurine/job.json
```

这个样例使用合成网格。要用真实图片，先按对应指南安装本地生成器，再在作业 JSON 中指定参考图和生成器。

- [Windows 工作流、验证与切片](docs/INSTALL_WINDOWS.md)
- [Hunyuan3D 本地生成](docs/INSTALL_HUNYUAN.md)
- [TripoSR 本地生成](docs/INSTALL_TRIPOSR.md)
- [验收范围和已知限制](docs/TEST_REPORT.md)

## 在 Codex 中使用

将 [figurine-maker 技能目录](skill/figurine-maker)复制到 Codex 项目的 `.agents/skills/`，在运行时项目中新开对话，附上参考图并输入：

> $figurine-maker 用本地 Hunyuan3D 把这张图做成 150 mm 手办，含圆形底座。先给我看正面灰模，外观通过后再导出 STL 和 A1 带支撑 3MF。

技能入口、运行时、样例与测试均在仓库内。模型权重、Blender 和 Bambu Studio 通过其官方渠道自行安装。首次试打前按实际打印机、喷嘴及耗材核对切片设置。

第三方来源及声明见 [依赖说明](docs/DEPENDENCIES.md) 和 [Blender Skills 声明](skill/figurine-maker/THIRD_PARTY_NOTICES.md)。
