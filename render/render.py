import math

class GeometryRenderer:
    @staticmethod
    def calculate_circle(bbox):
        """从边界框计算圆形参数"""
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        radius = int(math.hypot(x2-x1, y2-y1)) // 2
        return (center_x, center_y), radius

    @staticmethod
    def validate_circle(detections):
        """验证并修正圆形参数"""
        valid_detections = []
        for det in detections:
            # 确保半径不超过边界框范围
            w = det["bbox"][2] - det["bbox"][0]
            h = det["bbox"][3] - det["bbox"][1]
            max_radius = min(w, h) // 2
            det["radius"] = min(det["radius"], max_radius)
            valid_detections.append(det)
        return valid_detections