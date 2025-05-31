import asyncio
import websockets
import json
import threading

class websocketserver:
    def __init__(self, app):
        self.app = app # MCRCR
        self.clients = set()
        
    async def handler(self, websocket):
        
        self.clients.add(websocket)
        try:
            async for message in websocket:
                
                # 處理接收到的消息
                data = json.loads(message)
                cmd = data.get("cmd")
                self.app.append_text(f"[Websocket] 收到命令: {cmd} \n")
                if cmd == "start":
                    self.app.toggle_server()
                    continue
                
                if cmd == "stop":
                    self.app.toggle_server()
                    continue
                
                if cmd == "status":
                    status = {
                        "online": self.app.online,
                        "players": self.app.player_count,
                        "player_list": self.app.player_list
                    }
                    await websocket.send(json.dumps(status))
                    continue

                if cmd == "command":
                    command = data.get("content")
                    if command:
                        self.app.process.stdin.write(f"{command}\n")
                        self.app.process.stdin.flush()
                        continue
                # if cmd == "get_log":
                    
        except websocket.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            
            
    def start_websocket_server(self, host='localhost', port=8765):
        async def main():
            async with websockets.serve(self.handler, host, port):
                await asyncio.Future()
                
        threading.Thread(target=asyncio.run, args=(main(),), daemon=True).start()

    async def broadcast(self, message):
        if self.clients: 
            msg_text = json.dumps(message)
            await asyncio.gather(*(client.send(msg_text) for client in self.clients))
