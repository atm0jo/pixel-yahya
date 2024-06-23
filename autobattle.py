import asyncio
import websockets
import json
from random import randint
from colorama import Fore, Style, Back
from time import sleep
from time import time

class Battle:
    """Represents a battle session in the Pixelverse game."""
    win_count = 0
    lose_count = 0
    total_coin = 0
    kabur_count = 0
    def __init__(self):
        """Initializes the Battle object with game settings."""
        self.url = 'https://api-clicker.pixelverse.xyz/api/users'
        with open('./config.json', 'r') as file:
            config = json.load(file)

        self.secret = config['secret']
        self.tgId = config['tgId']
        self.initData = config['initData']
        self.hitRate = config['hitRate']

        self.websocket: websockets.WebSocketClientProtocol = None
        self.battleId = ""
        self.superHit = False
        self.strike = {
            "defense": False,
            "attack": False
        }

        self.space = ""
        self.stop_event = asyncio.Event()


    async def sendHit(self):
        """Continuously sends 'HIT' actions during the battle."""
        while not self.stop_event.is_set():
            if self.superHit:
                await asyncio.sleep(0.3)
                continue

            content = [
                "HIT",
                {
                    "battleId": self.battleId
                }
            ]
            try:
                await self.websocket.send(f"42{json.dumps(content)}")
            except:
                return
            await asyncio.sleep(self.hitRate)

    async def listenerMsg(self):
        if Battle.win_count + Battle.lose_count > 0:
            win_rate = (Battle.win_count / (Battle.win_count + Battle.lose_count)) * 100
        else:
            win_rate = 0  # Atau nilai default lain yang sesuai
    
        """Listens for and processes incoming messages from the game server."""
        while not self.stop_event.is_set():
            try:
                data = await self.websocket.recv()
                # print(data)
            except Exception as err:
                self.stop_event.set()
                return

            if data.startswith('42'):
                data = json.loads(data[2:])  # Remove prefix "42"
                # print(data)
                if data[0] == "HIT":
                    player1_id = data[1]['player1']['userId']
                    player1_energy = data[1]['player1']['energy']
                    player2_id = data[1]['player2']['userId']
                    player2_energy = data[1]['player2']['energy']

                    # Tentukan siapa yang adalah 'r_ghalibie' berdasarkan userId
                    if player1_id == '818a7a31-26be-4557-b0c5-af4f84a821ac':
                        my_energy = player1_energy
                        enemy_energy = player2_energy
                    elif player2_id == '818a7a31-26be-4557-b0c5-af4f84a821ac':
                        my_energy = player2_energy
                        enemy_energy = player1_energy
                    else:
                        continue  # Jika tidak ada userId yang cocok, lanjutkan ke data berikutnya

                    # Cek kondisi untuk kabur
                    if my_energy < 70 and enemy_energy > 120:
                        print(f"{self.space}> Auto Kabur karena energi kita {my_energy} < 70 dan musuh {enemy_energy} > 120")
                        Battle.kabur_count += 1
                        await self.websocket.close()
                        self.stop_event.set()
                        return

                    print(
                        f"{self.space}> {self.player1['name']} ({player1_energy}) {Back.WHITE + Fore.BLACK}VERSUS{Style.RESET_ALL} ({player2_energy}) {self.player2['name']} | Stats: ({Battle.win_count} Win / {Battle.lose_count} Lose) | Win Rate: {win_rate:.2f}% | Run Away: {Battle.kabur_count}"
                        , flush=True)

                elif data[0] == "SET_SUPER_HIT_PREPARE":
                    self.superHit = True

                elif data[0] == "SET_SUPER_HIT_ATTACK_ZONE":
                    content = [
                        "SET_SUPER_HIT_ATTACK_ZONE",
                        {
                            "battleId": self.battleId,
                            "zone": randint(1, 4)
                        }
                    ]
                    await self.websocket.send(f"42{json.dumps(content)}")
                    self.strike['attack'] = True

                elif data[0] == "SET_SUPER_HIT_DEFEND_ZONE":
                    content = [
                        "SET_SUPER_HIT_DEFEND_ZONE",
                        {
                            "battleId": self.battleId,
                            "zone": randint(1, 4)
                        }
                    ]
                    await self.websocket.send(f"42{json.dumps(content)}")
                    self.strike['defense'] = True

                elif data[0] == "END":
                    result = data[1]['result']
                    reward = data[1]['reward']
                    if result == 'WIN':
                        Battle.win_count += 1
                        Battle.total_coin += reward  # Menambahkan reward ke total coins
                    elif result == 'LOSE':
                        Battle.lose_count += 1
                    win_rate = (Battle.win_count / (Battle.win_count + Battle.lose_count)) * 100
                    await asyncio.sleep(0.5)
                    print('')
                    print(
                        f"{self.space}> You {Fore.WHITE}{Back.GREEN if result == 'WIN' else Back.RED}{result}{Style.RESET_ALL} {Style.BRIGHT}{reward}{Style.RESET_ALL} coins !")
                    print(f"{self.space}> Win Rate: Win {Battle.win_count} / Lose { Battle.lose_count} | Total {win_rate:.2f}%")
                    print(f"{self.space}> Total Coins: {Battle.total_coin}")
                    print(f"{self.space}> Total Kabur: {Battle.kabur_count}")
                    await self.websocket.recv()
                    self.stop_event.set()
                    return

                try:
                    if (self.strike['attack'] and not self.strike['defense']) or (
                            self.strike['defense'] and not self.strike['attack']):
                        await self.websocket.recv()
                        await self.websocket.recv()

                    if self.strike['attack'] and self.strike['defense']:
                        await self.websocket.recv()
                        await self.websocket.send("3")
                        await self.websocket.recv()
                        self.superHit = False
                except:
                    pass

    async def handleWssFreeze(self, seconds: int):
        timeToReach = time() + seconds

        while not self.stop_event.is_set():
            if time() > timeToReach:
                print("time is reach wss is close")
                self.websocket.close()
                print(f"bot wss has froze, bot is restarting ...")

            await asyncio.sleep(0.001)

    async def connect(self):
        """Establishes a connection to the game server and starts the battle."""
        uri = "wss://api-clicker.pixelverse.xyz/socket.io/?EIO=4&transport=websocket"

        async with websockets.connect(uri) as websocket:
            self.websocket = websocket

            data = await websocket.recv()

            content = {
                "tg-id": self.tgId,
                "secret": self.secret,
                "initData": self.initData
            }
            await websocket.send(f"40{json.dumps(content)}")

            await websocket.recv()
            data = await websocket.recv()

            data = json.loads(data[2:])  # Remove prefix "42"

            self.battleId = data[1]['battleId']
            self.player1 = {
                "name": data[1]['player1']['username']
            }
            self.player2 = {
                "name": data[1]['player2']['username']
            }

            for i in range(5, 0, -1):
                print(
                    f"{self.space}> The fight start in {Back.RED + Fore.WHITE}{i}{Style.RESET_ALL} seconds.",
                    end="\r", flush=True)
                await asyncio.sleep(1)

            listenerMsgTask = asyncio.create_task(self.listenerMsg())
            hitTask = asyncio.create_task(self.sendHit())
            # handleWssFreeze = asyncio.create_task(self.handleWssFreeze(180))
            
            await asyncio.gather(listenerMsgTask, hitTask)

async def main():
    while True:
            battle = Battle()
            await battle.connect()

if __name__ == "__main__":
    asyncio.run(main())
