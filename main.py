import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox
from mcstatus import JavaServer as MinecraftServer
import threading
import time
import subprocess
import ctypes
import sys
import mcrcr_websocket  # 假設你有 websocket.py 模組
import asyncio
import requests
import json

def is_admin():
    """判斷是否以管理員權限執行（Windows）"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
    
def run_as_admin():
    """以管理員權限重新啟動當前程式"""
    script = sys.executable
    params = " ".join([f'"{arg}"' for arg in sys.argv])
    # 使用 ShellExecuteW 以管理員權限執行
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        return True
    except Exception as e:
        print(f"無法以管理員權限啟動: {e}")
        return False

def check_and_restart_with_admin(root):
    if not is_admin():
        if messagebox.askyesno("權限不足", "此操作需要管理員權限，是否以管理員身份重新啟動？"):
            success = run_as_admin()
            if success:
                root.destroy()  # 關閉當前視窗，等待新視窗以管理員權限啟動
                sys.exit(0)
            else:
                messagebox.showerror("錯誤", "無法以管理員權限重新啟動程式。")
        else:
            messagebox.showwarning("權限不足", "沒有管理員權限，無法啟動伺服器。")
        return False
    return True

class ServerConsoleApp:
    def __init__(self, root, server_address="localhost"):
        self.root = root
        self.server = MinecraftServer(server_address)
        self.root.title("Minecraft 伺服器狀態監控")
        # Set the working directory for the Minecraft server process
        self.server_dir = "server"
        self.root.geometry("800x600")
        self.websocket_server = mcrcr_websocket.websocketserver(self)
        self.file_upload_url = "https://rippou-ripple-web.fly.dev/rippou-ripple-server/survival/upload"
        
        self.event_loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_event_loop, daemon=True).start()
        self.server_status = {
            "online": False,
            "online_player": 0,
            "max_player": 20,
            "player_list": None
        }
        
        
        
        # 建立 Frame left
        self.left_frame = tk.Frame(root, width=250)
        self.left_frame.pack(side='left', fill='y')
        
        self.status_label = tk.Label(self.left_frame, text="伺服器狀態: 離線", font=("Arial", 14))
        self.status_label.pack(pady=10, anchor='w')

        self.player_label = tk.Label(self.left_frame, text="在線玩家數: -", font=("Arial", 14))
        self.player_label.pack(pady=10, anchor='w')

        
        self.player_list_label = tk.Label(self.left_frame, text="在線玩家: -", font=("Arial", 14), anchor='w', justify='left')
        self.player_list_label.pack(pady=10, anchor='w')
        # 按鈕啟動伺服器（示意，請改成你的啟動指令）
        self.power_button = tk.Button(self.left_frame, text="啟動伺服器", command= self.toggle_server)
        self.power_button.pack(pady=5)
        
        
        
        # 建立 Frame middle
        self.middle_frame = tk.Frame(root, width=200, bg="#f0f0f0")
        self.middle_frame.pack(side='left', fill='both', expand=True)
        
        # 中間預留
        self.middle_placeholder = tk.Label(self.middle_frame, text="（預留區域）", font=("Arial", 12), bg="#f0f0f0")
        self.middle_placeholder.pack(expand=True)
        
        
        
        # 建立 Frame right
        self.right_frame = tk.Frame(root, width=450)
        self.right_frame.pack(side='left', fill='both', expand=True)

        self.console_text = ScrolledText(self.right_frame, wrap=tk.WORD, state='disabled')
        self.console_text.pack(expand=True, fill='both')
        
        

        # 啟動背景執行緒定時更新狀態
        self.process = None
        self.online = False
        self.websocket_server.start_websocket_server()

    def update_status_loop(self):
        while self.process is None or not self.online:
            time.sleep(1) # 等待伺服器啟動
        while self.process is not None and self.online:
            time.sleep(1)  # 每秒更新一次
            try:
                status = self.server.status()
                online = status.players.online
                players = status.players.sample
                max_players = status.players.max
                self.update_labels(True, online, max_players, players)
            except Exception as e:
                print(f"錯誤: {e}")
                self.update_labels(False, 0, 0, [])


    def update_labels(self, online, online_count, max_count, players):
        # Tkinter UI 更新必須在主執行緒中執行，使用 after 方法
        def update():
            self.server_status = {
                "cmd": "status",
                "online": online,
                "online_player": online_count,
                "max_player": max_count,
                "player_list": f"\n{(lambda players: '\n'.join([player.name for player in players]))(players) if online_count>=1 else "無玩家在線"}"
            }
            self.server_status.update({"cmd": "status"})
            asyncio.run_coroutine_threadsafe(self.websocket_server.broadcast(self.server_status), self.event_loop)
            self.status_label.config(text=f"伺服器狀態: {'在線' if online else '離線'}")
            self.player_label.config(text=f"在線玩家數: {f"{online_count} / {max_count}" if online else '-' }")
            self.player_list_label.config(text=f"在線玩家:\n{(lambda players: '\n'.join([player.name for player in players]))(players) if online_count>=1 else "無玩家在線"}")
        self.root.after(0, update)
        
    def toggle_server(self):
        if self.process is not None and self.online:
            if self.process.stdin:
                self.power_button.config(state='disabled', text="啟動伺服器")
                self.process.stdin.write("stop\n")
                self.process.stdin.flush()
            return
        self.console_text.config(state='normal')
        self.console_text.delete(1.0, tk.END)
        self.console_text.config(state='disabled')  # 清空控制台
        
        if self.process is None or not self.online:
            try:
                # 以子程序啟動 Minecraft 伺服器（範例命令，請改成你的啟動指令）
                command = ["java", "-Xmx12G", "-Xms512M", "-jar", "fabric-server-launcher.jar"]
                self.process = subprocess.Popen(
                    command,
                    cwd=self.server_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    encoding='utf-8'
                )

                # 啟動線程讀取輸出
                threading.Thread(target=self.read_output, daemon=True).start()
                threading.Thread(target=self.update_status_loop, daemon=True).start()
                self.power_button.config(state='disabled')
                self.status_label.config(text=f"伺服器狀態: 啟動中...")
                self.player_label.config(text=f"在線玩家數: -")
                self.player_list_label.config(text=f"在線玩家: -")
            except Exception as e:
                print(e)

    def stop(self):
        self.process = subprocess.run(["stop"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
    def read_output(self):
        for line in self.process.stdout:
            self.append_text(line)
            asyncio.run_coroutine_threadsafe(self.websocket_server.broadcast({"cmd": "log", "content": line.strip()}), self.event_loop)
            if "Done" in line:
                self.power_button.config(state='active', text="停止伺服器")
                self.append_text("[Minecraft 伺服器狀態監控] 伺服器啟動完成\n")
                self.online = True
                self.server_status
                asyncio.run_coroutine_threadsafe(self.websocket_server.broadcast({"cmd": "log", "content": line.strip()}), self.event_loop)
            elif "AccessDeniedException" in line:
                self.append_text("[Minecraft 伺服器狀態監控] 權限不足，請嘗試以管理員身分啟動app\n")
                check_and_restart_with_admin(self.root)
            elif "Stopping server" in line:
                self.append_text("[Minecraft 伺服器狀態監控] 伺服器正在關閉...\n")
                self.online = False
                self.status_label.config(text=f"伺服器狀態: 關閉中...")
                self.player_label.config(text=f"在線玩家數: -")
                self.player_list_label.config(text=f"在線玩家: -")
        self.process.stdout.close()
        self.process.wait()
        self.append_text("[Minecraft 伺服器狀態監控] 伺服器已關閉\n")
        self.power_button.config(state='active')
        self.update_labels(False, 0, 0, [])
        self.process = None
    
    def append_text(self, text):
        # 在主線程安全更新文字區域
        def update():
            self.console_text.config(state='normal')
            self.console_text.insert(tk.END, text)
            self.console_text.see(tk.END)  # 自動捲動到底部
            self.console_text.config(state='disabled')
        self.root.after(0, update)
    
    def start_event_loop(self):
        """在獨立執行緒中啟動事件迴圈，永久運行"""
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_forever()

    def stop_event_loop(self):
        """停止事件迴圈"""
        self.event_loop.call_soon_threadsafe(self.event_loop.stop)

if __name__ == "__main__":
    root = tk.Tk()
    # server_ip = "localhost"  # 請改成你的 Minecraft 伺服器地址
    # app = MinecraftStatusApp(root, server_ip)
    # root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    
    app = ServerConsoleApp(root)
    root.mainloop()
