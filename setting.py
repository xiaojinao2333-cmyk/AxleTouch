from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                             QGroupBox, QLineEdit,
                             QComboBox, QSpinBox, QFormLayout)

from config_manager import load_config, save_config


STYLE = """
    QGroupBox {
        border: 1px solid #ebedf1;
        border-radius: 8px; margin-top: 12px;
        padding: 16px 12px 12px 12px;
        font-size: 12px; color: #787d88;
    }
    QGroupBox::title {
        subcontrol-origin: margin; left: 16px; padding: 0 6px;
    }
    QLabel { color: #1e2026; }
"""

COMBO_STYLE = """
    QComboBox {
        border: 1px solid #ebedf1;
        border-radius: 6px; padding: 4px 8px;
        background: white; color: #1e2026; font-size: 12px;
    }
    QComboBox::drop-down { border: none; }
"""

INPUT_STYLE = """
    QLineEdit {
        border: 1px solid #ebedf1;
        border-radius: 6px; padding: 4px 8px;
        background: white; color: #1e2026; font-size: 12px;
    }
    QLineEdit:focus { border-color: #5078f0; }
"""

SPIN_STYLE = """
    QSpinBox {
        border: 1px solid #ebedf1;
        border-radius: 6px; padding: 4px 8px;
        background: white; color: #1e2026; font-size: 12px;
        min-width: 60px;
    }
"""

# 厂商列表（id, 显示名）
PROVIDER_OPTIONS = [
    ("stepfun", "阶跃星辰"),
    ("bailian", "阿里百炼"),
    ("deepseek", "DeepSeek"),
]

class SettingPage(QWidget):
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        # 嵌入对话框时使用透明背景，避免遮挡卡片圆角与阴影
        if config is not None:
            self._config = {**load_config(), **config}
        else:
            self._config = load_config()
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'refresh'):
            self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)

        layout.setContentsMargins(24, 12, 24, 16)
        layout.setSpacing(12)


        title = QLabel("关于与设置")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #1e2026;")
        layout.addWidget(title)

        # 关于组
        about_box = QGroupBox("关于 AxleTouch")
        about_box.setStyleSheet(STYLE)
        about_layout = QVBoxLayout(about_box)
        about_layout.addWidget(QLabel("版本：1.6.0"))
        about_layout.addWidget(QLabel("作者：Axlewire"))
        about_layout.addWidget(QLabel("许可证：GPL v3"))
        about_layout.addWidget(QLabel(" "))
        about_layout.addWidget(QLabel("仓库主页：https://github.com/baizhou830/AxleTouch"))
        about_layout.addWidget(QLabel("反馈建议：直接提Issue"))
        layout.addWidget(about_box)


        # 设置组
        settings_box = QGroupBox("设置项")
        settings_box.setStyleSheet(STYLE)
        settings_layout = QVBoxLayout(settings_box)
        settings_layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(8)

        self._provider_combo = QComboBox(self)
        self._provider_combo.setStyleSheet(COMBO_STYLE)
        for pid, pname in PROVIDER_OPTIONS:
            self._provider_combo.addItem(pname, pid)
        idx = self._provider_combo.findData(self._config.get("provider", "stepfun"))
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        form.addRow(self._label("模型厂商:"), self._provider_combo)

        self._api_key_edit = QLineEdit(self._config.get("api_key", ""))
        self._api_key_edit.setStyleSheet(INPUT_STYLE)
        self._api_key_edit.setPlaceholderText("输入 API Key")
        form.addRow(self._label("API Key:"), self._api_key_edit)

        self._tavily_key_edit = QLineEdit(self._config.get("tavily_api_key", ""))
        self._tavily_key_edit.setStyleSheet(INPUT_STYLE)
        self._tavily_key_edit.setPlaceholderText("输入 Tavily API Key（可留空）")
        form.addRow(self._label("Tavily Key:"), self._tavily_key_edit)

        self._tts_key_edit = QLineEdit(self._config.get("tts_api_key", ""))
        self._tts_key_edit.setStyleSheet(INPUT_STYLE)
        self._tts_key_edit.setPlaceholderText("输入 StepFun TTS API Key（可留空）")
        form.addRow(self._label("TTS Key:"), self._tts_key_edit)

        self._icon_size_spin = QSpinBox(self)
        self._icon_size_spin.setStyleSheet(SPIN_STYLE)
        self._icon_size_spin.setRange(50, 300)
        self._icon_size_spin.setValue(self._config.get("icon_size", 100))
        self._icon_size_spin.setSuffix(" px")
        form.addRow(self._label("图标大小:"), self._icon_size_spin)

        self._popup_width_spin = QSpinBox(self)
        self._popup_width_spin.setStyleSheet(SPIN_STYLE)
        self._popup_width_spin.setRange(200, 800)
        self._popup_width_spin.setValue(self._config.get("popup_width", 420))
        self._popup_width_spin.setSuffix(" px")
        form.addRow(self._label("输入框宽度:"), self._popup_width_spin)

        self._prompt_edit = QLineEdit(self._config.get("prompt", ""))
        self._prompt_edit.setStyleSheet(INPUT_STYLE)
        self._prompt_edit.setPlaceholderText("自定义prompt")
        form.addRow(self._label("prompt："), self._prompt_edit)

        self._tone_edit = QLineEdit(self._config.get("tts_tone", ""))
        self._tone_edit.setStyleSheet(INPUT_STYLE)
        self._tone_edit.setPlaceholderText("自定义音色")
        form.addRow(self._label("tone: "), self._tone_edit)

        settings_layout.addLayout(form)

        settings_layout.addStretch()

        layout.addWidget(settings_box)
        layout.addStretch()

    def _on_provider_changed(self, idx):
        pname = self._provider_combo.currentText()
        self._api_key_edit.setPlaceholderText(f"输入 {pname} API Key")

    def save_config_values(self):
        self._config["provider"] = self._provider_combo.currentData()
        self._config["api_key"] = self._api_key_edit.text().strip()
        self._config["tavily_api_key"] = self._tavily_key_edit.text().strip()
        self._config["tts_api_key"] = self._tts_key_edit.text().strip()
        self._config["icon_size"] = self._icon_size_spin.value()
        self._config["popup_width"] = self._popup_width_spin.value()
        self._config["prompt"] = self._prompt_edit.text().strip()
        self._config["tts_tone"] = self._tone_edit.text().strip()
        save_config(self._config)
        return self._config

    def reload_config_values(self):
        self._config = load_config()
        idx = self._provider_combo.findData(self._config.get("provider", "stepfun"))
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)
        self._api_key_edit.setText(self._config.get("api_key", ""))
        self._tavily_key_edit.setText(self._config.get("tavily_api_key", ""))
        self._tts_key_edit.setText(self._config.get("tts_api_key", ""))
        self._icon_size_spin.setValue(self._config.get("icon_size", 100))
        self._popup_width_spin.setValue(self._config.get("popup_width", 420))
        self._prompt_edit.setText(self._config.get("prompt", ""))
        self._tone_edit.setText(self._config.get("tts_tone", ""))


    #样式
    @staticmethod
    def _label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet(STYLE)
        return lbl