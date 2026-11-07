# 造官网

造（ZAO）的单屏占位页，仅展示品牌标志、定位「开源 Agent 开发引擎」与主句「打造你的 Agent.」。桌面采用左右构图，手机竖屏采用上下构图。

静态 HTML 与 CSS，无 JavaScript 或构建依赖。GitHub Pages 从本仓库根目录发布，`CNAME` 保留 `zao.tools`。

## 本地预览

在本目录运行 `python3 -m http.server 8080`，访问 `http://127.0.0.1:8080/`；使用上级目录的现有服务时访问 `/website/`。

修改后检查桌面、平板、手机与矮横屏的单屏排版。页面支持减少动态效果的系统偏好。

## 目录

- `index.html`：定位文案、页面与分享元信息。
- `styles/main.css`：单屏排版、品牌样式与响应式适配。
- `scripts/sync-brand.py`：本地刷新品牌素材的工具。
- `assets/brand/`：品牌 Logo 与图标。
- `assets/images/`：主视觉与官网分享图；分享图同时保留 SVG 源文件。
- `assets/fonts/`：当前页面使用的品牌字体子集与许可证。
- `assets/sources.json`：素材来源与校验摘要。

## 更新素材

品牌主文件在相邻 `brand/`。更新文字后，刷新字体子集、分享图及资源版本：

```sh
python3 -m venv .cache/asset-tools
.cache/asset-tools/bin/python -m pip install 'fonttools[woff]' cairosvg
.cache/asset-tools/bin/python scripts/sync-brand.py
```

还需安装 `cwebp` 与系统 Cairo 库。该脚本只用于本地制作素材，网站访问和 Pages 发布均不依赖 Python。
