# Yuuki Desktop

一个基于 **Live2D + PySide6** 的桌面智能萌宠应用，集成了 **多模态 AI 交互**、**屏幕感知**、**语音对话** 等功能。Yuuki 能够通过视觉和听觉感知你的工作状态，并以傲娇毒舌的方式与你互动。

---

## 🌟 功能特性

| 功能                | 说明                                                                        |
| :------------------ | :-------------------------------------------------------------------------- |
| **Live2D 模型渲染** | 使用 `live2d-py` + OpenGL 渲染 Live2D Cubism 3 模型，支持透明背景置顶显示。 |
| **智能 AI 大脑**    | 集成 Google Gemini 模型（通过 `agno`），拥有独特的人物设定（傲娇女仆）。    |
| **多模态感知**      | 支持 **屏幕视觉理解**（Screen Understanding）和 **语音听觉理解**。          |
| **屏幕变化检测**    | 实时监测屏幕显著变化，自动触发 AI 观察并吐槽你的操作。                      |
| **全双工语音交互**  | 集成 Silero VAD（语音检测）+ GLM-ASR（语音识别），支持自然语言对话。        |
| **气泡交互**        | 桌面悬浮粉色气泡，优雅地展示 AI 的回复内容。                                |
| **流量控制**        | 智能输入控制器，在 AI 思考或回复时自动屏蔽干扰输入。                        |

---

## ⚙️ 系统要求

- **操作系统**：Windows 10/11
- **Python**：>= 3.10
- **显卡**（推荐）：支持 CUDA 的 NVIDIA 显卡（用于加速 ASR 和 VAD 模型）
- **网络**：能够访问 Google Gemini API 的网络环境

---

## 🚀 安装指南

项目使用 [uv](https://docs.astral.sh/uv/) 管理依赖（也可以使用 pip）。

1. **安装 uv**（如果尚未安装）

   Windows:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   macOS / Linux:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **克隆仓库**

   ```bash
   git clone <repo-url>
   cd yuuki-desktop
   ```

3. **安装依赖**

   ```bash
   uv sync
   # 或者
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   项目需要 Google Gemini API Key 才能运行核心 AI 功能。

   复制配置文件模板：

   ```bash
   cp .env.example .env
   ```

   编辑 `.env` 文件，填入你的 API Key：

   ```ini
   GOOGLE_API_KEY=your_api_key_here
   ```

---

## 🎮 快速开始

```bash
# 启动应用
uv run main.py

# 指定模型文件
uv run main.py --model "resources/girlfriend/girlfriend.model3.json"
```

### 命令行参数

- `--model`: 指定 Live2D 模型路径 (`.model3.json`)。
- `--expressions`: 启动时自动应用的表情动作，例如 `水印关闭.exp3.json`。

---

## 💡 如何互动

1. **语音对话**：直接对着麦克风说话，Yuuki 听到完整句子后会进行回复。
2. **屏幕互动**：当你切换窗口或屏幕画面发生显著变化时，Yuuki 会“看”到你的屏幕内容并发表评论。
3. **鼠标交互**：
   - **左键拖拽**：移动 Yuuki 的位置。
   - **右键菜单**：退出程序。

---

## 📂 项目结构

```
yuuki-desktop/
├── main.py                  # 程序入口，组装各个模块
├── .env                     # 环境变量配置文件
├── resources/               # Live2D 模型资源目录
└── src/
    ├── agent.py             # AgentWorker，封装 LLM 交互逻辑
    ├── chat_bubble.py       # 桌面悬浮气泡 UI 组件
    ├── controller.py        # 输入控制器，管理并发请求
    ├── prompt.py            # AI 人设与系统提示词
    ├── screen_worker.py     # 屏幕变化检测线程
    ├── transcribe_worker.py # ASR 语音转文字线程
    └── vad_worker.py        # VAD 语音活动检测线程
```

## 🛠️ 技术栈

- **GUI**: PySide6 (Qt6)
- **Live2D**: live2d-py (OpenGL)
- **AI Agent**: Agno framework + Google Gemini
- **Vision**: OpenCV + MSS
- **Audio**: Silero VAD + GLM-ASR + SoundDevice

---

## 📄 开源协议

本项目采用 [MIT 许可证](LICENSE) 开源。

你可以自由地：

- **使用**：用于个人或商业项目。
- **修改**：根据需要修改代码。
- **分发**：复制并分享本项目。

惟需遵守以下条件：

- 在副本或修改版中包含原作者的版权声明和许可声明。

> **注意**：本项目中引用的 Live2D 模型资源可能受其原始作者的版权限制，不包含在 MIT 协议授权范围内。请在使用相关模型前确认其授权条款。
