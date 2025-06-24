import tkinter as tk
import threading
import queue
import win32gui
import time
from PIL import Image, ImageTk, ImageDraw, ImageFont

class BallOverlay:
    def __init__(self, target_window_title, model_path):
        # 初始化主窗口
        self.root = tk.Tk()
        self.root.geometry("1280x960")
        self.root.config(bg='#ffffff')
        self.root.wm_attributes('-transparentcolor', '#ffffff')
        self.root.attributes('-topmost', True)
        
        # 创建画布
        self.canvas = tk.Canvas(self.root, bg='#ffffff', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 初始化字体
        try:
            self.font = ImageFont.truetype("arial.ttf", 12)
        except:
            self.font = ImageFont.load_default()
            self.font.size = 12
        
        # 窗口句柄管理
        self.target_hwnd = win32gui.FindWindow(None, target_window_title)
        self.upper_hwnd = self.root.winfo_id()
        
        # 多线程通信
        self.detection_queue = queue.Queue(maxsize=3)
        self.stop_event = threading.Event()
        self.last_detections = []
        self.tk_img_cache = None  # 图像缓存
        
        # 颜色配置
        self.colors = {
            "Ball": "#00FF00",
            "Hole": "#FF00FF"
        }
        
        # 初始化检测系统
        from utils.yolo import YoloDetector
        from utils import stream
        self.detector = YoloDetector(model_path)
        self.stream_gen = stream.video_stream_generator(
            self.upper_hwnd, 
            self.target_hwnd,
            fps=30
        )
        
        # 启动工作线程
        self.worker_thread = threading.Thread(target=self.frame_processing_worker, daemon=True)
        self.worker_thread.start()
        
        # 启动界面更新
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_overlay()
        self.root.mainloop()

    def frame_processing_worker(self):
        """后台帧处理线程"""
        try:
            while not self.stop_event.is_set():
                frame = next(self.stream_gen)
                results = self.detector.detect(frame)
                processed = self.process_detections(results)
                
                try:
                    self.detection_queue.put_nowait(processed)
                except queue.Full:
                    pass
                time.sleep(0.02)
        except Exception as e:
            print(f"Worker error: {str(e)}")

    def process_detections(self, results):
        """处理检测结果"""
        detections = []
        if results:
            for box in results:
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                cls_id = int(box.cls[0])
                
                width = x2 - x1
                height = y2 - y1
                radius = int(min(width, height) // 2 * 0.9)
                center = (x1 + width//2, y1 + height//2)
                
                detections.append({
                    "type": "Ball" if cls_id == 0 else "Hole",
                    "bbox": (x1, y1, x2, y2),
                    "center": center,
                    "radius": radius
                })
        return detections

    def update_overlay(self):
        """更新覆盖层"""
        try:
            # 获取最新检测结果
            while not self.detection_queue.empty():
                self.last_detections = self.detection_queue.get_nowait()
            
            # 执行绘制
            if self.last_detections:
                self.draw_annotations()
            
            self.root.after(10, self.update_overlay)
        except Exception as e:
            print(f"Update error: {str(e)}")

    def draw_annotations(self):
        """执行绘制操作"""
        # 创建透明图像
        img = Image.new("RGBA", (self.root.winfo_width(), self.root.winfo_height()), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # 绘制所有检测目标
        for idx, det in enumerate(self.last_detections):
            color = self.colors[det["type"]]
            
            # 绘制边界框
            draw.rectangle(det["bbox"], outline=color, width=1)
            
            # 绘制圆形
            x, y = det["center"]
            r = det["radius"]
            draw.ellipse([x-r, y-r, x+r, y+r], outline=color, width=1)
            
            # 绘制圆心
            draw.ellipse([x-1, y-1, x+1, y+1], fill="white")
            
            # 绘制编号（带黑色描边）
            text = str(idx+1)
            text_x = det["bbox"][0] + 5
            text_y = det["bbox"][1] + 5
            
            # 描边
            for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                draw.text((text_x+dx, text_y+dy), text, fill="black", font=self.font)
            # 主体文字
            draw.text((text_x, text_y), text, fill="white", font=self.font)
        
        # 更新画布
        self.tk_img_cache = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, image=self.tk_img_cache, anchor="nw")

    def on_close(self):
        """关闭处理"""
        self.stop_event.set()
        self.root.destroy()

if __name__ == "__main__":
    BallOverlay(
        target_window_title="abc.png",
        model_path="models/best.pt"
    )
