# 验收范围

Windows 本地测试覆盖 Python 3.12、Blender 4.5.14 LTS、Bambu Studio 02.06.00.51 与 Bambu Lab A1 预设。

| 范围 | 结果 |
|---|---|
| 配置、路径边界、生成接口错误处理 | 单元测试通过 |
| STL、GLB 与 BLEND | 合成模型导出、重读和目标尺寸通过 |
| TripoSR CPU | 合成机器人由单张图生成，150 mm STL 与自动支撑切片通过 |
| Hunyuan3D CPU | 复杂人物由单张图生成。150 mm 单一闭合组件、三格式重读和 A1 自动支撑切片通过 |
| 人物外观 | Hunyuan3D 比 TripoSR 更好地保留了发束、胸舱和装备形状。眼部和神态仍有风格化，背面由正面图推断 |
| CUDA | 此 Windows 测试机的应用控制策略阻止了 PyTorch CUDA 组件加载 |
| Meshy API | 模拟传输测试通过，付费服务实际调用未验证 |
| 网页 ChatGPT 技能触发、实体试打 | 未验证 |

可在仓库根目录初始化运行时后运行 `python -m unittest discover -s tests -v`。公开样例使用项目内生成的机器人和合成网格。客户或用户提供的输入和相应运行产物保存在本地。
