import json
import time
import threading
import numpy as np
from mss import mss as mss_module
import kmNet
from ctypes import WinDLL
import sys

# Khởi tạo các thư viện hệ thống của Windows để có thể sử dụng các hàm API của Windows (chủ yếu cho xác định 2 chiều cao dài của cửa sổ)
user32, kernel32, shcore = (
    WinDLL("user32", use_last_error=True),
    WinDLL("kernel32", use_last_error=True),
    WinDLL("shcore", use_last_error=True),
)

# Thiết lập độ nhận diện DPI cho chương trình
shcore.SetProcessDpiAwareness(2)

# Lấy kích thước màn hình (chú ý tất cả các cửa sổ nên để maxsize để tránh lỗi)
WIDTH, HEIGHT = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

# Thiết lập vùng phát hiện mục tiêu
ZONE = 5
GRAB_ZONE = {
    "left": int(WIDTH / 2 - ZONE),
    "top": int(HEIGHT / 2 - ZONE),
    "width": 2 * ZONE,
    "height": 2 * ZONE,
}

# Thiết lập vùng phát hiện mục tiêu khi scope
SCOPE_ZONE = 3
SCOPE_GRAB_ZONE = {
    "left": int(WIDTH / 2 - SCOPE_ZONE),
    "top": int(HEIGHT / 2 - SCOPE_ZONE),
    "width": 2 * SCOPE_ZONE,
    "height": 2 * SCOPE_ZONE,
}

def exit_program():
    """Hàm thoát chương trình một cách an toàn."""
    try:
        sys.exit()
    except SystemExit:
        pass
    except:
        raise SystemExit

class TriggerBot:
    def __init__(self):
        """Khởi tạo các biến và đọc cấu hình từ file config.json."""
        self.triggerbot = False
        self.exit_program = False
        self.is_scoped = False
        self.target_detected = False

        # Đọc cấu hình từ file config.json
        try:
            with open('config.json') as json_file:
                data = json.load(json_file)
            self.ip = data["ip"]
            self.port = data["port"]
            self.uid = data["uid"]
            self.trigger_delay = data["trigger_delay"]
            self.base_delay = data["base_delay"]
            self.color_tolerance = data["color_tolerance"]
            self.R, self.G, self.B = data["target_color"]
            self.scope_R, self.scope_G, self.scope_B = data["scope_color"]
            self.scope_color_tolerance = data["scope_color_tolerance"]
            self.scope_R_alt, self.scope_G_alt, self.scope_B_alt = data["scope_color_alt"]
            self.scope_color_tolerance_alt = data["scope_color_tolerance_alt"]
        except KeyError as e:
            print(f"Không tìm thấy biến trong config.json: {e}")
            exit_program()
        except FileNotFoundError:
            print("Không tìm thấy file config.json.")
            exit_program()

        # Khởi tạo kết nối tới kmbox với các thông số từ config.json
        kmNet.init(self.ip, self.port, self.uid)
        # Khởi tạo monitor từ kmbox, listen ở port 10000
        kmNet.monitor(10000)

    def scanpixel(self):
        """Hàm phát hiện màu sắc theo yêu cầu."""
        sct = mss_module()
        while not self.exit_program:
            # Chụp một vùng nhỏ trên màn hình tại vị trí định nghĩa bởi GRAB_ZONE
            img = np.array(sct.grab(GRAB_ZONE))

            # Tạo mask màu để phát hiện màu mục tiêu trong vùng đã chụp
            color_mask = (
                (img[:, :, 0] > self.R - self.color_tolerance) & (img[:, :, 0] < self.R + self.color_tolerance) &
                (img[:, :, 1] > self.G - self.color_tolerance) & (img[:, :, 1] < self.G + self.color_tolerance) &
                (img[:, :, 2] > self.B - self.color_tolerance) & (img[:, :, 2] < self.B + self.color_tolerance)
            )
            
            # Cập nhật trạng thái target_detected nếu phát hiện màu mục tiêu trong vùng đã chụp
            self.target_detected = np.any(color_mask)

    def isScoped(self):
        """Hàm phát hiện màu tâm khi người chơi đang scope."""
        sct = mss_module()
        while not self.exit_program:
            # Chụp một vùng nhỏ trên màn hình tại vị trí scope (2x2)
            img = np.array(sct.grab(SCOPE_GRAB_ZONE))
            # Bypass với màu mặc định (cái này là chuột bên 2 - Xmousebutton2) Nhấn nút chuột này thì triggerbot sẽ dùng alternate color
            if kmNet.isdown_side2() == 1:
                # check bằng alternate color 
                scope_color = (self.scope_R_alt, self.scope_G_alt, self.scope_B_alt)
                scope_color_tolerance = self.scope_color_tolerance_alt
            else:
                # check bằng scope_color như bình thường
                scope_color = (self.scope_R, self.scope_G, self.scope_B)
                scope_color_tolerance = self.scope_color_tolerance

            # Tạo mask màu để phát hiện màu tâm ảo trong vùng đã chụp
            color_mask = (
                (img[:, :, 0] > scope_color[0] - scope_color_tolerance) & (img[:, :, 0] < scope_color[0] + scope_color_tolerance) &
                (img[:, :, 1] > scope_color[1] - scope_color_tolerance) & (img[:, :, 1] < scope_color[1] + scope_color_tolerance) &
                (img[:, :, 2] > scope_color[2] - scope_color_tolerance) & (img[:, :, 2] < scope_color[2] + scope_color_tolerance)
            )
            
            # Cập nhật trạng thái is_scoped nếu phát hiện màu tâm ảo
            self.is_scoped = np.any(color_mask)

    def trigger(self):
        """Hàm kích hoạt bắn khi phát hiện mục tiêu và đang scope."""
        while not self.exit_program:
            if self.is_scoped and self.target_detected:
                # Tính toán độ trễ thực tế dựa trên cấu hình (nếu base delay là 0ms thì actual delay cũng sẽ là 0ms)
                delay_percentage = self.trigger_delay / 100.0
                actual_delay = self.base_delay + self.base_delay * delay_percentage
                time.sleep(actual_delay)
                
                # Gửi lệnh bắn (nhấn phím) qua kmNet
                kmNet.enc_keydown(14)  # số 14 là virtual key K, thêm K thành bắn trong cài đặt của Valorant
                time.sleep(np.random.uniform(0.080, 0.12)) #thời gian giữ trạng thái bắn, randomize để giống người
                kmNet.enc_keyup(14)
                time.sleep(np.random.uniform(0.05, 0.09)) #thời gian delay giữa 2 lần bắn, để tránh rapid fire
            else:
                time.sleep(0.01) #delay giữa vòng lặp để hạn chế tiêu hao cpu

    def startthreads(self):
        """Hàm khởi động các luồng phát hiện và kích hoạt bắn."""
        threading.Thread(target=self.scanpixel).start()
        threading.Thread(target=self.isScoped).start()
        threading.Thread(target=self.trigger).start()

# Khởi tạo và chạy TriggerBot
triggerbot_instance = TriggerBot()
triggerbot_instance.startthreads()
