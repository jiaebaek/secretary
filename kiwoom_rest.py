import json

import requests
import time
from logger import logger
import asyncio
from kiwoom_condition import KiwoomConditionSearcher

KIWOOM_API_INTERVAL = 0.2

class KiwoomREST:
    BASE_URL = "https://api2.kiwoom.com"

    def __init__(self, appkey, appsecret):
        self.appkey = appkey
        self.appsecret = appsecret
        self.access_token = None
        self.token_expire_time = 0
        self.get_access_token()

    def get_access_token(self):
        url = f"{self.BASE_URL}/oauth2/token"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "secretkey": self.appsecret
        }
        response = requests.post(url, headers=headers, json=data)
        resp_json = response.json()
        self.access_token = resp_json['token']
        self.token_expire_time = time.time() + int(resp_json.get('expires_in', 3600)) - 60

    def ensure_token(self):
        if not self.access_token or time.time() > self.token_expire_time:
            self.get_access_token()

    def _safe_post(self, url, headers, data, max_retries=10):
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, headers=headers, json=data, timeout=30)
                time.sleep(KIWOOM_API_INTERVAL)
                logger.debug(f"[KiwoomREST] API CALL: url={url}, data={data}")
                resp_json = resp.json()
                logger.debug(f"[KiwoomREST] API RESP: {resp_json}")
                return resp_json
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.debug(
                        f"[KiwoomREST] Retryable error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries}) - {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[KiwoomREST] Max retries exceeded: {e}")
                    raise
            except Exception as e:
                logger.exception(f"[KiwoomREST] Non-retryable error occurred: {e}")
                raise

    def request_with_continuation(self, endpoint, api_id, data, result_key=None):
        """연속조회가 필요한 API를 위한 헬퍼 메소드"""
        self.ensure_token()
        all_result = None
        cont_yn = 'N'
        next_key = ''

        while True:
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "Authorization": f"Bearer {self.access_token}",
                "api-id": api_id,
                "cont-yn": cont_yn,
                "next-key": next_key
            }

            # 재시도 로직이 포함된 요청
            url = f"{self.BASE_URL}{endpoint}"
            max_retries = 10
            resp_json = None
            resp = None

            for attempt in range(max_retries):
                try:
                    resp = requests.post(url, headers=headers, json=data, timeout=30)
                    logger.debug(f"[KiwoomREST] API CALL: endpoint={endpoint}, api_id={api_id}, data={data}")
                    time.sleep(KIWOOM_API_INTERVAL)

                    # HTTP 상태 코드 확인
                    if resp.status_code != 200:
                        logger.warning(
                            f"[KiwoomREST] HTTP {resp.status_code} on attempt {attempt + 1}: {resp.text[:200]}")
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.debug(f"[KiwoomREST] Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"[KiwoomREST] Final attempt failed with HTTP {resp.status_code}")
                            resp.raise_for_status()

                    # 응답 내용 확인
                    if not resp.text.strip():
                        logger.warning(f"[KiwoomREST] Empty response on attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.debug(f"[KiwoomREST] Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error("[KiwoomREST] Final attempt returned empty response")
                            raise ValueError("Empty response from API")

                    # JSON 파싱 시도
                    try:
                        resp_json = resp.json()
                        # logger.debug(f"[KiwoomREST] API RESP: {resp_json}")
                        break  # 성공하면 루프 탈출
                    except requests.exceptions.JSONDecodeError as e:
                        logger.warning(f"[KiwoomREST] JSON decode error on attempt {attempt + 1}: {e}")
                        logger.warning(f"[KiwoomREST] Response text: '{resp.text[:200]}...'")
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.debug(f"[KiwoomREST] Retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"[KiwoomREST] Final attempt failed with JSON decode error: {e}")
                            raise

                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"[KiwoomREST] Connection error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.debug(f"[KiwoomREST] Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"[KiwoomREST] Max retries exceeded: {e}")
                        raise

                except Exception as e:
                    logger.error(f"[KiwoomREST] Unexpected error on attempt {attempt + 1}: {e}")
                    raise

            if resp_json is None:
                break

            # 결과 누적
            if all_result is None:
                all_result = resp_json.copy()
                if result_key and result_key in resp_json:
                    all_result[result_key] = []

            if result_key and result_key in resp_json:
                all_result[result_key].extend(resp_json[result_key])

            cont_yn = resp.headers.get('cont-yn', 'N')
            next_key = resp.headers.get('next-key', '')
            if cont_yn != 'Y':
                break

        return all_result if all_result is not None else {}

    def request(self, endpoint, api_id, data=None):
        self.ensure_token()
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": f"Bearer {self.access_token}",
            "api-id": api_id
        }
        return self._safe_post(url, headers, data)

    def _map_balance_stock(self, stock, real_server=False):
        """
        Convert a REST API stock dict to the legacy format for get_balance (현금/일반잔고).
        """
        code = str(stock.get('stk_cd', '')).lstrip('A')
        name = stock.get('stk_nm', '')
        current_price = str(int(stock.get('cur_prc', '0')))
        buy_price = str(int(stock.get('pur_pric', '0')))
        buy_amount = str(int(stock.get('pur_amt', '0')))
        possession_num = str(int(stock.get('rmnd_qty', '0')))
        available_num = str(int(stock.get('trde_able_qty', '0')))
        earning_rate = stock.get('prft_rt', '0')
        loan_date = stock.get('crd_loan_dt', '')
        if real_server:
            try:
                earning_rate = float(earning_rate) / 100
                earning_rate = str(earning_rate)
            except Exception:
                pass
        return {
            'code': code,
            'name': name,
            'current_price': current_price,
            'buy_price': buy_price,
            'buy_amount': buy_amount,
            'possession_num': possession_num,
            'available_num': available_num,
            'earning_rate': '{}'.format(earning_rate),
            'loan_date': loan_date
        }

    def get_balance(self, qry_tp='1', dmst_stex_tp='KRX', include_credit=False):
        """
        계좌 잔고 조회 (2025 REST API, 연속조회 지원)
        :param qry_tp: 조회구분 1:합산, 2:개별
        :param dmst_stex_tp: 국내거래소구분 KRX:한국거래소
        - include_credit=True → qry_tp='2' → 신용잔고까지 포함 (대출일별 세부내역 반환)
        :return: 잔고조회 결과 (dict, 기존 구조와 동일, 융자 종목 제외)
        """
        endpoint = "/api/dostk/acnt"
        api_id = "kt00018"
        data = {
            "qry_tp": qry_tp,
            "dmst_stex_tp": dmst_stex_tp
        }

        result = self.request_with_continuation(endpoint, api_id, data, 'acnt_evlt_remn_indv_tot')

        # 융자 종목 필터링 및 매핑
        if 'acnt_evlt_remn_indv_tot' in result:
            mapped_list = []
            real_server = False  # 실제 서버 여부 판단 필요시 수정

            for stock in result['acnt_evlt_remn_indv_tot']:
                mapped_stock = self._map_balance_stock(stock, real_server=real_server)
                # 융자 종목이 아닌 경우만 추가
                if not include_credit and "*" in mapped_stock['name']:
                        continue
                mapped_list.append(mapped_stock)

            result['acnt_evlt_remn_indv_tot'] = mapped_list

        return result

    def _build_order_data(self, stock_code, quantity, price, tr_type, cond_price, order_price, market, extra=None):
        """
        주문 데이터 공통 생성 함수
        """
        if tr_type is None:
            trde_tp_val = '0'
        else:
            trde_tp_val = str(tr_type)
        if trde_tp_val in ['0', '5', '28', '29', '30', '31', '61', '62', '81']:
            ord_uv_val = str(price) if price is not None else ''
        else:
            ord_uv_val = ''
        data = {
            "dmst_stex_tp": market,
            "stk_cd": stock_code,
            "ord_qty": str(quantity),
            "ord_uv": order_price if order_price is not None else ord_uv_val,
            "trde_tp": trde_tp_val,
            "cond_uv": cond_price,
        }
        if extra:
            data.update(extra)
        return data

    def _place_order(self, endpoint, api_id, data):
        return self.request(endpoint, api_id, data=data)

    def _is_order_success(self, resp_json):
        """
        주문 응답에서 성공 여부를 판단 (return_code == '0'이면 성공)
        """
        return resp_json.get("return_code") == 0

    def place_cash_buy_order(self, stock_code, quantity, price=None, market='KRX', tr_type=None, cond_price='', order_price=None, order_style=None):
        """
        현금 매수 주문 (2025 REST API)
        """
        data = self._build_order_data(stock_code, quantity, price, tr_type, cond_price, order_price, market)
        resp = self._place_order("/api/dostk/ordr", "kt10000", data)
        if self._is_order_success(resp):
            return True
        else:
            return False, resp.get("return_msg", "주문 실패")

    def place_cash_sell_order(self, stock_code, quantity, price=None, market='KRX', tr_type=None, cond_price='', order_price=None, order_style=None):
        """
        현금 매도 주문 (2025 REST API)
        """
        data = self._build_order_data(stock_code, quantity, price, tr_type, cond_price, order_price, market)
        resp = self._place_order("/api/dostk/ordr", "kt10001", data)
        if self._is_order_success(resp):
            return True
        else:
            return False, resp.get("return_msg", "주문 실패")

    def place_credit_buy_order(self, stock_code, quantity, price, market='KRX', tr_type='0', cond_price=''):
        """
        신용 매수 주문 (2025 REST API, kt10006)
        """
        endpoint = "/api/dostk/crdordr"
        api_id = "kt10006"
        data = {
            "dmst_stex_tp": market,
            "stk_cd": stock_code,
            "ord_qty": str(quantity),
            "ord_uv": str(price),
            "trde_tp": str(tr_type),  # '0': 보통
            "cond_uv": cond_price,
        }
        resp = self._place_order(endpoint, api_id, data)
        if self._is_order_success(resp):
            return True
        else:
            return False, resp.get("return_msg", "주문 실패")

    def place_credit_sell_order(self, stock_code, quantity, price, market='KRX',
                                tr_type='0', cond_price='', crd_deal_tp='33', crd_loan_dt=''):
        """
        신용 매도 주문 (2025 REST API, kt10007)
        """
        endpoint = "/api/dostk/crdordr"
        api_id = "kt10007"
        data = {
            "dmst_stex_tp": market,
            "stk_cd": stock_code,
            "ord_qty": str(quantity),
            "ord_uv": str(price),
            "trde_tp": str(tr_type),  # '0': 보통
            "crd_deal_tp": str(crd_deal_tp),  # 신용거래구분 33:융자 , 99:융자합
            "crd_loan_dt": str(crd_loan_dt),
            "cond_uv": cond_price,
        }
        resp = self._place_order(endpoint, api_id, data)
        if self._is_order_success(resp):
            return True
        else:
            return False, resp.get("return_msg", "주문 실패")

    def _build_cancel_modify_data(self, orig_order_no, quantity, price, tr_type, cond_price, order_price, extra=None):
        data = {
            "orig_ord_no": orig_order_no
        }
        if quantity is not None:
            data["ord_qty"] = str(quantity)
        if tr_type is not None:
            data["trde_tp"] = str(tr_type)
        if order_price is not None:
            data["ord_uv"] = str(order_price)
        elif price is not None:
            data["ord_uv"] = str(price)
        if cond_price:
            data["cond_uv"] = cond_price
        if extra:
            data.update(extra)
        return data

    def _place_cancel_modify(self, endpoint, api_id, market, data):
        data["dmst_stex_tp"] = market
        return self.request(endpoint, api_id, data=data)

    def cancel_order(self, orig_order_no, stock_code, quantity, market='KRX'):
        """
        현금 주문 취소 (2025 REST API, kt10003)
        """
        endpoint = "/api/dostk/ordr"
        api_id = "kt10003"
        data = {
            "dmst_stex_tp": market,
            "orig_ord_no": orig_order_no,
            "stk_cd": stock_code,
            "cncl_qty": str(quantity),
        }
        resp = self._place_order(endpoint, api_id, data)
        if self._is_order_success(resp):
            return True
        else:
            return False, resp.get("return_msg", "주문 취소 실패")

    def modify_order(self, orig_order_no, stock_code, quantity, price, market='KRX', cond_price=''):
        """
        현금 주문 정정 (2025 REST API, kt10002)
        """
        endpoint = "/api/dostk/ordr"
        api_id = "kt10002"
        data = {
            "dmst_stex_tp": market,
            "orig_ord_no": orig_order_no,
            "stk_cd": stock_code,
            "mdfy_qty": str(quantity),
            "mdfy_uv": str(price),
            "mdfy_cond_uv": cond_price,
        }
        resp = self._place_order(endpoint, api_id, data)
        if self._is_order_success(resp):
            return True
        else:
            return False, resp.get("return_msg", "주문 정정 실패")

    def cancel_credit_order(self, orig_order_no, stock_code, quantity, market='KRX'):
        """
        신용 주문 취소 (2025 REST API, kt10009)
        """
        endpoint = "/api/dostk/crdordr"
        api_id = "kt10009"
        data = {
            "dmst_stex_tp": market,
            "orig_ord_no": orig_order_no,
            "stk_cd": stock_code,
            "cncl_qty": str(quantity),
        }
        resp = self._place_order(endpoint, api_id, data)
        if self._is_order_success(resp):
            return True
        else:
            return False, resp.get("return_msg", "신용 주문 취소 실패")

    def modify_credit_order(self, orig_order_no, stock_code, quantity, price, market='KRX', cond_price=''):
        """
        신용 주문 정정 (2025 REST API, kt10008)
        """
        endpoint = "/api/dostk/crdordr"
        api_id = "kt10008"
        data = {
            "dmst_stex_tp": market,
            "orig_ord_no": orig_order_no,
            "stk_cd": stock_code,
            "mdfy_qty": str(quantity),
            "mdfy_uv": str(price),
            "mdfy_cond_uv": cond_price,
        }
        resp = self._place_order(endpoint, api_id, data)
        if self._is_order_success(resp):
            return True
        else:
            return False, resp.get("return_msg", "신용 주문 정정 실패")

    def get_unfilled_orders(self, stock_code, all_stk_tp='1', tr_type='0', stex_tp='0'):
        """
        미체결 주문 조회 (2025 REST API, 연속조회 지원)
        :param stock_code: 종목코드 (str)
        :param all_stk_tp: 전체종목구분 (0: 전체, 1: 종목)
        :param tr_type: 매매구분 (0: 전체, 1: 매도, 2: 매수)
        :param stex_tp: 거래소구분 (0: 통합, 1: KRX, 2: NXT)
        :return: 미체결 주문 목록 (dict)
        """
        endpoint = "/api/dostk/acnt"
        api_id = "ka10075"
        data = {
            "all_stk_tp": all_stk_tp,
            "trde_tp": tr_type,
            "stk_cd": stock_code,
            "stex_tp": stex_tp
        }
        return self.request_with_continuation(endpoint, api_id, data, 'oso')

    def _map_credit_stock(self, stock):
        """
        Convert a REST API stock dict to the legacy format for credit stocks (with loan_dt).
        """
        code = str(stock.get('stk_cd', '')).lstrip('A')
        name = stock.get('stk_nm', '')
        current_price = str(int(stock.get('cur_prc', '0')))
        buy_price = str(int(stock.get('avg_prc', '0')))
        buy_amount = str(int(stock.get('pur_amt', '0')))
        possession_num = str(int(stock.get('rmnd_qty', '0')))
        pl_amt = float(stock.get('pl_amt', '0'))
        loan_date_str = stock.get('loan_dt', '')
        from datetime import datetime
        try:
            loan_date = datetime.strptime(loan_date_str, "%Y%m%d")
            today = datetime.today()
            if loan_date.year == today.year and loan_date.month == today.month:
                loan_days = (today - loan_date).days + 2
                if loan_days < 0:
                    loan_days += 2
            elif loan_date.month > today.month:
                loan_days = 1
            else:
                loan_days = today.day
            if loan_days < 0:
                loan_days = 1
        except Exception:
            loan_days = 1
        try:
            buy_amount_f = float(stock.get('pur_amt', 0))
        except Exception:
            buy_amount_f = 0
        interest = round((buy_amount_f * 0.07 * loan_days) / 365, 2)
        profit_loss_price = pl_amt - interest
        if buy_amount_f != 0:
            earning_rate = ((buy_amount_f + profit_loss_price) / buy_amount_f * 100) - 100
        else:
            earning_rate = 0
        return {
            'code': code,
            'name': name,
            'current_price': current_price,
            'buy_price': buy_price,
            'buy_amount': buy_amount,
            'possession_num': possession_num,
            'profit_loss_price': '{}'.format(profit_loss_price),
            'loan_days': '{}'.format(loan_days),
            'earning_rate': '{}'.format(round(earning_rate, 2)),
            'interest': '{}'.format(interest),
            'loan_date': loan_date_str
        }

    def get_account_evaluation(self, qry_tp='0', dmst_stex_tp='KRX'):
        """
        계좌평가현황요청 (2025 REST API, kt00004, 연속조회 지원)
        :param qry_tp: 상장폐지조회구분 0:전체, 1:상장폐지종목제외
        :param dmst_stex_tp: 국내거래소구분 KRX:한국거래소,NXT:넥스트트레이드
        :return: 예수금 등 계좌평가현황(dict)
        """
        endpoint = "/api/dostk/acnt"
        api_id = "kt00004"
        data = {
            "qry_tp": qry_tp,
            "dmst_stex_tp": dmst_stex_tp
        }
        result = self.request_with_continuation(endpoint, api_id, data, 'stk_acnt_evlt_prst')

        # 신용 종목 필터링 및 매핑
        if 'stk_acnt_evlt_prst' in result:
            mapped_list = []
            for stock in result['stk_acnt_evlt_prst']:
                name = stock.get('stk_nm', '')
                if not name.startswith('*'):
                    continue  # 이름이 *로 시작하는 종목만 저장
                mapped_list.append(self._map_credit_stock(stock))
            result['stk_acnt_evlt_prst'] = mapped_list

        return result

    def get_cash_detail(self, qry_tp='3'):
        """
        예수금상세현황요청 (2025 REST API, kt00001, 연속조회 지원)
        :param qry_tp: 조회구분 3:추정조회, 2:일반조회
        :return: 예수금 등 상세현황(dict)
        """
        endpoint = "/api/dostk/acnt"
        api_id = "kt00001"
        data = {
            "qry_tp": qry_tp
        }
        return self.request_with_continuation(endpoint, api_id, data, 'stk_entr_prst')

    def get_interesting_stocks(self, stk_cd=''):
        """
        관심종목정보요청 (2025 REST API, ka10095, 연속조회 지원)
        :param stk_cd: 종목코드 (빈 문자열로 전체 관심종목)
        :return: 관심종목 리스트(dict)
        """
        endpoint = "/api/dostk/stkinfo"
        api_id = "ka10095"
        data = {
            "stk_cd": stk_cd
        }
        return self.request_with_continuation(endpoint, api_id, data, 'atn_stk_infr')

    def get_stock_price(self, stock_code):
        """
        주식기본정보요청 (REST API, ka10001)
        :param stock_code: 종목코드 (str)
        :return: {'current_price': ..., 'name': ...} 등
        """
        endpoint = "/api/dostk/stkinfo"
        api_id = "ka10001"
        data = {
            "stk_cd": stock_code
        }
        result = self.request(endpoint, api_id, data=data)
        return result

    def get_stock_info(self, stock_code):
        """
        종목정보 조회 (REST API, ka10100)
        :param stock_code: 종목코드 (str)
        :return: 종목정보 응답(dict)
        """
        endpoint = "/api/dostk/stkinfo"
        api_id = "ka10100"
        data = {
            "stk_cd": stock_code
        }
        result = self.request(endpoint, api_id, data=data)
        return result

    def get_condition_stocks(self, seq: str, timeout: int = 15):
        """
        조건검색 실행 후 'A' 제거된 종목코드 리스트 반환
        :return: list[str] or {"error": "..."}
        """

        async def _run():
            searcher = KiwoomConditionSearcher(self.access_token, recv_timeout=7.0)
            raw = await searcher.fetch(seq=seq, throttle_ms=150, max_pages=50)
            if isinstance(raw, dict) and "error" in raw:
                return raw
            # 9001 필드에서 'A' 제거
            codes = []
            for item in raw:
                code = item.get("9001", "")
                if code:
                    codes.append(code.lstrip("A"))
            return codes

        try:
            return asyncio.run(asyncio.wait_for(_run(), timeout=timeout))
        except asyncio.TimeoutError:
            return {"error": "조건검색 전체 타임아웃"}
