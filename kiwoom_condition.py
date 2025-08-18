# kiwoom_condition.py
import asyncio
import json
import websockets

SOCKET_URL = "wss://api.kiwoom.com:10000/api/dostk/websocket"


class KiwoomConditionSearcher:
    """
    조건검색(WebSocket)
    - LOGIN → CNSRLST → CNSRREQ(연속조회 처리)
    - fetch(seq) 호출 시 전체 data(list[dict])를 반환
    """

    def __init__(self, access_token: str, recv_timeout: float = 7.0):
        self.uri = SOCKET_URL
        self.access_token = access_token
        self.websocket = None
        self.connected = False

        self.target_seq: str | None = None
        self.all_data: list[dict] = []

        self._done: asyncio.Future | None = None
        self._receiver_task: asyncio.Task | None = None
        self._recv_timeout = recv_timeout

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        self.connected = True
        # 로그인
        await self._send({"trnm": "LOGIN", "token": self.access_token})

    async def _send(self, message: dict):
        if not self.connected or self.websocket is None:
            await self.connect()
        await self.websocket.send(json.dumps(message))

    async def _recv_once(self) -> dict:
        """단일 수신에 타임아웃을 적용"""
        raw = await asyncio.wait_for(self.websocket.recv(), timeout=self._recv_timeout)
        return json.loads(raw)

    async def _receive_loop(self, throttle_ms: int, max_pages: int):
        page = 0
        while True:
            try:
                resp = await self._recv_once()
            except asyncio.TimeoutError:
                # 더 이상 응답이 없으면 종료(부분 결과라도 반환)
                if self._done and not self._done.done():
                    self._done.set_result(self.all_data)
                return
            except websockets.ConnectionClosed:
                if self._done and not self._done.done():
                    self._done.set_result(self.all_data)
                return

            trnm = resp.get("trnm")
            # print(f"[RECV] {resp}")  # 디버그 원하면 주석 해제

            # LOGIN 성공 → CNSRLST
            if trnm == "LOGIN":
                if resp.get("return_code") == 0:
                    await self._send({"trnm": "CNSRLST"})
                else:
                    if self._done and not self._done.done():
                        self._done.set_result({"error": resp.get("return_msg", "LOGIN 실패")})
                    return

            # CNSRLST 응답 → 첫 CNSRREQ 요청
            elif trnm == "CNSRLST" and self.target_seq:
                await self._send({
                    "trnm": "CNSRREQ",
                    "seq": str(self.target_seq),
                    "search_type": "0",
                    "stex_tp": "K",
                    "cont_yn": "N",
                    "next_key": ""
                })

            # CNSRREQ 응답(연속조회 처리)
            elif trnm == "CNSRREQ":
                if resp.get("return_code") != 0:
                    if self._done and not self._done.done():
                        self._done.set_result({"error": resp.get("return_msg", "조건검색 실패")})
                    return

                # 페이지 데이터 누적
                data_list = resp.get("data", [])
                if data_list:
                    self.all_data.extend(data_list)
                cont_yn = resp.get("cont_yn", "N")
                next_key = resp.get("next_key", "")

                if cont_yn == "Y" and next_key and page < max_pages:
                    page += 1
                    # 너무 빠른 연속 요청 방지(레이트리밋/버퍼링 회피)
                    await asyncio.sleep(throttle_ms / 1000)
                    await self._send({
                        "trnm": "CNSRREQ",
                        "seq": str(self.target_seq),
                        "search_type": "0",
                        "stex_tp": "K",
                        "cont_yn": "Y",
                        "next_key": next_key
                    })
                else:
                    # 마지막 페이지
                    if self._done and not self._done.done():
                        self._done.set_result(self.all_data)
                    return

    async def _graceful_close(self):
        """소켓 종료 및 수신 태스크 취소"""
        try:
            if self.websocket is not None:
                await self.websocket.close()
        except Exception:
            pass
        finally:
            self.connected = False

        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass

    async def fetch(self, seq: str, throttle_ms: int = 150, max_pages: int = 50) -> list[dict] | dict:
        """
        조건검색 전체 결과 반환. 에러 시 {"error": "..."} 반환
        """
        self.target_seq = seq
        loop = asyncio.get_running_loop()
        self._done = loop.create_future()

        await self.connect()
        self._receiver_task = asyncio.create_task(self._receive_loop(throttle_ms, max_pages))

        try:
            result = await self._done  # 완료 신호 대기
            return result
        finally:
            await self._graceful_close()
