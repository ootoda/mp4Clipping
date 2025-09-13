#!/usr/bin/env python3
"""
MP4 クリッピング GUI (PyQt5 + moviepy)

使い方:
 1) 必要ライブラリをインストール:
      pip install pyqt5 moviepy
   ※ moviepy は ffmpeg を内部で利用します。別途 ffmpeg がインストールされている必要があります。

 2) 実行:
      python mp4_trimmer_gui_moviepy.py

 3) ウィンドウに mp4 をドラッグ＆ドロップ
 4) 動画が表示されるのでマウスで矩形を選択
 5) 「Crop & Save」で保存
"""

import sys, os, math
from PyQt5 import QtCore, QtGui, QtWidgets
from moviepy.editor import VideoFileClip


class VideoWidget(QtWidgets.QLabel):
    fileDropped = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumSize(640, 360)

        # 選択矩形
        self.dragging = False
        self.start_pos = None
        self.end_pos = None

        self.pixmap_img = None  # 表示している QPixmap

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isfile(path):
                self.fileDropped.emit(path)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.start_pos = event.pos()
            self.end_pos = self.start_pos
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.dragging:
            self.end_pos = event.pos()
            self.dragging = False
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.start_pos and self.end_pos:
            painter = QtGui.QPainter(self)
            pen = QtGui.QPen(QtGui.QColor(0, 255, 0, 200))
            pen.setWidth(2)
            painter.setPen(pen)
            brush = QtGui.QBrush(QtGui.QColor(0, 255, 0, 50))
            painter.setBrush(brush)
            r = QtCore.QRect(self.start_pos, self.end_pos)
            painter.drawRect(r.normalized())

    def get_selection_normalized(self):
        if not (self.start_pos and self.end_pos):
            return None
        r = QtCore.QRect(self.start_pos, self.end_pos).normalized()
        r = r.intersected(self.contentsRect())
        if r.width() == 0 or r.height() == 0:
            return None
        return (r.x(), r.y(), r.width(), r.height())


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MP4 Clipping (moviepy版)")

        self.video_path = None
        self.clip = None
        self.current_frame = None
        self.orig_w = 0
        self.orig_h = 0

        self.video_widget = VideoWidget()
        self.video_widget.fileDropped.connect(self.load_video)

        self.crop_btn = QtWidgets.QPushButton("Crop & Save")
        self.crop_btn.clicked.connect(self.crop_and_save)
        self.crop_btn.setEnabled(False)

        self.info_label = QtWidgets.QLabel("Drop an MP4 file onto the area above")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.video_widget, stretch=1)
        layout.addWidget(self.crop_btn)
        layout.addWidget(self.info_label)

    def load_video(self, path):
        try:
            self.clip = VideoFileClip(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to open video:\n{e}")
            return

        self.video_path = path
        self.orig_w, self.orig_h = self.clip.size

        # 最初のフレームを取得
        self.current_frame = self.clip.get_frame(0)  # numpy配列 (H,W,3) RGB

        self.show_frame(self.current_frame)

        self.info_label.setText(
            f"Loaded: {os.path.basename(path)} ({self.orig_w}x{self.orig_h}) FPS:{self.clip.fps} Duration:{self.clip.duration:.2f}s"
        )
        self.crop_btn.setEnabled(True)

    def show_frame(self, frame_rgb):
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QtGui.QImage(
            frame_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888
        )
        scaled = qimg.scaled(
            self.video_widget.width(),
            self.video_widget.height(),
            QtCore.Qt.KeepAspectRatio,
        )
        pix = QtGui.QPixmap.fromImage(scaled)
        self.video_widget.setPixmap(pix)
        self.video_widget.pixmap_img = pix

    def crop_and_save(self):
        sel = self.video_widget.get_selection_normalized()
        if not sel:
            QtWidgets.QMessageBox.warning(
                self, "No selection", "Please draw a rectangle on the video."
            )
            return

        disp_x, disp_y, disp_w, disp_h = sel
        pixmap = self.video_widget.pixmap_img
        if pixmap is None:
            return
        disp_w_pix = pixmap.width()
        disp_h_pix = pixmap.height()

        label_w = self.video_widget.width()
        label_h = self.video_widget.height()
        offset_x = max(0, (label_w - disp_w_pix) // 2)
        offset_y = max(0, (label_h - disp_h_pix) // 2)

        sel_x_in_pix = disp_x - offset_x
        sel_y_in_pix = disp_y - offset_y
        sel_w_in_pix = min(disp_w, disp_w_pix - sel_x_in_pix)
        sel_h_in_pix = min(disp_h, disp_h_pix - sel_y_in_pix)

        if sel_w_in_pix <= 0 or sel_h_in_pix <= 0:
            QtWidgets.QMessageBox.warning(self, "Invalid", "Selection outside video.")
            return

        scale_x = self.orig_w / disp_w_pix
        scale_y = self.orig_h / disp_h_pix
        x0 = int(round(sel_x_in_pix * scale_x))
        y0 = int(round(sel_y_in_pix * scale_y))
        x2 = int(round((sel_x_in_pix + sel_w_in_pix) * scale_x))
        y2 = int(round((sel_y_in_pix + sel_h_in_pix) * scale_y))

        out_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save cropped video",
            os.path.splitext(self.video_path)[0] + "_cropped.mp4",
            "MP4 files (*.mp4)",
        )
        if not out_path:
            return

        self.info_label.setText("Cropping... please wait")
        QtWidgets.QApplication.processEvents()

        try:
            cropped = self.clip.crop(x1=x0, y1=y0, x2=x2, y2=y2)
            cropped.write_videofile(out_path, codec="libx264")
            self.info_label.setText(f"Saved: {out_path}")
            QtWidgets.QMessageBox.information(
                self, "Done", f"Cropped video saved:\n{out_path}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to crop:\n{e}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.resize(1000, 600)
    w.show()
    sys.exit(app.exec_())
