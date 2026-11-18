# TripoSR 本地单图生成

TripoSR 在 Windows 上将一张参考图重建为带顶点颜色的 GLB，接着复用 Figurine Maker 的 Blender 流程。本地模型权重下载完成后可离线推理。TripoSR 的代码和权重采用 MIT 许可。运行时归档提供适配器和安装脚本。 [TripoSR 源码](https://github.com/VAST-AI-Research/TripoSR) · [官方模型权重](https://huggingface.co/stabilityai/TripoSR)

## 安装

从项目根目录使用 PowerShell 7 和 64 位 Python 3.12。脚本将上游源码、模型和 Python 依赖保存到 `.tools/triposr`，并验证官方主权重的 SHA‑256。GPU 版 PyTorch 约 2.7 GB，TripoSR 权重约 1.68 GB。CPU 版的 PyTorch 下载较小。

```powershell
.\scripts\setup-triposr.ps1 -Python 'C:\path\to\python.exe' -Device cpu
. .\scripts\initialize.ps1 -Python 'C:\path\to\python.exe' -Blender 'C:\path\to\blender.exe'
& 'C:\path\to\python.exe' -m figurine_runtime run --job examples/triposr_local/job.json
```

示例默认安装 CPU 版本。运行时优先使用已安装的 CPU 版本，也可显式设置 `$env:FIGURINE_TRIPOSR_DEVICE = 'cpu'`。GPU 版本可用 `-Device cuda` 安装，并以 `$env:FIGURINE_TRIPOSR_DEVICE = 'cuda'` 运行。本机 GPU 版在加载 CUDA 动态库时被 Windows 应用控制拦截，GPU 推理尚未通过。可用 `FIGURINE_TRIPOSR_HOME` 指定工具目录，用 `FIGURINE_TRIPOSR_PYTHON` 指定生成进程的 Python。

## 使用自己的图片

复制 `examples/triposr_local`，替换里面的参考图并更新作业中的 `source_images`，保留 `"provider": "triposr"`。优先使用主体完整、边缘清晰的图。透明 PNG 直接使用透明度，其他图片由本机 U2NetP 抠图。重复运行时传新的 `--output`。

`models/original.glb` 保存生成网格，`models/triposr-input.png` 是实际送入模型的预处理图，`models/triposr.log` 记录设备和提取后的面数。Blender 检查失败时，先用 GLB 和前后预览定位问题。侧面和背面由单图推断。薄壁、支撑及实际打印需按自己的打印条件检查。

适配器使用上游模型推理、scikit-image 提取等值面和上游的 GLB 轴向转换。该路径使用预编译的 Python 依赖，省去了 Windows 下编译 torchmcubes 的步骤。

本机已用 CPU 成功生成示例机器人并完成 STL、GLB、BLEND 导出重读，目标高度 150 mm。网格轮廓较粗，脸部小特征有丢失，底座直径约 170 mm。首次切片提示局部悬空，使用下面的参数启用支撑重新检查。

```powershell
.\scripts\slice-bambu.ps1 -Mesh projects/triposr-local/print/figurine.stl -Output projects/triposr-slice-supported -EnableSupport
python scripts/check-triposr.py projects/triposr-local --slice-output projects/triposr-slice-supported
```
