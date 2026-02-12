# Yuuki Desktop

一个基于 **Live2D + PySide6** 的桌面宠物应用，集成了 **屏幕变化检测**、**语音活动检测（VAD）** 和 **自动语音识别（ASR）** 功能。模型以透明无边框窗口置顶显示在桌面上，支持鼠标拖拽移动。

---

## 功能一览

| 功能                | 说明                                                            |
| ------------------- | --------------------------------------------------------------- |
| **Live2D 模型渲染** | 使用 `live2d-py` + OpenGL 渲染 Live2D Cubism 3 模型，60fps 刷新 |
| **透明置顶窗口**    | 无边框、透明背景、始终置顶，不占用任务栏                        |
| **鼠标拖拽**        | 左键拖拽移动模型位置                                            |
| **表情自动应用**    | 启动时根据配置自动加载 `.exp3.json` 表情文件                    |
| **屏幕变化检测**    | 实时截屏并对比帧差异，超过阈值时触发事件                        |
| **语音活动检测**    | 使用 Silero VAD 监听麦克风输入，自动分割完整语句                |
| **语音识别**        | 使用 GLM-ASR-Nano 将检测到的语音转录为文字                      |

---

## 系统要求

- **操作系统**：Windows 10/11
- **Python**：>= 3.12
- **GPU**（推荐）：支持 CUDA 的 NVIDIA 显卡（ASR 模型加速）
- **音频输入**：麦克风或虚拟声卡

---

## 安装

项目使用 [uv](https://docs.astral.sh/uv/) 管理依赖。

```bash
# 克隆仓库
git clone <repo-url>
cd yuuki-desktop

# 安装依赖
uv sync
```

### 依赖列表

| 包名            | 用途                                     |
| --------------- | ---------------------------------------- |
| `live2d-py`     | Live2D Cubism 3 模型加载与渲染           |
| `PySide6`       | Qt6 GUI 框架（窗口、OpenGL、线程、菜单） |
| `mss`           | 高性能跨平台屏幕截图                     |
| `opencv-python` | 图像预处理与帧差异比较                   |
| `numpy`         | 音频/图像数据的数组操作                  |
| `sounddevice`   | 音频流输入（麦克风监听）                 |
| `silero-vad`    | 语音活动检测模型                         |
| `transformers`  | Hugging Face 模型加载框架                |
| `accelerate`    | 模型推理加速                             |
| `torch`         | PyTorch 深度学习运行时                   |

---

## 快速开始

```bash
# 使用默认模型启动
uv run main.py

# 指定模型文件
uv run main.py --model "resources/girlfriend/girlfriend.model3.json"

# 指定启动时自动应用的表情
uv run main.py --expressions 水印关闭.exp3.json 兽耳关闭.exp3.json
```

### 命令行参数

| 参数            | 默认值                                    | 说明                                     |
| --------------- | ----------------------------------------- | ---------------------------------------- |
| `--model`       | `resources/狐狸学姐/狐狸学姐.model3.json` | Live2D 模型文件路径（`.model3.json`）    |
| `--expressions` | `水印关闭.exp3.json`                      | 启动时自动应用的表情文件列表（空格分隔） |

### 运行时操作

- **拖拽移动**：左键按住模型拖拽
- **退出程序**：右键点击模型 → 选择「退出」

---

## 项目结构

```
yuuki-desktop/
├── main.py                  # 程序入口，Live2D 窗口与线程编排
├── pyproject.toml           # 项目元数据与依赖声明
├── README.md                # 项目文档
├── src/
│   ├── controler.py         # 控制器（待实现）
│   ├── screen_worker.py     # 屏幕变化检测 Worker
│   ├── transcribe_worker.py # ASR 语音识别 Worker
│   └── vad_worker.py        # VAD 语音活动检测 Worker
└── resources/
    ├── 狐狸学姐/             # Live2D 模型：狐狸学姐
    │   ├── 狐狸学姐.model3.json
    │   ├── 狐狸学姐.moc3
    │   ├── 狐狸学姐.physics3.json
    │   ├── *.exp3.json       # 表情文件
    │   └── 狐狸学姐.4096/    # 纹理资源目录
    └── girlfriend/           # Live2D 模型：girlfriend
        ├── girlfriend.model3.json
        └── ...
```

---

## 架构设计

程序基于 **PySide6 (Qt6)** 的多线程模型，使用 `QThread` + `moveToThread` 将耗时任务分离到独立线程中，通过 Qt 信号/槽机制进行线程间通信。

```
┌──────────────────────────────────────────────────────┐
│                    主线程 (GUI)                        │
│  Live2DWidget (QOpenGLWidget)                        │
│  - 模型渲染 (60fps)                                   │
│  - 鼠标交互 / 右键菜单                                 │
│  - 接收 Worker 信号                                   │
└────────┬──────────────┬──────────────┬───────────────┘
         │              │              │
    信号/槽          信号/槽        信号/槽
         │              │              │
┌────────▼────┐  ┌──────▼──────┐  ┌───▼──────────────┐
│ScreenChange │  │ VAD Worker  │  │ Transcribe Worker│
│  Detector   │  │(FullSentence│  │  (GLM-ASR-Nano)  │
│  (屏幕检测)  │  │  Worker)    │  │   (语音识别)      │
│             │  │  (语音检测)  │──▶│                  │
└─────────────┘  └─────────────┘  └──────────────────┘
                  sentence_ready ──▶ on_sentence_audio
```

### 数据流

1. **屏幕检测流**：`ScreenChangeDetector` 以 60fps 截屏 → 灰度化 + 缩放 + 高斯模糊 → 帧差异对比 → 超过阈值时发射 `significant_change_detected` 信号
2. **语音处理流**：`FullSentenceWorker` 监听麦克风 → Silero VAD 逐帧检测 → 语音起止分割 → 发射 `sentence_ready` 信号 → `TranscribeWorker` 接收音频 → GLM-ASR 推理 → 发射 `transcription_ready` 信号

---

## 模块说明

### `main.py` — 程序入口

- 解析命令行参数
- 初始化 Live2D 引擎和 OpenGL 上下文
- 创建 `Live2DWidget` 窗口和各 Worker 线程
- 管理应用生命周期

### `src/screen_worker.py` — 屏幕变化检测

**类**：`ScreenChangeDetector(QObject)`

| 属性                             | 默认值       | 说明                     |
| -------------------------------- | ------------ | ------------------------ |
| `check_interval`                 | `1/60`       | 检测频率（秒）           |
| `resize_width` / `resize_height` | `1280 × 720` | 截图压缩分辨率           |
| `threshold`                      | `50`         | 触发阈值（平均像素差异） |

**信号**：

- `significant_change_detected(float, np.ndarray)` — 检测到显著变化时发射，携带分数和原始截图

**工作流程**：截屏 → BGRA 转灰度 → 缩放 → 高斯模糊去噪 → `cv2.absdiff` 计算帧差 → 均值超过阈值则触发

### `src/vad_worker.py` — 语音活动检测

**类**：`FullSentenceWorker(QObject)`

使用 **Silero VAD** 模型对麦克风输入进行实时语音活动检测，自动将连续语音分割为完整语句。

| 参数                      | 值      | 说明                       |
| ------------------------- | ------- | -------------------------- |
| `sample_rate`             | `16000` | 采样率                     |
| `frame_size`              | `512`   | 每帧采样点数               |
| `min_silence_duration_ms` | `300`   | 停顿超过此时长视为语句结束 |
| `threshold`               | `0.5`   | VAD 置信度阈值             |

**信号**：

- `sentence_ready(np.ndarray)` — 完整语句音频（int16），供 ASR 消费

### `src/transcribe_worker.py` — 语音识别

**类**：`TranscribeWorker(QObject)`

使用 **GLM-ASR-Nano** (`zai-org/GLM-ASR-Nano-2512`) 将音频转录为文字。支持 CUDA 加速，自动选择可用设备。

**信号**：

- `transcription_ready(str)` — 识别出的文本

---

## 模型资源

项目内置两套 Live2D 模型，放置于 `resources/` 目录下：

| 模型       | 目录                    | 表情数量 |
| ---------- | ----------------------- | -------- |
| 狐狸学姐   | `resources/狐狸学姐/`   | 19 个    |
| girlfriend | `resources/girlfriend/` | 17 个    |

每个模型目录包含：

- `.model3.json` — 模型描述文件（入口）
- `.moc3` — 模型数据
- `.physics3.json` — 物理效果配置
- `.cdi3.json` — 显示信息
- `.exp3.json` — 表情文件
- `.4096/` — 纹理资源目录

---

## 许可证

待定
