"""仅加载并显示 Live2D 模型的精简查看器。"""

import argparse
import json
import os
import traceback

import live2d.v3 as live2d
from OpenGL.GL import glViewport
from PySide6.QtCore import QPoint, Qt, QTimerEvent
from PySide6.QtGui import QMouseEvent, QSurfaceFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication, QMenu


class Live2DWidget(QOpenGLWidget):
    def __init__(self, model_path, init_expressions=None):
        super().__init__()
        self.model_path = model_path
        self.model: live2d.LAppModel | None = None
        self.init_expressions = init_expressions or []

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.resize(1280, 720)

        self._dragging = False
        self._drag_offset = QPoint()

    # ── OpenGL ──

    def initializeGL(self):
        try:
            live2d.glInit()
            self.model = live2d.LAppModel()
            self.model.LoadModelJson(self.model_path)
            self.model.SetAutoBlinkEnable(True)
            self.model.SetAutoBreathEnable(True)
            self.model.Resize(self.width(), self.height())
            self._apply_initial_expressions()
            self._print_model_info()
            self.startTimer(int(1000 / 60))
        except Exception:
            traceback.print_exc()

    def resizeGL(self, w: int, h: int) -> None:
        glViewport(0, 0, w, h)
        if self.model:
            self.model.Resize(w, h)

    def paintGL(self):
        try:
            live2d.clearBuffer(0.0, 0.0, 0.0, 0.0)
            if self.model:
                self.model.Update()
                self.model.Draw()
        except Exception:
            traceback.print_exc()

    def timerEvent(self, a0: QTimerEvent | None) -> None:
        self.update()

    # ── 鼠标拖拽 ──

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        else:
            if self.model:
                x = event.globalPosition().x() - self.x()
                y = event.globalPosition().y() - self.y()
                cx, cy = self.width() / 2, self.height() / 2
                x = cx + (x - cx) * 0.3
                y = cy + (y - cy) * 0.3
                self.model.Drag(x, y)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
        super().mouseReleaseEvent(event)

    # ── 右键菜单 ──

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        quit_action = menu.addAction("退出")
        if menu.exec(event.globalPos()) == quit_action:
            QApplication.quit()

    # ── 表情 ──

    def _print_model_info(self):
        """打印模型的所有可用表情和动作组。"""
        if not self.model:
            return
        # 表情列表
        expression_ids = self.model.GetExpressionIds()
        print(f"\n[模型] 可用表情 ({len(expression_ids)} 个):")
        for eid in expression_ids:
            print(f"  - {eid}")
        # 动作组
        motion_groups = self.model.GetMotionGroups()
        print(f"\n[模型] 可用动作组 ({len(motion_groups)} 个):")
        for group_name, count in motion_groups.items():
            print(f"  - {group_name}: {count} 个动作")
        print()

    def _apply_initial_expressions(self):
        if not self.model:
            return
        model_dir = os.path.dirname(self.model_path)
        for exp_name in self.init_expressions:
            exp_path = os.path.join(model_dir, exp_name)
            if not os.path.exists(exp_path):
                continue
            try:
                with open(exp_path, "r", encoding="utf-8") as f:
                    exp_data = json.load(f)
                for param in exp_data.get("Parameters", []):
                    pid = param["Id"]
                    value = float(param["Value"])
                    blend = param.get("Blend", "Add")
                    if blend == "Add":
                        self.model.AddParameterValue(pid, value)
                    else:
                        self.model.SetParameterValue(pid, value)
                print(f"[表情] 已应用: {exp_name}")
            except Exception as e:
                print(f"[表情] 加载失败 {exp_name}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live2D 模型查看器")
    parser.add_argument(
        "--model",
        default="resources/狐狸学姐/狐狸学姐.model3.json",
        help="模型文件路径",
    )
    parser.add_argument(
        "--expressions",
        nargs="*",
        default=["水印关闭.exp3.json"],
        help="启动时自动应用的表情文件列表",
    )
    args, remaining = parser.parse_known_args()

    live2d.init()

    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(remaining)
    widget = Live2DWidget(args.model, init_expressions=args.expressions)
    widget.show()
    app.exec()

    live2d.dispose()
