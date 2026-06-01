"""
腾讯云抢购脚本 - 单文件版
功能：扫码登录 → 捕获Token → 等待秒杀 → 并发抢购
使用方法：python snap_up.py
依赖：pip install playwright requests && playwright install chromium
"""
import json
import os
import sys
import io
import time
import signal
import requests as req_lib
from datetime import datetime, timedelta
from urllib.parse import quote

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# =================== 配置 =================== #

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_FILE = os.path.join(SCRIPT_DIR, "cookies.json")
TOKEN_FILE = os.path.join(SCRIPT_DIR, "csrf_token.txt")

ACTIVITY_URL = "https://cloud.tencent.com/act/pro/featured-202604?from=29779&cps_key=a1651a7d5dda2e0152ada7c41c6102b0"
CPS_URL = "https://cloud.tencent.com/act/cps/redirect?redirect=6544&cps_key=a1651a7d5dda2e0152ada7c41c6102b0&from=console"
LOGIN_URL = "https://cloud.tencent.com/login?s_url=" + quote(ACTIVITY_URL, safe="")

SECKILL_HOURS = [10, 15]
SECKILL_WINDOW = 20  # 秒杀后20秒内持续抢购
REGION_IDS = [1, 4, 8]
MAX_RETRY = 5
KEEPALIVE_INTERVAL = 60


def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def get_next_seckill_time():
    """计算距离现在最近的下一次抢购时间（每天10点和15点）"""
    now = datetime.now()
    candidates = []
    for day_offset in range(2):
        for hour in SECKILL_HOURS:
            t = now.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
            if t > now + timedelta(seconds=-SECKILL_WINDOW):
                candidates.append(t)
    target = min(candidates)
    return target, int(target.timestamp() * 1000)


# =================== 工具函数 =================== #

TIME_OFFSET_MS = None  # 服务器时间 - 本地时间 的偏移量(毫秒)


def calibrate_time_offset(samples=5):
    """多次采样计算本地时钟与服务器时钟的偏移量，补偿网络RTT"""
    global TIME_OFFSET_MS
    urls = [
        "https://cloud.tencent.com",
        "https://www.tencent.com",
        "https://www.qq.com",
    ]
    offsets = []
    for _ in range(samples):
        for url in urls:
            try:
                t1 = time.time()
                response = req_lib.head(url, timeout=10)
                t2 = time.time()
                server_time = response.headers.get("Date")
                if server_time:
                    dt = datetime.strptime(server_time, "%a, %d %b %Y %H:%M:%S GMT")
                    beijing_time = dt + timedelta(hours=8)
                    server_ms = int(beijing_time.timestamp() * 1000)
                    # 用请求往返中点作为本地参考时间，补偿单程延迟
                    local_mid_ms = int((t1 + t2) / 2 * 1000)
                    rtt_ms = int((t2 - t1) * 1000)
                    offset = server_ms - local_mid_ms
                    offsets.append(offset)
                    log(f"  时间采样: RTT={rtt_ms}ms, 偏移={offset}ms (源: {url})")
                    break
            except Exception:
                continue
        time.sleep(0.3)

    if not offsets:
        log("所有时间源均失败，偏移量设为0（使用本地时间）")
        TIME_OFFSET_MS = 0
        return

    # 去掉最大最小值后取平均，减少异常值影响
    if len(offsets) >= 3:
        offsets.sort()
        offsets = offsets[1:-1]
    TIME_OFFSET_MS = int(sum(offsets) / len(offsets))
    log(f"时间校准完成: 偏移量={TIME_OFFSET_MS}ms (采样{len(offsets)}次)")


def get_server_time():
    """基于校准偏移量推算当前服务器时间，无需每次发请求"""
    global TIME_OFFSET_MS
    if TIME_OFFSET_MS is None:
        calibrate_time_offset()
    return int(time.time() * 1000) + TIME_OFFSET_MS


def build_do_goods_js(region_id, token):
    do_data = {
        "activity_id": 162634773874417,
        "agent_channel": {
            "fromChannel": "", "fromSales": "",
            "isAgentClient": False, "fromUrl": ACTIVITY_URL
        },
        "business": {"id": 22755, "from": "lightningDeals"},
        "goods": [{
            "act_id": 1784747698901873,
            "type": "bundle_budget_mc_lg4_01",
            "goods_param": {
                "BlueprintId": "LINUX_UNIX", "area": 1,
                "ddocUnionConnect": 0, "goodsNum": 1,
                "imageId": "lhbp-eqora508", "scenario": "0",
                "timeSpanUnit": "12m", "zone": "",
                "regionId": region_id,
                "type": "bundle_budget_mc_lg4_01"
            }
        }],
        "preview": 0
    }
    body_str = json.dumps(do_data)
    return f"""
    async () => {{
        try {{
            const resp = await fetch("https://act-api.cloud.tencent.com/dianshi/do-goods", {{
                method: "POST",
                headers: {{"Content-Type": "application/json", "x-csrf-token": "{token}"}},
                body: '{body_str}',
                credentials: "include"
            }});
            return await resp.text();
        }} catch(e) {{
            return JSON.stringify({{code: -1, msg: e.message}});
        }}
    }}
    """


def build_check_js(token):
    check_data = {
        "activity_id": 162634773874417,
        "goods": [{"act_id": 1784747698901873, "region_id": [1, 4, 8]}],
        "preview": 0
    }
    body_str = json.dumps(check_data)
    return f"""
    async () => {{
        try {{
            const resp = await fetch("https://act-api.cloud.tencent.com/dianshi/check-available", {{
                method: "POST",
                headers: {{"Content-Type": "application/json", "x-csrf-token": "{token}"}},
                body: '{body_str}',
                credentials: "include"
            }});
            return await resp.text();
        }} catch(e) {{
            return JSON.stringify({{code: -1, msg: e.message}});
        }}
    }}
    """


# =================== 浏览器生命周期管理 =================== #

class BrowserManager:
    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.captured_tokens = []
        self.is_alive = False
        self.last_keepalive = 0

    def get_token(self):
        return self.captured_tokens[-1] if self.captured_tokens else ""

    def _on_request(self, request):
        token = request.headers.get("x-csrf-token")
        if token and token not in self.captured_tokens:
            self.captured_tokens.append(token)
            log(f"[拦截到新 x-csrf-token] {token}")

    def _on_page_crash(self, _page=None):
        log("页面崩溃！正在恢复...")
        self._recover_page()

    def _on_disconnected(self, _browser=None):
        log("浏览器断开连接！")
        self.is_alive = False

    def start(self):
        from playwright.sync_api import sync_playwright
        log("正在启动 Playwright...")
        self.pw = sync_playwright().start()
        log("正在启动 Chromium 有头浏览器...")
        self.browser = self.pw.chromium.launch(headless=False)
        self.browser.on("disconnected", self._on_disconnected)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.on("request", self._on_request)
        self.page.on("crash", self._on_page_crash)
        self.is_alive = True
        self.last_keepalive = time.time()
        log("浏览器启动完成")

    def _recover_page(self):
        try:
            log("正在恢复页面...")
            self.page = self.context.new_page()
            self.page.on("request", self._on_request)
            self.page.on("crash", self._on_page_crash)
            self.page.goto(ACTIVITY_URL, wait_until="domcontentloaded", timeout=30000)
            log("页面恢复成功")
        except Exception as e:
            log(f"页面恢复失败: {e}")

    def restart(self):
        log("正在完整重启浏览器...")
        self.shutdown(silent=True)
        self.start()
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                saved_cookies = json.load(f)
            self.context.add_cookies(saved_cookies)
        self.page.goto(ACTIVITY_URL, wait_until="domcontentloaded", timeout=30000)
        log("浏览器重启完成")

    def check_alive(self):
        if not self.is_alive:
            return False
        try:
            self.page.evaluate("() => document.readyState")
            return True
        except Exception:
            return False

    def keepalive(self):
        now = time.time()
        if now - self.last_keepalive < KEEPALIVE_INTERVAL:
            return
        self.last_keepalive = now
        if not self.check_alive():
            log("保活检测：浏览器无响应，尝试重启...")
            self.restart()
            return
        try:
            self.page.evaluate("() => { window.__keepalive = Date.now(); }")
        except Exception as e:
            log(f"保活操作异常: {e}，尝试恢复页面...")
            self._recover_page()

    def ensure_on_activity_page(self):
        try:
            current_url = self.page.url
            if "act/pro" not in current_url:
                log("不在活动页面，正在导航...")
                self.page.goto(ACTIVITY_URL, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            self._recover_page()

    def login(self):
        log("正在打开登录页面...")
        self.page.goto(LOGIN_URL, timeout=60000)
        log("登录页面已打开，请扫描二维码...")
        # 等待跳转离开登录页（URL 不再包含 /login）
        self.page.wait_for_url(lambda url: "cloud.tencent.com" in url and "/login" not in url, timeout=300000)
        log("登录成功，页面已跳转")

        # 等待页面完全加载，确保 cookies 写入完整
        log("等待登录态稳定...")
        self.page.wait_for_timeout(5000)

        wait_count = 0
        while wait_count < 60 and not self.captured_tokens:
            self.page.wait_for_timeout(500)
            wait_count += 1
        if self.captured_tokens:
            log(f"Token 捕获成功: {self.get_token()}")
        else:
            log("未自动捕获到 token，将尝试继续...")

        all_cookies = self.context.cookies()
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(all_cookies, f, ensure_ascii=False, indent=2)
        log(f"Cookies 已保存 ({len(all_cookies)} 个)")

        if self.captured_tokens:
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(self.get_token())
            log(f"Token 已保存: {self.get_token()}")

    def load_existing_credentials(self):
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            saved_cookies = json.load(f)
        self.context.add_cookies(saved_cookies)
        log(f"已加载 {len(saved_cookies)} 个 Cookie")
        self.page.goto(ACTIVITY_URL, wait_until="domcontentloaded", timeout=30000)
        log("已打开活动页面，等待捕获实时 x-csrf-token...")
        wait_count = 0
        while wait_count < 60 and not self.captured_tokens:
            self.page.wait_for_timeout(500)
            wait_count += 1
        if self.captured_tokens:
            log(f"实时 Token 捕获成功: {self.get_token()}")
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(self.get_token())
        else:
            log("未捕获到 token，将继续等待页面请求...")

    def precheck(self):
        try:
            check_result = self.page.evaluate(build_check_js(self.get_token()))
            result = json.loads(check_result)
            log(f"预检返回: code={result.get('code')}, msg={result.get('msg')}")
            return result.get("code") == 0
        except Exception as e:
            log(f"预检异常: {e}")
            return False

    def buy(self, region_id):
        try:
            resp_text = self.page.evaluate(build_do_goods_js(region_id, self.get_token()))
            result = json.loads(resp_text)
            log(f"  地域{region_id} 返回: code={result.get('code')}, msg={result.get('msg')}")
            return result
        except Exception as e:
            log(f"  地域{region_id} 异常: {e}")
            return None

    def shutdown(self, silent=False):
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.pw:
                self.pw.stop()
        except Exception:
            pass
        self.is_alive = False
        if not silent:
            log("浏览器已关闭")


# =================== 主程序 =================== #

if __name__ == "__main__":
    log("腾讯云抢购 - 单文件版")
    log(f"抢购时段: 每天 {SECKILL_HOURS} 点整，窗口 {SECKILL_WINDOW} 秒")
    log(f"目标地域: 华北(1), 华东(4), 华南(8)")
    print("=" * 50, flush=True)

    bm = BrowserManager()

    def signal_handler(sig, frame):
        log("收到中断信号，正在退出...")
        bm.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        bm.start()

        # 扫码登录
        bm.login()

        bm.ensure_on_activity_page()
        # 滚动到秒杀区域
        try:
            bm.page.locator("#MS").scroll_into_view_if_needed(timeout=10000)
            log("已滚动到秒杀区域")
        except Exception:
            log("未找到秒杀区域，继续执行")
        log(f"当前 x-csrf-token: {bm.get_token()}")
        log("浏览器就绪，保活机制已启动")
        print("=" * 50, flush=True)

        # 初始时间校准
        log("正在校准服务器时间...")
        calibrate_time_offset()
        print("-" * 50, flush=True)

        # 预检
        bm.precheck()
        print("-" * 50, flush=True)

        # 循环等待每个抢购时段
        while True:
            seckill_dt, seckill_ts = get_next_seckill_time()
            log(f"下一次抢购时间: {seckill_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            recalibrated = False

            # 等待秒杀时间（带保活）
            while True:
                bm.keepalive()
                current_time = get_server_time()
                diff_ms = seckill_ts - current_time
                if diff_ms <= 0:
                    log("秒杀时间到！开始抢购！")
                    break
                diff_seconds = diff_ms / 1000

                # 距抢购30秒时重新校准一次，确保最终精度
                if not recalibrated and diff_seconds <= 30:
                    log("临近抢购，重新校准时间...")
                    calibrate_time_offset(samples=3)
                    recalibrated = True
                    continue

                if diff_seconds > 60:
                    log(f"距离秒杀还有 {diff_seconds:.0f} 秒 ({diff_seconds/60:.1f}分钟)")
                    time.sleep(30)
                elif diff_seconds > 5:
                    log(f"距离秒杀还有 {diff_seconds:.1f} 秒")
                    time.sleep(1)
                else:
                    log(f"距离秒杀还有 {diff_seconds:.3f} 秒")
                    time.sleep(0.05)

            # 抢购前确认浏览器状态
            if not bm.check_alive():
                log("抢购前检测到浏览器异常，紧急重启...")
                bm.restart()

            # 在窗口期内持续抢购
            success = False
            attempt = 0
            while not success:
                elapsed = get_server_time() - seckill_ts
                if elapsed > SECKILL_WINDOW * 1000:
                    log(f"已超过 {SECKILL_WINDOW} 秒窗口期，停止本轮抢购")
                    break
                attempt += 1
                log(f"第 {attempt} 轮抢购 (token: {bm.get_token()})")
                for region_id in REGION_IDS:
                    result = bm.buy(region_id)
                    if isinstance(result, dict) and result.get("code") == 0:
                        log(f"抢购成功！地域={region_id}")
                        log(f"返回: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        success = True
                        break
                if not success:
                    time.sleep(0.3)

            if success:
                log("抢购成功，浏览器保持打开，可手动操作")
                input("按回车键退出...")
                break
            else:
                log("本轮抢购未成功，等待下一个时段...")
                print("=" * 50, flush=True)

    except KeyboardInterrupt:
        log("用户中断")
    except Exception as e:
        log(f"未预期异常: {e}")
    finally:
        bm.shutdown()
        log("程序退出")
