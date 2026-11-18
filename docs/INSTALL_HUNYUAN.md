# Hunyuan3D 本地细节重建

Hunyuan3D-2mini Turbo 在项目中用于包含五官、复杂服装和配件的单图重建，使用 CPU 和本地权重。Windows PowerShell 7 下运行。首次安装会下载约 3.82 GB 权重及依赖。权重与代码来自腾讯，按其社区许可单独安装。 [官方模型](https://huggingface.co/tencent/Hunyuan3D-2mini) · [许可](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE)

```powershell
.\scripts\setup-hunyuan.ps1 -Python 'C:\path\to\python.exe'
. .\scripts\initialize.ps1 -Python 'C:\path\to\python.exe' -Blender 'C:\path\to\blender.exe'
python -m figurine_runtime run --job path/to/job.json
```

参照 `examples/triposr_local/job.json`，把 `provider` 改为 `hunyuan`，填入单张参考图。需要清理小游离片时可加 `"remove_small_components": true`，处理后查看报告中的删除数量和尺寸。此选项仅清理相对顶点数不超过最大组件 0.1%、最长边不超过 6 mm 的独立小碎片。生成的原件保存在 `models/original.glb`，生成时间与诊断保存在 `models/hunyuan.log`。

主权重经过固定版本和 SHA‑256 校验。安装脚本对上游分层解码中的索引坐标先转浮点，以保留小数步长。官方 Shape 模块和经过校验的权重在本机运行。
