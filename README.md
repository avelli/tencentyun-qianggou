# 腾讯云抢购脚本

基于 Playwright 的腾讯云活动抢购辅助脚本。

## 特性

- 扫码登录并自动保存 Cookie
- 抓取实时 `x-csrf-token`
- 按时等待并循环发起抢购
- 支持多个地域并发尝试

## 环境要求

- Python 3.8+
- Playwright
- requests

## 安装

```bash
pip install playwright requests
playwright install chromium
```

## 使用

```bash
python snap_up.py
```

## 项目结构

- `snap_up.py`：主程序
- `cookies.json`：登录态缓存
- `csrf_token.txt`：Token 缓存

## 致谢

项目参考 [zhouyifan007/tencentyun-snake-up](https://github.com/zhouyifan007/tencentyun-snake-up) 的实现方式。

## 免责声明

本项目仅供学习、研究与个人自动化实验使用，不保证可用性、时效性或抢购结果。使用者需自行确保行为符合所在地法律法规、平台规则与活动规则；由使用本项目引起的任何账号风险、财产损失、封禁、纠纷或其他后果，均由使用者自行承担。

## 协议

本项目采用 MIT License。
