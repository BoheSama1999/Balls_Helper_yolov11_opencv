import win32gui
import cv2
import time
import numpy as np
from ctypes import windll, c_int, byref, Structure, POINTER, c_ubyte
import ctypes

#dxgi = ctypes.CDLL("G:\\Projects\\Python\\Balls_Helper_yolov11_opencv\\dxgi\\x64\\dxgi4py.dll")
dxgi = ctypes.CDLL("..\\dxgi\\x64\\dxgi4py.dll")
dxgi.grab.argtypes = (POINTER(c_ubyte), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int)
dxgi.grab.restype = POINTER(c_ubyte)
dxgi.init_dxgi.argtypes = (ctypes.c_void_p,)
dxgi.destroy.argtypes = ()

# 启用DPI感知
windll.user32.SetProcessDPIAware()
windll.shcore.SetProcessDpiAwareness(c_int(2))

class RECT(Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]

class POINT(Structure):
    _fields_ = [("x", ctypes.c_long),
                ("y", ctypes.c_long)]

def is_window_minimized(hwnd):
    return windll.user32.IsIconic(hwnd)

def video_stream_generator(upper_hwnd, target_hwnd, fps=30):
    dxgi.init_dxgi(target_hwnd)
    
    shot = None
    shot_pointer = None
    last_client_size = (0, 0)

    frame_interval = 1.0 / fps
    last_capture_time = 0
    last_valid_frame = None

    try:
        while True:
            current_time = time.time()
            
            if is_window_minimized(upper_hwnd) or is_window_minimized(target_hwnd):
                composite = last_valid_frame if last_valid_frame is not None else np.zeros((100, 100, 3), dtype=np.uint8)
                yield composite
                time.sleep(1.0/fps)
                continue

            try:
                if current_time - last_capture_time < frame_interval:
                    time.sleep(0.001)
                    continue
                last_capture_time = current_time

                client_rect = RECT()
                windll.user32.GetClientRect(target_hwnd, byref(client_rect))
                client_width = client_rect.right - client_rect.left
                client_height = client_rect.bottom - client_rect.top

                if last_client_size != (client_width, client_height) or shot is None:
                    shot = np.ndarray((client_height, client_width, 4), dtype=np.uint8)
                    shot_pointer = shot.ctypes.data_as(POINTER(c_ubyte))
                    last_client_size = (client_width, client_height)

                dxgi.grab(shot_pointer, 0, 0, client_width, client_height)

                target_bgr = cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)

                upper_client_rect = RECT()
                windll.user32.GetClientRect(upper_hwnd, byref(upper_client_rect))
                upper_origin = POINT()
                windll.user32.ClientToScreen(upper_hwnd, byref(upper_origin))

                client_origin = POINT()
                windll.user32.ClientToScreen(target_hwnd, byref(client_origin))

                composite = np.zeros((upper_client_rect.bottom, upper_client_rect.right, 3), dtype=np.uint8)

                x_offset = client_origin.x - upper_origin.x
                y_offset = client_origin.y - upper_origin.y
                x_start = max(0, x_offset)
                y_start = max(0, y_offset)
                x_end = min(upper_client_rect.right, x_offset + client_width)
                y_end = min(upper_client_rect.bottom, y_offset + client_height)

                src_x = max(0, -x_offset)
                src_y = max(0, -y_offset)
                copy_width = x_end - x_start
                copy_height = y_end - y_start

                if copy_width > 0 and copy_height > 0:
                    composite[y_start:y_end, x_start:x_end] = \
                        target_bgr[src_y:src_y+copy_height, src_x:src_x+copy_width]

                last_valid_frame = composite.copy()
                yield composite

            except Exception as e:
                print(f"捕获异常：{str(e)}")
                yield last_valid_frame if last_valid_frame is not None else np.zeros((100, 100, 3), dtype=np.uint8)

            # 维持帧率
            elapsed = time.time() - current_time
            if elapsed < 1.0/fps:
                time.sleep(1.0/fps - elapsed)
                
    finally:
        dxgi.destroy()


def display_video_stream(stream_generator, window_name="Video Stream"):
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    try:
        for frame in stream_generator:
            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) == 27:
                break
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    upper_hwnd = win32gui.FindWindow(None, "管理员: Windows PowerShell")
    target_hwnd = win32gui.FindWindow(None, "媒体播放器")

    stream_gen = video_stream_generator(upper_hwnd, target_hwnd, fps=75)
    display_video_stream(stream_gen)
