import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from mcstatus import JavaServer as MinecraftServer
import threading
import time
import subprocess

class ServerConsoleApp:
    def __init__(self, root, server_address="localhost"):
        self.root = root
        self.server = MinecraftServer(server_address)
        self.root.title("Minecraft 伺服器狀態監控")
        # Set the working directory for the Minecraft server process
        self.server_dir = "server"
        self.root.geometry("800x600")
        
        
        
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
        self.power_button = tk.Button(self.left_frame, text="啟動伺服器", command=self.toggle_server)
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
        self.console_text.delete(1.0, tk.END)  # 清空控制台
        if self.process is None and not self.online:
            # 以子程序啟動 Minecraft 伺服器（範例命令，請改成你的啟動指令）
            command = ["java", "-Xmx12G", "-Xms512M", "-jar", "fabric-server-launcher.jar"]
            self.process = subprocess.Popen(
                command,
                cwd=self.server_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # 啟動線程讀取輸出
            threading.Thread(target=self.read_output, daemon=True).start()
            threading.Thread(target=self.update_status_loop, daemon=True).start()
            self.power_button.config(state='disabled')
            self.status_label.config(text=f"伺服器狀態: 啟動中...")
            self.player_label.config(text=f"在線玩家數: -")
            self.player_list_label.config(text=f"在線玩家: -")

    def stop(self):
        self.process = subprocess.run(["stop"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
    def read_output(self):
        for line in self.process.stdout:
            self.append_text(line)
            if "Done" in line:
                self.power_button.config(state='active', text="停止伺服器")
                self.append_text("[Minecraft 伺服器狀態監控] 伺服器啟動完成\n")
                self.online = True
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

if __name__ == "__main__":
    root = tk.Tk()
    # server_ip = "localhost"  # 請改成你的 Minecraft 伺服器地址
    # app = MinecraftStatusApp(root, server_ip)
    # root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    
    app = ServerConsoleApp(root)
    root.mainloop()
