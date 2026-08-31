# DSH Video Workbench

一个独立的 React + TypeScript + Vite 前端工作台 Demo，用于演示「素材输入 → 导演 Prompt → Agent 编排 → 结果 / QA 回传」的视频生产控制台。

> 当前实现是本地 Demo Adapter。文件只在浏览器内通过 `URL.createObjectURL()` 预览；生成按钮推进的是明确标注为 `MOCK` 的状态机，不调用真实模型、不上传素材、不生成真实视频文件。

## 启动

需要 Node.js 22+：

```bash
cd /Volumes/SSK\ SSD/deepseek\ harness\ 桌面端/dsh-video-workbench
npm install
npm run dev
```

然后打开终端提示的本地地址。生产构建与预览：

```bash
npm run build
npm run preview
```

## Demo 交互

- 顶部可切换抖音、小红书、视频号，运行热点抓取与 Hook 分析的本地 UI 状态。
- 左侧 5 个槽位支持本地图片、视频、音频选择和浏览器内预览。
- 中央预览固定为 9:16，时间轴、Prompt 和素材状态会随输入更新。
- 底部「生成视频 Demo」按阶段推进：资产预检 → 动作重定向 → 镜头合成 → QA 回传。
- 结束后展示 `MOCK-...` 结果编号、QA 状态与禁用/可用的导出按钮；该结果不是模型文件。

## GitHub Pages

构建产物位于 `dist/`，Vite 已配置 `base: './'`，可将 `dist/` 作为 GitHub Pages 的静态发布目录。该目录刻意不依赖根仓库的 workspace、配置或上游 `deepseek-harness/`。
