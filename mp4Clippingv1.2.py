#!/usr/bin/env python3
"""
MP4 クリッピング GUI (PyQt5 + OpenCV) - 修正版

使い方:
 1) 必要ライブラリをインストール:
      pip install pyqt5 opencv-python

 2) 実行:
      python mp4_trimmer_gui_opencv.py

 3) ウィンドウに mp4 をドラッグ＆ドロップ
 4) 動画が表示されるのでマウスで矩形を選択
 5) 「Crop & Save」で保存

注意: 動画範囲外でも選択開始可能ですが、クリッピングは動画範囲内のみ適用されます
"""

import sys, os
from PyQt5 import QtCore, QtGui, QtWidgets
import cv2
import numpy as np


class VideoWidget(QtWidgets.QLabel):
    fileDropped = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(640, 360)
        self.setStyleSheet("background-color: #f0f0f0; border: 2px dashed #ccc;")

        # 選択矩形（ウィジェット座標系）
        self.dragging = False
        self.start_pos = None
        self.end_pos = None

        # 動画情報
        self.original_pixmap = None  # オリジナルサイズのpixmap
        self.displayed_pixmap = None  # 表示用にスケールされたpixmap
        self.video_display_rect = None  # 動画が表示されている矩形範囲

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isfile(path):
                self.fileDropped.emit(path)

    def set_video_frame(self, frame_pixmap):
        """動画フレームを設定"""
        self.original_pixmap = frame_pixmap
        self.update_display()

    def update_display(self):
        """表示を更新（リサイズ対応）"""
        if self.original_pixmap is None:
            return

        # ウィジェットサイズに合わせてスケール
        widget_size = self.size()
        scaled_pixmap = self.original_pixmap.scaled(
            widget_size.width() - 20,  # マージン
            widget_size.height() - 20,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )

        self.displayed_pixmap = scaled_pixmap
        self.setPixmap(scaled_pixmap)

        # 動画表示範囲を計算
        widget_w = widget_size.width()
        widget_h = widget_size.height()
        pixmap_w = scaled_pixmap.width()
        pixmap_h = scaled_pixmap.height()
        
        # 中央配置での位置計算
        offset_x = max(0, (widget_w - pixmap_w) // 2)
        offset_y = max(0, (widget_h - pixmap_h) // 2)
        
        self.video_display_rect = QtCore.QRect(offset_x, offset_y, pixmap_w, pixmap_h)

    def resizeEvent(self, event):
        """ウィンドウリサイズ時の処理"""
        super().resizeEvent(event)
        if self.original_pixmap:
            self.update_display()

    def get_video_display_rect(self):
        """動画表示矩形を取得"""
        return self.video_display_rect

    def mousePressEvent(self, event):
        """マウスクリック開始（どこでも選択開始可能）"""
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.start_pos = event.pos()
            self.end_pos = self.start_pos
            self.update()

    def mouseMoveEvent(self, event):
        """マウスドラッグ中"""
        if self.dragging:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """マウスクリック終了"""
        if event.button() == QtCore.Qt.LeftButton and self.dragging:
            self.end_pos = event.pos()
            self.dragging = False
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # 動画表示範囲を視覚的に示す枠線
        if self.video_display_rect:
            pen = QtGui.QPen(QtGui.QColor(100, 100, 100, 180))
            pen.setWidth(1)
            pen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(self.video_display_rect)
        
        # 選択矩形を描画
        if self.start_pos and self.end_pos:
            selection_rect = QtCore.QRect(self.start_pos, self.end_pos).normalized()
            
            if self.dragging:
                # ドラッグ中: 緑色
                pen = QtGui.QPen(QtGui.QColor(0, 255, 0, 200))
                pen.setWidth(2)
                painter.setPen(pen)
                brush = QtGui.QBrush(QtGui.QColor(0, 255, 0, 30))
                painter.setBrush(brush)
            else:
                # 確定後: 赤色
                pen = QtGui.QPen(QtGui.QColor(255, 0, 0, 200))
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(QtCore.Qt.NoBrush)
            
            painter.drawRect(selection_rect)
            
            # 動画範囲外の部分は異なる色で表示
            if self.video_display_rect:
                video_intersect = selection_rect.intersected(self.video_display_rect)
                if video_intersect != selection_rect:
                    # 範囲外部分を黄色で描画
                    pen_outside = QtGui.QPen(QtGui.QColor(255, 255, 0, 150))
                    pen_outside.setWidth(2)
                    pen_outside.setStyle(QtCore.Qt.DashLine)
                    painter.setPen(pen_outside)
                    painter.setBrush(QtCore.Qt.NoBrush)
                    painter.drawRect(selection_rect)

    def get_selection_info(self):
        """選択範囲の情報を取得"""
        if not (self.start_pos and self.end_pos and self.video_display_rect and self.displayed_pixmap):
            return None
        
        # 選択矩形
        selection_rect = QtCore.QRect(self.start_pos, self.end_pos).normalized()
        
        if selection_rect.width() < 5 or selection_rect.height() < 5:
            return None
        
        # 動画範囲との交差部分を計算
        video_intersect = selection_rect.intersected(self.video_display_rect)
        
        if video_intersect.width() <= 0 or video_intersect.height() <= 0:
            return None  # 動画範囲との交差なし
        
        # 動画範囲内の相対座標に変換
        rel_x = video_intersect.x() - self.video_display_rect.x()
        rel_y = video_intersect.y() - self.video_display_rect.y()
        rel_w = video_intersect.width()
        rel_h = video_intersect.height()
        
        return {
            'selection_rect': selection_rect,
            'video_intersect': video_intersect,
            'relative_pos': (rel_x, rel_y, rel_w, rel_h),
            'display_size': (self.displayed_pixmap.width(), self.displayed_pixmap.height())
        }

    def clear_selection(self):
        """選択をクリア"""
        self.start_pos = None
        self.end_pos = None
        self.update()


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MP4 Clipping Tool - 修正版")
        
        self.video_path = None
        self.cap = None
        self.frame_count = 0
        self.fps = 0
        self.orig_w = 0
        self.orig_h = 0
        self.current_frame = None

        self.setup_ui()

    def setup_ui(self):
        self.video_widget = VideoWidget()
        self.video_widget.fileDropped.connect(self.load_video)

        # ボタンレイアウト
        button_layout = QtWidgets.QHBoxLayout()
        
        self.clear_btn = QtWidgets.QPushButton("Clear Selection")
        self.clear_btn.clicked.connect(self.clear_selection)
        self.clear_btn.setEnabled(False)
        
        self.crop_btn = QtWidgets.QPushButton("Crop & Save")
        self.crop_btn.clicked.connect(self.crop_and_save)
        self.crop_btn.setEnabled(False)
        
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.crop_btn)

        # 情報表示
        self.info_label = QtWidgets.QLabel("Drop an MP4 file onto the area above")
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        
        # 選択情報表示
        self.selection_info_label = QtWidgets.QLabel("")
        self.selection_info_label.setAlignment(QtCore.Qt.AlignCenter)
        self.selection_info_label.setStyleSheet("color: #333; font-size: 12px;")
        
        # 使用方法の説明
        help_text = (
            "使い方:\n"
            "1) MP4ファイルをドラッグ&ドロップ\n"
            "2) マウスでドラッグして矩形選択（動画範囲外でも選択開始可能）\n"
            "3) 動画範囲外の選択は黄色破線、動画範囲内は赤色実線で表示\n"
            "4) クリッピングは動画範囲内の部分のみ適用されます"
        )
        self.help_label = QtWidgets.QLabel(help_text)
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        self.help_label.setAlignment(QtCore.Qt.AlignCenter)

        # メインレイアウト
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.video_widget, stretch=1)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.info_label)
        main_layout.addWidget(self.selection_info_label)
        main_layout.addWidget(self.help_label)

        # タイマーで選択情報を更新
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_selection_info)
        self.update_timer.start(100)  # 100ms間隔

    def update_selection_info(self):
        """選択情報を更新"""
        if not self.video_widget.start_pos or not self.video_widget.end_pos:
            self.selection_info_label.setText("")
            return
        
        sel_info = self.video_widget.get_selection_info()
        if sel_info:
            rel_x, rel_y, rel_w, rel_h = sel_info['relative_pos']
            disp_w, disp_h = sel_info['display_size']
            
            # 元動画サイズでの座標計算
            if disp_w > 0 and disp_h > 0:
                scale_x = self.orig_w / disp_w
                scale_y = self.orig_h / disp_h
                
                orig_x = int(rel_x * scale_x)
                orig_y = int(rel_y * scale_y)
                orig_w = int(rel_w * scale_x)
                orig_h = int(rel_h * scale_y)
                
                self.selection_info_label.setText(
                    f"Selection: {orig_w}x{orig_h} at ({orig_x},{orig_y}) in original {self.orig_w}x{self.orig_h}"
                )
        else:
            self.selection_info_label.setText("Selection outside video area or too small")

    def load_video(self, path):
        try:
            if self.cap:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(path)
            
            if not self.cap.isOpened():
                raise Exception("Failed to open video file")
            
            # 動画情報取得
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.orig_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.orig_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 最初のフレームを表示
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                self.show_frame(frame)
            
            self.video_path = path
            duration = self.frame_count / self.fps if self.fps > 0 else 0
            
            self.info_label.setText(
                f"Loaded: {os.path.basename(path)} ({self.orig_w}x{self.orig_h}) "
                f"FPS:{self.fps:.1f} Duration:{duration:.1f}s"
            )
            
            self.clear_btn.setEnabled(True)
            self.crop_btn.setEnabled(True)
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to open video:\n{e}")
            if self.cap:
                self.cap.release()
                self.cap = None

    def show_frame(self, frame):
        """フレームを表示"""
        # BGR -> RGB変換
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        
        qt_image = QtGui.QImage(rgb_frame.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        original_pixmap = QtGui.QPixmap.fromImage(qt_image)
        
        self.video_widget.set_video_frame(original_pixmap)

    def clear_selection(self):
        """選択をクリア"""
        self.video_widget.clear_selection()

    def crop_and_save(self):
        if not self.cap:
            QtWidgets.QMessageBox.warning(self, "No Video", "No video loaded.")
            return
        
        sel_info = self.video_widget.get_selection_info()
        if not sel_info:
            QtWidgets.QMessageBox.warning(
                self, "No Valid Selection", 
                "Please draw a rectangle that intersects with the video area."
            )
            return

        rel_x, rel_y, rel_w, rel_h = sel_info['relative_pos']
        disp_w, disp_h = sel_info['display_size']

        # 元動画サイズでの座標計算
        scale_x = self.orig_w / disp_w
        scale_y = self.orig_h / disp_h
        
        x0 = max(0, int(rel_x * scale_x))
        y0 = max(0, int(rel_y * scale_y))
        x2 = min(self.orig_w, int((rel_x + rel_w) * scale_x))
        y2 = min(self.orig_h, int((rel_y + rel_h) * scale_y))
        
        crop_w = x2 - x0
        crop_h = y2 - y0

        if crop_w <= 0 or crop_h <= 0:
            QtWidgets.QMessageBox.warning(self, "Invalid Selection", "Invalid crop dimensions.")
            return

        # 保存先選択
        out_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save cropped video",
            os.path.splitext(self.video_path)[0] + "_cropped.mp4",
            "MP4 files (*.mp4)",
        )
        if not out_path:
            return

        # クロップ処理
        self.process_crop(out_path, x0, y0, crop_w, crop_h)

    def process_crop(self, output_path, x, y, width, height):
        """動画をクロップして保存"""
        try:
            self.info_label.setText(f"Cropping to {width}x{height} at ({x},{y})...")
            QtWidgets.QApplication.processEvents()
            
            input_cap = cv2.VideoCapture(self.video_path)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_writer = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))
            
            frame_idx = 0
            
            while True:
                ret, frame = input_cap.read()
                if not ret:
                    break
                
                # フレームをクロップ
                cropped_frame = frame[y:y+height, x:x+width]
                out_writer.write(cropped_frame)
                
                # 進捗表示
                frame_idx += 1
                if frame_idx % 30 == 0:
                    progress = (frame_idx / self.frame_count) * 100
                    self.info_label.setText(f"Processing... {progress:.1f}%")
                    QtWidgets.QApplication.processEvents()
            
            input_cap.release()
            out_writer.release()
            
            self.info_label.setText(f"Saved: {os.path.basename(output_path)}")
            QtWidgets.QMessageBox.information(
                self, "Complete", 
                f"Cropped video saved!\nFile: {os.path.basename(output_path)}\nSize: {width}x{height}"
            )
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to crop video:\n{e}")
            self.info_label.setText("Error occurred during cropping")

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.resize(1000, 700)
    w.show()
    sys.exit(app.exec_())