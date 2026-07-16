from datetime import datetime

import os
import tempfile
import winsound
from pathlib import Path
from config_manager import load_config
import base64

from schedule import Poller
from tts import TTSThread

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLineEdit, QPushButton, QLabel, QApplication,
                              QMenu, QAction, QDialog)
from PyQt5.QtCore import (Qt, QPoint, QRectF, QPropertyAnimation,
                           QEasingCurve, QTimer, pyqtSignal, QElapsedTimer,QBuffer)
from PyQt5.QtGui import (QPainter, QBrush, QColor, QPen, QPainterPath,
                          QRegion, QCursor, QFontMetrics, QPixmap)

from tools import _log_to_json, get_base_path, capture_screen
from setting import SettingPage


current_dir = get_base_path()


image_path = os.path.join(current_dir, "assets", "image.svg")

class ContentBar(QWidget):

    def __init__(self, parent_floating):
        super().__init__()
        self._parent = parent_floating
        self._progress = 0.0
        self._elapsed = QElapsedTimer()
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(30)
        self._progress_timer.timeout.connect(self._tick_progress)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(63)
        self.setFixedWidth(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 16px;
                background: transparent;
            }
        """)
        self._label.setWordWrap(False)
        layout.addWidget(self._label)

    def show_content(self, text):
        self._label.setText(text)
        self._adjust_width(text)
        self._update_position()
        self._progress = 1.0
        self._elapsed.start()
        self._progress_timer.start()
        self._show_animated()
        show_time = min(len(text) + 1, 25)
        show_time = max(show_time, 3)
        QTimer.singleShot(show_time*1000, self._hide_animated)

    def _tick_progress(self):
        elapsed_ms = self._elapsed.elapsed()
        self._progress = max(0.0, 1.0 - elapsed_ms / 5000)
        self.update()
        if self._progress <= 0.0:
            self._progress_timer.stop()

    def _final_pos(self):
        fx = self._parent.x()
        fy = self._parent.y()
        fw = self._parent.width()
        pw = self.width()
        ph = self.height()

        screen = QApplication.primaryScreen().geometry()
        sw = screen.width()

        edge = self._parent._edge_side
        if edge == 'left':
            px = fx
        elif edge == 'right':
            px = fx + fw - pw
        else:
            px = fx + fw // 2 - pw // 2

        if px < 0:
            px = 0
        elif px + pw > sw:
            px = sw - pw

        py = fy - ph - 6
        if py < 0:
            py = fy + self._parent.height() + 6

        return QPoint(px, py)

    def _show_animated(self):
        final = self._final_pos()
        start = QPoint(final.x(), self._parent.y() - self.height())

        self.setWindowOpacity(0.0)
        self.setFixedHeight(63)
        self.move(start)
        self.show()

        anim_p = QPropertyAnimation(self, b"pos")
        anim_p.setDuration(400)
        anim_p.setStartValue(start)
        anim_p.setEndValue(final)
        anim_p.setEasingCurve(QEasingCurve.OutCubic)
        anim_p.start()
        self._show_anim_p = anim_p

        anim_o = QPropertyAnimation(self, b"windowOpacity")
        anim_o.setDuration(300)
        anim_o.setStartValue(0.0)
        anim_o.setEndValue(1.0)
        anim_o.setEasingCurve(QEasingCurve.OutCubic)
        anim_o.start()
        self._show_anim_o = anim_o

    def _hide_animated(self):
        self._progress_timer.stop()
        cur = self.pos()
        target = QPoint(cur.x(), self._parent.y() - self.height())

        anim_p = QPropertyAnimation(self, b"pos")
        anim_p.setDuration(350)
        anim_p.setStartValue(cur)
        anim_p.setEndValue(target)
        anim_p.setEasingCurve(QEasingCurve.InCubic)
        anim_p.start()
        self._hide_anim_p = anim_p

        anim_o = QPropertyAnimation(self, b"windowOpacity")
        anim_o.setDuration(300)
        anim_o.setStartValue(self.windowOpacity())
        anim_o.setEndValue(0.0)
        anim_o.setEasingCurve(QEasingCurve.InCubic)
        anim_o.finished.connect(self._after_hide)
        anim_o.start()
        self._hide_anim_o = anim_o

    def _after_hide(self):
        self.hide()
        self.setWindowOpacity(1.0)
        self._progress = 0.0

    def _adjust_width(self, text):
        fm = QFontMetrics(self._label.font())
        text_w = fm.horizontalAdvance(text)
        w = text_w + 24 * 2 + 20
        w = max(w, 120)
        self.setFixedWidth(w)

    def _update_position(self):
        self.move(self._final_pos())

    def reposition(self):
        if self.isVisible():
            self._update_position()

    def _card_rect(self):
        return QRectF(10, 10, self.width() - 20, self.height() - 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        card = self._card_rect()

        for i in range(4):
            offset = 6 - i * 1.5
            r = card.adjusted(-offset, -offset + 2, offset, offset + 2)
            alpha = 8 + i * 8
            painter.setBrush(QBrush(QColor(60, 65, 80, alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(r, 12 + offset, 12 + offset)

        painter.setBrush(QBrush(QColor(251, 251, 253)))
        painter.setPen(QPen(QColor(230, 232, 236), 0.5))
        painter.drawRoundedRect(card, 12, 12)

        if self._progress > 0.0 and card.height() > 2:
            bar_w = card.width() * self._progress
            bar_x = card.x()
            bar_y = card.bottom() - 2.5
            painter.setBrush(QBrush(QColor(74, 144, 217, 200)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, 2.5), 1, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12, 12)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))



class InputPopup(QWidget):

    submitted = pyqtSignal(str)
    image = pyqtSignal(str)
    not_image = pyqtSignal()
    no_vlm = pyqtSignal()

    def __init__(self, parent_floating):
        super().__init__()
        self._parent = parent_floating
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(self._parent.collapsed_size)
        self.setFixedWidth(420)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._edit = QLineEdit(self)
        self._edit.setPlaceholderText("输入...")
        self._edit.setStyleSheet("""
            QLineEdit {
                background: #fbfbfd;
                border: 1px solid #e0e2e8;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 12px;
                color: #333;
            }
            QLineEdit:focus {
                border: 1.5px solid #4a90d9;
            }
        """)
        self._edit.returnPressed.connect(self._on_submit)
        layout.addWidget(self._edit)

        self._btn = QPushButton("✓", self)
        self._btn.setFixedSize(28, 28)
        self._btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3a7bc8;
            }
            QPushButton:pressed {
                background: #2e6ab5;
            }
        """)
        self._btn.clicked.connect(self._on_submit)
        layout.addWidget(self._btn)

    def _on_submit(self):
        text = self._edit.text().strip()
        if text:
            self.submitted.emit(text)
        self.hide_popup()

    def _calc_position(self):
        fx = self._parent.x()
        fy = self._parent.y()
        fh = self._parent.height()
        fw = self._parent.width()
        pw = self.width()
        ph = self.height()

        screen = QApplication.primaryScreen().geometry()
        sw = screen.width()
        sh = screen.height()

        edge = self._parent._edge_side
        if edge == 'left':
            px = fx
        elif edge == 'right':
            px = fx + fw - pw
        else:
            px = fx + fw // 2 - pw // 2

        if px < 0:
            px = 0
        elif px + pw > sw:
            px = sw - pw

        py = fy + fh + 4
        if py + ph > sh:
            py = fy - ph - 4

        return QPoint(px, py)

    def popup(self):
        pos = self._calc_position()
        self.move(pos)
        self.show()
        self._edit.setFocus()

    def reposition(self):
        if self.isVisible():
            pos = self._calc_position()
            self.move(pos)

    def hide_popup(self):
        self.hide()
        self._edit.clear()

    def apply_config(self, config):
        width = config.get("popup_width", 420)
        self.setFixedWidth(width)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()  

    def dropEvent(self, event):
        config = load_config()
        if config.get("provider") != "stepfun":
            self.no_vlm.emit()
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                with open(file_path, "rb") as image_file:
                    base64_bytes = base64.b64encode(image_file.read()).decode('utf-8')
                    image_data = f"data:image/{Path(file_path).suffix[1:].lower()};base64,{base64_bytes}"
                    self.image.emit(image_data)
            else:
                self.not_image.emit()




class SettingsDialog(QDialog):
    config_saved = pyqtSignal(dict)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config.copy() if config else {}
        self._drag_pos = None
        self.setWindowTitle("AxleTouch")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 650)
        self.init_ui()

    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(0)

        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(52)
        self.top_bar.setStyleSheet("background: transparent;")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(20, 0, 12, 0)

        title = QLabel("AxleTouch")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #1e2026;")
        top_layout.addWidget(title)
        top_layout.addStretch()

        self.ok_btn = QPushButton("Yes")
        self.ok_btn.setFixedSize(56, 32)
        self.ok_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background: #5078f0; color: white; border: none;
                border-radius: 8px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #6090E8; }
        """)
        self.ok_btn.clicked.connect(self._on_save)
        top_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedSize(56, 32)
        self.cancel_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #787d88;
                border: 1px solid #787d88;
                border-radius: 8px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #ebf0ff; }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        top_layout.addWidget(self.cancel_btn)

        outer.addWidget(self.top_bar)


        divider = QWidget()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #ebedf1;")
        outer.addWidget(divider)
        self._about_page = SettingPage(config=self._config)
        outer.addWidget(self._about_page, stretch=1)

    def _on_save(self):
        new_config = self._about_page.save_config_values()
        self._config = new_config
        self.config_saved.emit(new_config)
        self.accept()

    def _on_cancel(self):
        self._about_page.reload_config_values()
        self.reject()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, '_drag_pos') and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _card_rect(self):
        m = 20
        return QRectF(m, m, self.width() - m * 2, self.height() - m * 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        card = self._card_rect()
        radius = 12

        # 阴影
        for i in range(4):
            offset = 6 - i * 1.5
            r = card.adjusted(-offset, -offset + 2, offset, offset + 2)
            alpha = 8 + i * 8
            painter.setBrush(QBrush(QColor(60, 65, 80, alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(r, radius + offset, radius + offset)


        painter.setBrush(QBrush(QColor(251, 251, 253)))
        painter.setPen(QPen(QColor(230, 232, 236), 0.5))
        painter.drawRoundedRect(card, radius, radius)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12, 12)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))



class EdgeFloatingBlock(QWidget):
    def __init__(self):
        super().__init__()
        self.collapsed_size = 100
        self._edge_side = 'right'
        self._animating = False

        self._press_pos = None
        self._drag_offset = None
        self._long_press_fired = False
        self._is_dragging = False
        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._on_long_press)

        self._input_popup = InputPopup(self)
        self._input_popup.submitted.connect(self._on_input_submitted)
        self._input_popup.not_image.connect(self._not_image)
        self._input_popup.image.connect(self._image)
        self._input_popup.no_vlm.connect(self._no_vlm)


        self._content_bar = ContentBar(self)

        pixmap = QPixmap(image_path)
        self.image = pixmap.scaled(720, 720,
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self._ai = None
        self._config = None

        self._poller = Poller(self) 
        self._poller.status_ready.connect(self._on_poller_status)

        self.init_ui()

    def _on_poller_status(self, status_text):
        if self._ai:
            self._ai.send_message(status_text)

    def set_ai_client(self, client, config=None):
        self._ai = client
        self._config = config or {}
        self._ai.response_ready.connect(self._on_ai_response)
        self._apply_size_config()


    def _apply_size_config(self):
        icon_size = self._config.get("icon_size", 100)
        self.collapsed_size = icon_size
        self.resize(icon_size, icon_size)

        pixmap = QPixmap(image_path)
        self.image = pixmap.scaled(int(icon_size * 7.2), int(icon_size * 7.2),
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self._input_popup.apply_config(self._config)

        screen = QApplication.primaryScreen().geometry()
        if self._edge_side == 'left':
            self.move(0, self.y())
        else:
            self.move(screen.width() - icon_size, self.y())


    def _on_ai_response(self, text):
        self._content_bar.show_content(text)
        print("[", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "]", "\n",
              "雨竹：", "\"", text, "\"", "\n")
        _log_to_json(text)

        tts_api_key = self._config.get("tts_api_key", "") if self._config else ""
        if tts_api_key:
            tts_text = text.replace("[web search]", "").strip()
            if tts_text:
                self._tts_thread = TTSThread(tts_api_key, tts_text)
                self._tts_thread.audio_ready.connect(self._on_tts_audio_ready)
                self._tts_thread.error_occurred.connect(self._on_tts_error)
                self._tts_thread.start()

    def _on_tts_audio_ready(self, audio_data):
        temp_path = os.path.join(tempfile.gettempdir(), "axletouch_tts.wav")
        try:
            with open(temp_path, "wb") as f:
                f.write(audio_data)
            winsound.PlaySound(temp_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:
            print("TTS 播放失败:", e)

    def _on_tts_error(self, error_msg):
        print("TTS 错误:", error_msg)

    def _on_input_submitted(self, text):
        print(" -----[ user input ]----- ", "\n",
              "[", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "]", "\n",
              "\"", text, "\"","\n")
        if self._ai:
            self._ai.send_message(text)

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen().geometry()
        default_size = self.collapsed_size
        self.resize(default_size, default_size)
        cy = (screen.height() - default_size) // 2
        self.move(screen.width() - default_size, cy)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

    def moveEvent(self, event):
        super().moveEvent(event)
        self._input_popup.reposition()
        self._content_bar.reposition()

    def _snap_to_edge(self):
        screen = QApplication.primaryScreen().geometry()
        center_x = self.x() + self.width() / 2
        self._edge_side = 'left' if center_x < screen.width() / 2 else 'right'

        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(200)
        anim.setEasingCurve(QEasingCurve.InOutCubic)

        cur_y = self.y()
        if self._edge_side == 'left':
            target = QPoint(0, cur_y)
        else:
            target = QPoint(screen.width() - self.width(), cur_y)

        anim.setStartValue(self.pos())
        anim.setEndValue(target)
        anim.start()

    def _on_long_press(self):
        self._long_press_fired = True
        self._is_dragging = True
        self.setCursor(QCursor(Qt.ClosedHandCursor))

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._press_pos = event.globalPos()
        self._drag_offset = event.globalPos() - self.pos()
        self._long_press_fired = False
        self._is_dragging = False
        self._long_press_timer.start(300)

    def mouseMoveEvent(self, event):
        if not event.buttons() & Qt.LeftButton or self._press_pos is None:
            return
        dist = (event.globalPos() - self._press_pos).manhattanLength()
        if dist > 5 and not self._long_press_fired:
            self._long_press_timer.stop()
            self._long_press_fired = True
            self._is_dragging = True
            self.setCursor(QCursor(Qt.ClosedHandCursor))

        if self._is_dragging:
            self.move(event.globalPos() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._long_press_timer.stop()

        if self._is_dragging:
            self._snap_to_edge()
        else:
            if self._input_popup.isVisible():
                self._input_popup.hide_popup()
            else:
                self._input_popup.popup()

        self._long_press_fired = False
        self._is_dragging = False
        self._press_pos = None
        self.setCursor(QCursor(Qt.ArrowCursor))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #fbfbfd;
                border: 1px solid #e0e2e8;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background: #4a90d9;
                color: white;
            }
        """)

        settings_action = QAction("关于与设置", self)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        capture_action = QAction("让雨竹看看！", self)
        capture_action.triggered.connect(self._capture)
        menu.addAction(capture_action)

        menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.quit)
        menu.addAction(exit_action)

        menu.exec_(event.globalPos())

    def _open_settings(self):
        dialog = SettingsDialog(self._config or {}, self)
        dialog.config_saved.connect(self._on_config_saved)
        dialog.exec_()

    def _capture(self):
        try:
            pixmap = capture_screen()
        except Exception:
            print("截图失败：无法获取屏幕图像")
            return

        if pixmap.isNull():
            print("截图失败：获取的图像无效")
            return
        
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        pixmap = pixmap.scaled(1280, 720, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap.save(buffer, "PNG")
        data = buffer.data().toBase64().data().decode()
        image_url = f"data:image/png;base64,{data}"
        #此处不复用_image其实是有说法的 image发送路径的可自定义性太低。
        print(" -----[ Action ]----- ", "\n",
              "[", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "]", "\n",
              "\"", "雨竹看了一眼你的屏幕", "\"","\n")
        _data = [
            {"type": "text", "text": "这是用户桌面截图。"},
            {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}}
        ]
        if self._ai:
            self._ai.send_message(_data)

    def _on_config_saved(self, config):
        self._config = config
        self._apply_size_config()
        if self._ai:
            self._ai.update(
                config.get("provider", "stepfun"),
                config.get("api_key", ""),
                config.get("tavily_api_key", ""),
            )

    def _card_rect(self):
        return QRectF(15, 15, self.width() - 30, self.height() - 30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        card = self._card_rect()

        for i in range(4):
            offset = 9 - i * 2.25
            r = card.adjusted(-offset, -offset + 3, offset, offset + 3)
            alpha = 8 + i * 8
            painter.setBrush(QBrush(QColor(60, 65, 80, alpha)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(r, 18 + offset, 18 + offset)

        painter.setBrush(QBrush(QColor(251, 251, 253)))
        painter.setPen(QPen(QColor(230, 232, 236), 0.5))
        painter.drawRoundedRect(card, 18, 18)

        painter.setPen(QPen(QColor(100, 105, 115)))
        painter.setFont(painter.font())
        font = painter.font()
        font.setPixelSize(int(card.height() * 0.45))
        painter.setFont(font)

        painter.save()
        clip_path = QPainterPath()
        clip_path.addRoundedRect(card, 18, 18)
        painter.setClipPath(clip_path)
        painter.drawPixmap(card.toRect(), self.image)
        painter.restore()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 18, 18)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _not_image(self):
        self._content_bar.show_content("不是图片文件，拖进来也没用ww")

    def _no_vlm(self):
        self._content_bar.show_content("没有VLM API哦，请使用StepFun API或等待下版本对其他VLM的支持。")

    def _image(self,data):
        print(" -----[ user input ]----- ", "\n",
              "[", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "]", "\n",
              "\"", "图片", "\"",'\n')
        data = [
        {"type": "image_url", "image_url": {"url": data,"detail":"high"}}
    ]
        if self._ai:
            self._ai.send_message(data)