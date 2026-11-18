# Windows 安装与复现

需要 Python 3.10+ 及 Blender 4.5 LTS。示例使用 PowerShell 7，从仓库根目录运行。Windows 的 `python` 若打开 Microsoft Store，请将它替换为实际的 `python.exe` 路径。本项目运行时使用 Python 标准库。

```powershell
. .\scripts\initialize.ps1 -Blender 'C:\tools\Blender\blender.exe'
python -m figurine_runtime validate --job examples/mock_figurine/job.json
python -m figurine_runtime run --job examples/mock_figurine/job.json
python -m figurine_runtime verify --job examples/mock_figurine/job.json
```

也可用 `python -m pip install ./runtime` 安装 `figurine` 命令。脚本以点号加载，把运行时路径和 Blender 路径设在当前 PowerShell 会话。Blender 可使用[官方便携版 ZIP](https://www.blender.org/releases/4-5/)。若便携版可执行文件放在其他目录，给 `--blender` 传实际路径，或设置 `FIGURINE_BLENDER`。

## 输入

- 文字用 `input_mode: text`、`prompt` 和明确的目标高度。先运行 `design --job …`，确认角色规格草稿，再创建图片或网格作业。
- 现有网格用 `input_mode: mesh` 和 `source_mesh`。GLB 默认 m，OBJ/STL 默认 mm，可显式设 `input_unit`。GLB 资产须嵌入文件，OBJ 旁置材质引用在处理副本中剥离。原件留在 `models/`。
- 图片用 `input_mode: image`、`source_images` 和 `provider`。mock 用合成模型测试流水线，示例参考图仅用于提供输入。可设 `mock_format: stl` 以实测 STL 路径，默认 `glb`。
- 选择 `provider: triposr` 可在本机用一张图片生成 GLB，见 [TripoSR 本地安装与复现](INSTALL_TRIPOSR.md)。
- 五官和复杂配件优先用本地 `provider: hunyuan`，见 [Hunyuan3D 本地细节重建](INSTALL_HUNYUAN.md)。
- Meshy 选择 `provider: meshy`。先核验[当前官方积分定价](https://docs.meshy.ai/en/api/pricing)和账户余额，取得此次调用及上传的授权，再设置 `allow_external_image_upload: true`、`max_paid_credits`（当前配置预估 20）、当前会话的 `MESHY_API_KEY`，并在运行时加 `--approve-paid --approve-upload`。接口使用 Meshy 7.1 标准网格、无纹理。若提交后失败，请先用报告里的远端任务 ID 检查服务端状态，避免再次扣费。

输入文件用相对于任务 JSON 的路径。重新运行时传入新的 `--output DIR`，便于对比前一版。检查 `reports/geometry.json`、`reports/quality_report.json` 和预览。底座使用圆形布尔并集，连通性和几何检查失败时查看报告。

## 测试与切片

```powershell
python tests/make_fixtures.py
python -m unittest discover -s tests -v
.\scripts\slice-bambu.ps1 -Mesh projects/mock_figurine/print/figurine.stl -Output projects/bambu
```

切片脚本示例使用 Bambu Lab A1、0.4 mm 喷嘴、0.20 mm 标准层高及 Bambu PLA Basic。给自己的机器切片时，需按真实设备与材料调整脚本中的配置。项目不向设备发送打印作业。可用 `evidence/glb-retest.job.json` 复现 GLB 往返。如果运行环境阻止 Blender 加载 GLB 依赖，`examples/mock_figurine/job.json` 提供可独立运行的 STL 样例。
