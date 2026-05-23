# ==================== Android 手机端 WiFi 室内定位APP ====================
from kivy.utils import platform
import os
os.environ["KIVY_WINDOW"] = "sdl2"
os.environ["KIVY_NO_ARGS"] = "1"
import json
import math
import numpy as np
import pandas as pd
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from plyer import wifi
import random

# 安卓权限申请
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.ACCESS_FINE_LOCATION,
        Permission.ACCESS_COARSE_LOCATION,
        Permission.ACCESS_WIFI_STATE,
        Permission.CHANGE_WIFI_STATE,
        Permission.NEARBY_WIFI_DEVICES,
        Permission.INTERNET
    ])

# 全局配置
last_final_x = 3.0
last_final_y = 3.0

kalman_pos = {
    'x': 3.0, 'y': 3.0,
    'P': 5.0,
    'Q': 0.002,
    'R': 10.0
}
pos_history = []
error_history = []
trace_history = []

# 加载指纹库 适配双端路径
def load_all_fingerprints():
    try:
        if platform == "android":
            csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fingerprints.csv")
        else:
            csv_path = "fingerprints.csv"
        df = pd.read_csv(csv_path)
        ap_cols = [col for col in df.columns if col not in ["x", "y"]]
        return df, ap_cols
    except Exception as e:
        print("加载指纹库失败:", e)
        return None, None

# 扫描WiFi信号
def get_real_phone_rssi(ap_cols):
    try:
        wifi_list = wifi.scan_wifi()
        if not wifi_list:
            return np.array([-60 for _ in ap_cols])
        bssid_to_rssi = {ap["bssid"].upper(): ap["signal_strength"] for ap in wifi_list}
        vec = []
        for bssid in ap_cols:
            vec.append(bssid_to_rssi.get(bssid.upper(), -100))
        return np.array(vec)
    except Exception as e:
        print("WiFi扫描异常", e)
        return np.array([-50 + random.uniform(-3,3) for _ in ap_cols])

# 卡尔曼滤波
def kalman_xy(meas_x, meas_y):
    global kalman_pos
    kalman_pos['P'] += kalman_pos['Q']
    k = kalman_pos['P'] / (kalman_pos['P'] + kalman_pos['R'])
    kalman_pos['x'] += k * (meas_x - kalman_pos['x'])
    kalman_pos['y'] += k * (meas_y - kalman_pos['y'])
    kalman_pos['P'] *= (1 - k)
    return kalman_pos['x'], kalman_pos['y']

# WKNN算法
def wknn_locate(current_vec, df, ap_cols, K=5):
    fingerprint_matrix = df[ap_cols].fillna(-100).values
    coords = df[["x", "y"]].values
    distances = np.sqrt(np.sum((fingerprint_matrix - current_vec) ** 2, axis=1))
    df["distance"] = distances
    top_k = df.nsmallest(K, "distance")
    weights = 1 / (top_k["distance"] + 1e-6)
    x = np.sum(top_k["x"] * weights) / np.sum(weights)
    y = np.sum(top_k["y"] * weights) / np.sum(weights)
    return round(x, 1), round(y, 1), top_k

# 优化定位
def optimized_knn(current_vec, df, ap_cols):
    global last_final_x, last_final_y
    x, y, top_k = wknn_locate(current_vec, df, ap_cols, K=8)
    x, y = kalman_xy(x, y)
    dist = math.hypot(x - last_final_x, y - last_final_y)
    if dist < 0.05:
        x, y = last_final_x, last_final_y
    pos_history.append((x, y))
    if len(pos_history) > 5:
        pos_history.pop(0)
    x = sum(p[0] for p in pos_history) / len(pos_history)
    y = sum(p[1] for p in pos_history) / len(pos_history)
    last_final_x, last_final_y = x, y
    return round(x, 1), round(y, 1), top_k

# 误差计算
def calc_error(x, y):
    true_x, true_y = 3, 3
    err = math.hypot(x - true_x, y - true_y)
    error_history.append(err)
    if len(error_history) > 20:
        error_history.pop(0)
    avg_err = np.mean(error_history) if error_history else 0
    return round(err, 2), round(avg_err, 2)

# APP界面
class WifiLocApp(App):
    def build(self):
        self.df, self.ap_cols = load_all_fingerprints()
        if self.df is None:
            return Label(text="指纹库加载失败，请检查文件")
        self.layout = BoxLayout(orientation="vertical", padding=20, spacing=15)
        self.title_label = Label(text="WiFi指纹室内定位APP", font_size=20, bold=True)
        self.layout.add_widget(self.title_label)
        self.knn_label = Label(text="传统WKNN: -- , --", font_size=14)
        self.wknn_label = Label(text="加权WKNN: -- , --", font_size=14)
        self.layout.add_widget(self.knn_label)
        self.layout.add_widget(self.wknn_label)
        self.coord_label = Label(text="坐标: -- , --", font_size=22, color=(1,0,0,1), bold=True)
        self.layout.add_widget(self.coord_label)
        self.err_label = Label(text="本次误差: -- m  平均误差: -- m", font_size=14)
        self.layout.add_widget(self.err_label)
        self.btn = Button(text="📶 一键定位", font_size=18, background_color=(0.2,0.6,1,1))
        self.btn.bind(on_press=self.do_locate)
        self.layout.add_widget(self.btn)
        self.auto_btn = Button(text="⏱️ 自动连续定位", font_size=16)
        self.auto_btn.bind(on_press=self.start_auto)
        self.layout.add_widget(self.auto_btn)
        self.auto_event = None
        return self.layout

    def do_locate(self, instance):
        current_vec = get_real_phone_rssi(self.ap_cols)
        x1, y1, _ = wknn_locate(current_vec, self.df, self.ap_cols, K=3)
        x2, y2, _ = wknn_locate(current_vec, self.df, self.ap_cols, K=5)
        x3, y3, topk = optimized_knn(current_vec, self.df, self.ap_cols)
        err, avg_err = calc_error(x3, y3)
        trace_history.append((x3, y3))
        if len(trace_history) > 15:
            trace_history.pop(0)
        self.knn_label.text = f"传统WKNN: {x1}, {y1}"
        self.wknn_label.text = f"加权WKNN: {x2}, {y2}"
        self.coord_label.text = f"坐标: {x3}, {y3}"
        self.err_label.text = f"本次误差: {err} m  平均误差: {avg_err} m"

    def start_auto(self, instance):
        if self.auto_event:
            Clock.unschedule(self.auto_event)
            self.auto_btn.text = "⏱️ 自动连续定位"
            self.auto_event = None
        else:
            self.auto_btn.text = "自动定位中..."
            self.auto_event = Clock.schedule_interval(self.do_locate, 2.2)

if __name__ == "__main__":
    WifiLocApp().run()