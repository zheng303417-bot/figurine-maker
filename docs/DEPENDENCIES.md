# 依赖与授权

- 本地生成现已接入 TripoSR，见 [本地安装指南](INSTALL_TRIPOSR.md)。源码和权重由官方独立下载，主权重校验通过。CPU 推理及 Blender 后处理和支撑切片已实测。独立工具目录使用 PyTorch 2.7.1、Transformers 4.49.0、scikit-image 提取等值面和 U2NetP 背景移除。

- Python、运行时包及可选 Blender：以项目 Windows 安装指南、运行时配置和 `figurine probe` 的实际结果为准；技能 ZIP 不包含运行时。
- Meshy：可选外部服务；[官方定价](https://docs.meshy.ai/en/api/pricing)说明 API 使用预付积分。Skillry 会员不代表 Meshy 积分。检查当前价格、余额与授权；真实调用及数据上传未经用户同意不得执行。实测状态见项目测试报告。
- Skillry：可选；[continuity 页面](https://skillry.dev/skills/bs-continuity-asset-set)本次公开访问失败，账号权益、版本、许可证和依赖均 UNVERIFIED。提供独立自研设计模板，不包含其代码。
- 切片器、打印机和 3MF：可选，未由技能本身提供；只有实际运行并保存证据才能报告通过。

凭据放环境变量或用户自己的安全存储，不写入任务、日志或分发包。第三方组件在使用前独立核查许可、安全和当前版本。

