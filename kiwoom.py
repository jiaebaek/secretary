from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
import logging
import logging.handlers
import datetime
from logger import logger


class Kiwoom(QAxWidget):

    def __init__(self):
        super().__init__()
        self._create_kiwoom_instance()
        self._set_signal_slots()
        self.ret_multi_data = []
        self.ret_data = {}
        self.ret_cnt = 0
        self.code_list = []

    def _create_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")

    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._event_connect)
        self.OnReceiveTrData.connect(self._receive_tr_data)
        self.OnReceiveConditionVer.connect(self._receive_condition_ver)
        self.OnReceiveTrCondition.connect(self._receive_tr_condition)
        self.OnReceiveMsg.connect(self._receive_msg)
        self.OnReceiveChejanData.connect(self._receive_chejan_data)
        #self.OnReceiveRealData.connect(self._receive_real_data)

    def comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    def _event_connect(self, err_code):
        if err_code == 0:
            logger.debug("connected")
        else:
            logger.debug("disconnected")

        self.login_event_loop.exit()

    def get_connect_state(self):
        """
    322         현재 접속상태를 반환합니다.
    323
    324         반환되는 접속상태는 아래와 같습니다.
    325         0: 미연결, 1: 연결
    326
    327         :return: int
    328         """
        state = self.dynamicCall("GetConnectState()")
        return state

    def get_login_info(self):
        ret = self.dynamicCall("GetLoginInfo(QString)", ["ACCNO"])
        return ret.rstrip(';')

    def get_code_list_by_market(self, market):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market)
        code_list = code_list.split(';')
        return code_list[:-1]

    def get_master_code_name(self, code):
        code_name = self.dynamicCall("GetMasterCodeName(QString)", code)
        return code_name

    def get_server_gubun(self):
        ret = self.dynamicCall("KOA_Functions(QString, QString)", "GetServerGubun", "")
        return ret

    def set_input_value(self, id, value):
        self.dynamicCall("SetInputValue(QString, QString)", id, value)

    def comm_rq_data(self, rqname, trcode, next, screen_no):
        self.remained_data = False
        ret = self.dynamicCall("CommRqData(QString, QString, int, QString", rqname, trcode, next, screen_no)
        logging.debug(ret)
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    def _comm_get_data(self, code, real_type, field_name, index, item_name):
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString", code,
                               real_type, field_name, index, item_name)
        return ret.strip()

    def _get_repeat_cnt(self, trcode, rqname):
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return ret


    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        logger.debug('[receiveTrData : {}]'.format(rqname))

        if next == '2':
            self.remained_data = True
        else:
            self.remained_data = False

        if rqname == "잔고조회":
            self._opw00018(rqname, trcode)
        elif rqname == "주식기본정보":
            self._opt10001(rqname, trcode)
        elif rqname == "실시간체결":
            self._opt10075(rqname, trcode)
        elif rqname == "계좌평가현황요청":
            self._opw00004(rqname, trcode)
        elif rqname == "계좌수익률요청":
            self._opt10085(rqname, trcode)
        elif rqname == "수동주문":
            self.order_loop.exit()
            return

        try:
            self.tr_event_loop.exit()
        except Exception as err:
            logger.error(err)
        except AttributeError:
            pass

    def _opw00004(self, rqname, trcode):
        self.ret_cnt = self._get_repeat_cnt(trcode, rqname)

        self.ret_data = {}
        self.ret_multi_data = []

        self.ret_data["remain"] = self._comm_get_data(trcode, "", rqname, 0, "예수금")
        real_server = False if self.get_server_gubun() else True
        try:
            for i in range(self.ret_cnt):
                is_credit = self._comm_get_data(trcode, "", rqname, i, "대출일")
                if is_credit == "":
                    continue
                loan_date = datetime.datetime.strptime(is_credit, "%Y%m%d")
                today = datetime.datetime.today()

                # 같은 달인지 확인
                if loan_date.year == today.year and loan_date.month == today.month:
                    loan_days = (today - loan_date).days + 2  # 신용이자가 영업일 기준으로 +2일 부터 대출이 시행되기 때문에 2일 추가
                    if loan_days < 0:
                        loan_days += 2
                elif loan_date.month > today.month:  # 30, 31일에 매수할 경우, 대출 시행 일이 월이 바뀌면서 미래가 됨
                    loan_days = 1
                else:
                    loan_days = today.day  # 다른 달일 경우 오늘 날짜의 일(day)만 사용

                if loan_days < 0:  # 명절이 낀 경우에는 loan_days가 마이너스가 될 수 있어서 이 경우에는 0으로 처리함
                    loan_days = 1

                buy_amount = float(self._comm_get_data(trcode, "", rqname, i, "매입금액"))

                interest = round((buy_amount * 0.07 * loan_days) / 365, 2) # 이자율은 7프로로 가정
                profit_loss_price = float(self._comm_get_data(trcode, "", rqname, i, "손익금액"))
                profit_loss_price -= interest
                earning_rate = ((buy_amount + profit_loss_price) / buy_amount * 100) - 100

                data = {
                    'code': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "종목코드").lstrip('A')),
                    'name': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "종목명")),
                    'current_price': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "현재가")),
                    'buy_price': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "평균단가")),
                    'buy_amount': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "매입금액")),
                    'possession_num': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "보유수량")),
                    'profit_loss_price': '{}'.format(profit_loss_price),
                    'loan_days': '{}'.format(loan_days),
                    'earning_rate': '{}'.format(round(earning_rate, 2)),
                    'interest': '{}'.format(interest),
                    'loan_date': '{}'.format(is_credit)
                }
                self.ret_multi_data.append(data)

        except Exception as err:
            logger.exception(err)


    def _opt10085(self, rqname, trcode):
        self.ret_cnt = self._get_repeat_cnt(trcode, rqname)

        self.ret_multi_data = []
        real_server = False if self.get_server_gubun() else True
        for i in range(self.ret_cnt):
            is_credit = self._comm_get_data(trcode, "", rqname, i, "대출일")
            if is_credit == "":
                continue

            data = {
                'code': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "종목코드").lstrip('A')),
                'name': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "종목명")),
                'current_price': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "현재가")),
                'buy_price': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "매입가")),
                'buy_amount': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "매입금액")),
                'possession_num': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "보유수량")),
                'credit_price': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "신용이자"))
            }
            self.ret_multi_data.append(data)

    def _opt10075(self, rqname, trcode):
        self.ret_cnt = self._get_repeat_cnt(trcode, rqname)

        self.ret_multi_data = []

        for i in range(self.ret_cnt):
            data = {
                'order_num': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "주문번호")),
                'code': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "종목코드")),
                'name': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "종목명")),
                'state': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "주문상태")),
                'num': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "미체결수량")),
                'type': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "주문구분"))
            }
            self.ret_multi_data.append(data)

    def _opt10001(self, rqname, trcode):
        self.ret_data = {}
        self.ret_data['code'] = self._comm_get_data(trcode, "", rqname, 0, "종목코드")
        self.ret_data['name'] = self._comm_get_data(trcode, "", rqname, 0, "종목명")
        self.ret_data['current_price'] = self._comm_get_data(trcode, "", rqname, 0, "현재가").lstrip('-+')

    def _opw00018(self, rqname, trcode):
        self.ret_cnt = self._get_repeat_cnt(trcode, rqname)

        self.ret_multi_data = []

        real_server = False if self.get_server_gubun() else True

        try:
            for i in range(self.ret_cnt):
                is_credit = self._comm_get_data(trcode, "", rqname, i, "신용구분")
                if is_credit == "03":
                    continue
                total_earning_rate = self._comm_get_data(trcode, "", rqname, i, "수익률(%)")

                if real_server:
                    total_earning_rate = float(total_earning_rate) / 100
                    total_earning_rate = str(total_earning_rate)

                data = {
                    'code': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "종목번호").lstrip('A')),
                    'name': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "종목명")),
                    'current_price': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "현재가")),
                    'buy_price': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "매입가")),
                    'buy_amount': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "매입금액")),
                    'possession_num': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "보유수량")),
                    'available_num': '{}'.format(self._comm_get_data(trcode, "", rqname, i, "매매가능수량")),
                    'earning_rate': '{}'.format(total_earning_rate)
                }
                self.ret_multi_data.append(data)
        except Exception as err:
            logger.exception(err)

    def get_condition_load(self):
        if not self.get_connect_state():
            raise Exception

        isLoad = self.dynamicCall("GetConditionLoad()")

        # 요청 실패시
        if not isLoad:
            raise Exception("getConditionLoad(): 조건식 요청 실패")
        # receiveConditionVer() 이벤트 메서드에서 루프 종료
        self.condition_loop = QEventLoop()
        self.condition_loop.exec_()

    def _get_condition_name_list(self):
        """
    737         조건식 획득 메서드
    738
    739         조건식을 딕셔너리 형태로 반환합니다.
    740         이 메서드는 반드시 receiveConditionVer() 이벤트 메서드안에서 사용해야 합니다.
    741
    742         :return: dict - {인덱스:조건명, 인덱스:조건명, ...}
    743         """

        data = self.dynamicCall("GetConditionNameList()")
        if data == "":
            return None
        condition_list = data.split(';')
        del condition_list[-1]
        condition_dictionary = {}

        for condition in condition_list:
            key, value = condition.split('^')
            condition_dictionary[int(key)] = value

        return condition_dictionary

    def send_condition(self, screenNo, conditionName, conditionIndex, isRealTime):
        """
    763         종목 조건검색 요청 메서드
    764
    765         이 메서드로 얻고자 하는 것은 해당 조건에 맞는 종목코드이다.
    766         해당 종목에 대한 상세정보는 setRealReg() 메서드로 요청할 수 있다.
    767         요청이 실패하는 경우는, 해당 조건식이 없거나, 조건명과 인덱스가 맞지 않거나, 조회 횟수를 초과하는 경우 발생한다.
    768
    769         조건검색에 대한 결과는
    770         1회성 조회의 경우, receiveTrCondition() 이벤트로 결과값이 전달되며
    771         실시간 조회의 경우, receiveTrCondition()과 receiveRealCondition() 이벤트로 결과값이 전달된다.
    772
    773         :param screenNo: string
    774         :param conditionName: string - 조건식 이름
    775         :param conditionIndex: int - 조건식 인덱스
    776         :param isRealTime: int - 조건검색 조회구분(0: 1회성 조회, 1: 실시간 조회)
    777         """
        if not self.get_connect_state():
            raise Exception()
        self.remained_data = False

        if not (isinstance(screenNo, str)
                    and isinstance(conditionName, str)
                    and isinstance(conditionIndex, int)
                    and isinstance(isRealTime, int)):
            raise Exception()

        isRequest = self.dynamicCall("SendCondition(QString, QString, int, int",
                                        screenNo, conditionName, conditionIndex, isRealTime)
        if not isRequest:
            raise Exception("sendCondition(): 조건검색 요청 실패")

        # receiveTrCondition() 이벤트 메서드에서 루프 종료
        self.condition_loop = QEventLoop()
        self.condition_loop.exec_()


    def send_condition_stop(self, screenNo, conditionName, conditionIndex):
        """ 종목 조건검색 중지 메서드 """
        if not self.get_connect_state():
            raise Exception()

        if not (isinstance(screenNo, str)
                and isinstance(conditionName, str)
                and isinstance(conditionIndex, int)):
            raise Exception()

        self.dynamicCall("SendConditionStop(QString, QString, int)", screenNo, conditionName, conditionIndex)
         ###############################################################
         # 메서드 정의: 주문과 잔고처리 관련 메서드                              #
         # 1초에 5회까지 주문 허용                                          #
         ###############################################################

    def _receive_condition_ver(self, receive, msg):
        try:
            if not receive:
                return

            self.condition = self._get_condition_name_list()
            if self.condition is None:
                return
            logger.debug("조건식 개수: ".format(len(self.condition)))

            for key in self.condition.keys():
                logger.debug("조건식: {}: {}".format(key, self.condition[key]))
                logger.debug("key type: ".format(type(key)))

        except Exception as e:
            logger.debug(e)

        finally:
            self.condition_loop.exit()

    def _receive_tr_condition(self, screenNo, codes, conditionName, conditionIndex, inquiry):
        """
    680         (1회성, 실시간) 종목 조건검색 요청시 발생되는 이벤트
    681
    682         :param screenNo: string
    683         :param codes: string - 종목코드 목록(각 종목은 세미콜론으로 구분됨)
    684         :param conditionName: string - 조건식 이름
    685         :param conditionIndex: int - 조건식 인덱스
    686         :param inquiry: int - 조회구분(0: 남은데이터 없음, 2: 남은데이터 있음)
    687         """

        logger.debug("[receiveTrCondition]")
        try:
            if codes == "":
                return

            self.code_list = codes.split(';')
            del self.code_list[-1]

            if inquiry == 2:
                self.remained_data = True

        finally:
            self.condition_loop.exit()


    def _receive_msg(self, screenNo, requestName, trCode, msg):
        """
    124         수신 메시지 이벤트
    125
    126         서버로 어떤 요청을 했을 때(로그인, 주문, 조회 등), 그 요청에 대한 처리내용을 전달해준다.
    127
    128         :param screenNo: string - 화면번호(4자리, 사용자 정의, 서버에 조회나 주문을 요청할 때 이 요청을 구별하기 위한 키값)
    129         :param requestName: string - TR 요청명(사용자 정의)
    130         :param trCode: string
    131         :param msg: string - 서버로 부터의 메시지
    132         """
        logger.debug(requestName + ": " + msg)


    def _receive_chejan_data(self, gubun, itemCnt, fidList):
        """
    286         주문 접수/확인 수신시 이벤트
    287
    288         주문요청후 주문접수, 체결통보, 잔고통보를 수신할 때 마다 호출됩니다.
    289
    290         :param gubun: string - 체결구분('0': 주문접수/주문체결, '1': 잔고통보, '3': 특이신호)
    291         :param itemCnt: int - fid의 갯수
    292         :param fidList: string - fidList 구분은 ;(세미콜론) 이다.
    293         """

        fids = fidList.split(';')
        logger.debug("[receiveChejanData]")
        logger.debug("gubun: {} itemCnt: {} fidList: {}".format(gubun, itemCnt, fidList))
        logger.debug("========================================")
        logger.debug("[ 구분: {}]".format(self._get_chejan_data(913) if '913' in fids else '잔고통보'))
        for fid in fids:
            logger.debug("{}: {}".format(FidList.CHEJAN[int(fid)] if int(fid) in FidList.CHEJAN else fid, self._get_chejan_data(int(fid))))
        logger.debug("========================================")

    def _get_chejan_data(self, fid):
        """
    865         주문접수, 주문체결, 잔고정보를 얻어오는 메서드
    866
    867         이 메서드는 receiveChejanData() 이벤트 메서드가 호출될 때 그 안에서 사용해야 합니다.
    868
    869         :param fid: int
    870         :return: string
    871         """

        if not isinstance(fid, int):
            raise Exception()

        cmd = 'GetChejanData("%s")' % fid
        data = self.dynamicCall(cmd)
        return data

    def send_order(self, requestName, screenNo, accountNo, orderType, code, qty, price, hogaType, originOrderNo):
        """
    819         주식 주문 메서드
    820
    821         sendOrder() 메소드 실행시,
    822         OnReceiveMsg, OnReceiveTrData, OnReceiveChejanData 이벤트가 발생한다.
    823         이 중, 주문에 대한 결과 데이터를 얻기 위해서는 OnReceiveChejanData 이벤트를 통해서 처리한다.
    824         OnReceiveTrData 이벤트를 통해서는 주문번호를 얻을 수 있는데, 주문후 이 이벤트에서 주문번호가 ''공백으로 전달되면,
    825         주문접수 실패를 의미한다.
    826
    827         :param requestName: string - 주문 요청명(사용자 정의)
    828         :param screenNo: string - 화면번호(4자리)
    829         :param accountNo: string - 계좌번호(10자리)
    830         :param orderType: int - 주문유형(1: 신규매수, 2: 신규매도, 3: 매수취소, 4: 매도취소, 5: 매수정정, 6: 매도정정)
    831         :param code: string - 종목코드
    832         :param qty: int - 주문수량
    833         :param price: int - 주문단가
    834         :param hogaType: string - 거래구분(00: 지정가, 03: 시장가, 05: 조건부지정가, 06: 최유리지정가, 그외에는 api 문서참조)
    835         :param originOrderNo: string - 원주문번호(신규주문에는 공백, 정정및 취소주문시 원주문번호르 입력합니다.)
    836         """

        if not self.get_connect_state():
            raise Exception()

        if not (isinstance(requestName, str)
                    and isinstance(screenNo, str)
                    and isinstance(accountNo, str)
                    and isinstance(orderType, int)
                    and isinstance(code, str)
                    and isinstance(qty, int)
                    and isinstance(price, int)
                    and isinstance(hogaType, str)
                    and isinstance(originOrderNo, str)):
            raise Exception()
        logger.debug("{} {} {} {} {} {} {} {} {}".format(requestName, screenNo, accountNo, orderType, code, qty, price, hogaType, originOrderNo))
        return_code = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                      [requestName, screenNo, accountNo, orderType, code, qty, price, hogaType, originOrderNo])

        if return_code == None:
            logger.debug((f"sendOrder({code}, {qty}, {price}): Return Code is None"))
            #raise Exception(f"sendOrder({code}, {qty}, {price}): Return Code is None")
        elif return_code != ReturnCode.OP_ERR_NONE:
            logger.debug((f"sendOrder({code}, {qty}, {price}): {ReturnCode.CAUSE[return_code]}"))
            #raise Exception(f"sendOrder({code}, {qty}, {price}): {ReturnCode.CAUSE[return_code]}")


        # receiveTrData() 에서 루프종료
        self.order_loop = QEventLoop()
        self.order_loop.exec_()

    def send_credit_order(self, requestName, screenNo, accountNo, orderType, code, qty, price, hogaType, creditType, loanDate, originOrderNo):
        """
    819         주식 주문 메서드
    820
    821         sendOrder() 메소드 실행시,
    822         OnReceiveMsg, OnReceiveTrData, OnReceiveChejanData 이벤트가 발생한다.
    823         이 중, 주문에 대한 결과 데이터를 얻기 위해서는 OnReceiveChejanData 이벤트를 통해서 처리한다.
    824         OnReceiveTrData 이벤트를 통해서는 주문번호를 얻을 수 있는데, 주문후 이 이벤트에서 주문번호가 ''공백으로 전달되면,
    825         주문접수 실패를 의미한다.
    826
    827         :param requestName: string - 주문 요청명(사용자 정의)
    828         :param screenNo: string - 화면번호(4자리)
    829         :param accountNo: string - 계좌번호(10자리)
    830         :param orderType: int - 주문유형(1: 신규매수, 2: 신규매도, 3: 매수취소, 4: 매도취소, 5: 매수정정, 6: 매도정정)
    831         :param code: string - 종목코드
    832         :param qty: int - 주문수량
    833         :param price: int - 주문단가
    834         :param hogaType: string - 거래구분(00: 지정가, 03: 시장가, 05: 조건부지정가, 06: 최유리지정가, 그외에는 api 문서참조)
    834         :param creditType: string - 신용구분(03: 시장가, 33: 신용매도 융자 상환, 99: 신용매도 융자 합)
    834         :param loanDate: string - 거래구분(00: 지정가, ㅛㅇ03: 시장가, 05: 조건부지정가, 06: 최유리지정가, 그외에는 api 문서참조)
    835         :param originOrderNo: string - 원주문번호(신규주문에는 공백, 정정및 취소주문시 원주문번호르 입력합니다.)
    836         """

        if not self.get_connect_state():
            raise Exception()

        if not (isinstance(requestName, str)
                    and isinstance(screenNo, str)
                    and isinstance(accountNo, str)
                    and isinstance(orderType, int)
                    and isinstance(code, str)
                    and isinstance(qty, int)
                    and isinstance(price, int)
                    and isinstance(hogaType, str)
                    and isinstance(originOrderNo, str)):
            raise Exception()
        logger.debug("{} {} {} {} {} {} {} {} {} {} {}".format(requestName, screenNo, accountNo, orderType, code, qty, price, hogaType, creditType, loanDate, originOrderNo))
        return_code = self.dynamicCall("SendOrderCredit(QString, QString, QString, int, QString, int, int, QString, QString, QString, QString)",
                                      [requestName, screenNo, accountNo, orderType, code, qty, price, hogaType, creditType, loanDate, originOrderNo])

        if return_code == None:
            logger.debug((f"SendOrderCredit({code}, {qty}, {price}): Return Code is None"))
            #raise Exception(f"sendOrder({code}, {qty}, {price}): Return Code is None")
        elif return_code != ReturnCode.OP_ERR_NONE:
            logger.debug((f"SendOrderCredit({code}, {qty}, {price}): {ReturnCode.CAUSE[return_code]}"))
            #raise Exception(f"sendOrder({code}, {qty}, {price}): {ReturnCode.CAUSE[return_code]}")


        # receiveTrData() 에서 루프종료
        self.order_loop = QEventLoop()
        self.order_loop.exec_()

    def _receive_real_data(self, code, realType, realData):
        """
    248         실시간 데이터 수신 이벤트
    249
    250         실시간 데이터를 수신할 때 마다 호출되며,
    251         setRealReg() 메서드로 등록한 실시간 데이터도 이 이벤트 메서드에 전달됩니다.
    252         getCommRealData() 메서드를 이용해서 실시간 데이터를 얻을 수 있습니다.
    253
    254         :param code: string - 종목코드
    255         :param realType: string - 실시간 타입(KOA의 실시간 목록 참조)
    256         :param realData: string - 실시간 데이터 전문
    257         """

        try:
            logger.debug("[receiveRealData]")
            logger.debug("({})".format(realType))

            if realType not in RealType.REALTYPE:
                return

            data = []

            if code != "":
                data.append(code)
                code_or_not = code
            else:
                code_or_not = realType

            for fid in sorted(RealType.REALTYPE[realType].keys()):
                value = self._get_comm_real_data(code_or_not, fid)
            data.append(value)

            self.real_data = data
            logger.debug(data)

        except Exception as e:
            self.log.error('{}'.format(e))

    def disconnect_real_data(self, screenNo):
        """

    566         해당 화면번호로 설정한 모든 실시간 데이터 요청을 제거합니다.
    567
    568         화면을 종료할 때 반드시 이 메서드를 호출해야 합니다.
    569
    570         :param screenNo: string
    571         """
        if not self.get_connect_state():
            raise Exception()

        if not isinstance(screenNo, str):
            raise Exception()

        self.dynamicCall("DisconnectRealData(QString)", screenNo)


    def _get_comm_real_data(self, code, fid):
        """
    583         실시간 데이터 획득 메서드
    584
    585         이 메서드는 반드시 receiveRealData() 이벤트 메서드가 호출될 때, 그 안에서 사용해야 합니다.
    586
    587         :param code: string - 종목코드
    588         :param fid: - 실시간 타입에 포함된 fid
    589         :return: string - fid에 해당하는 데이터
    590         """


        if not (isinstance(code, str)
                    and isinstance(fid, int)):
            raise Exception()

        value = self.dynamicCall("GetCommRealData(QString, int)", code, fid)

        return value

    def set_real_reg(self, screenNo, codes, fids, realRegType):
        """
    602         실시간 데이터 요청 메서드
    603
    604         종목코드와 fid 리스트를 이용해서 실시간 데이터를 요청하는 메서드입니다.
    605         한번에 등록 가능한 종목과 fid 갯수는 100종목, 100개의 fid 입니다.
    606         실시간등록타입을 0으로 설정하면, 첫 실시간 데이터 요청을 의미하며
    607         실시간등록타입을 1로 설정하면, 추가등록을 의미합니다.
    608
    609         실시간 데이터는 실시간 타입 단위로 receiveRealData() 이벤트로 전달되기 때문에,
    610         이 메서드에서 지정하지 않은 fid 일지라도, 실시간 타입에 포함되어 있다면, 데이터 수신이 가능하다.
    611
    612         :param screenNo: string
    613         :param codes: string - 종목코드 리스트(종목코드;종목코드;...)
    614         :param fids: string - fid 리스트(fid;fid;...)
    615         :param realRegType: string - 실시간등록타입(0: 첫 등록, 1: 추가 등록)
    616         """

        if not self.get_connect_state():
            raise Exception()

        if not (isinstance(screenNo, str)
                    and isinstance(codes, str)
                    and isinstance(fids, str)
                    and isinstance(realRegType, str)):
            raise Exception()

        self.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                        screenNo, codes, fids, realRegType)


    def set_real_remove(self, screenNo, code):
        """
    632         실시간 데이터 중지 메서드
    633
    634         setRealReg() 메서드로 등록한 종목만, 이 메서드를 통해 실시간 데이터 받기를 중지 시킬 수 있습니다.
    635
    636         :param screenNo: string - 화면번호 또는 ALL 키워드 사용가능
    637         :param code: string - 종목코드 또는 ALL 키워드 사용가능
    638         """


        if not self.get_connect_state():
            raise Exception()

        if not (isinstance(screenNo, str)
                    and isinstance(code, str)):
            raise Exception()

        self.dynamicCall("SetRealRemove(QString, QString)", screenNo, code)

    @staticmethod
    def change_format(data):
        strip_data = data.lstrip('-0')
        if strip_data == '':
            strip_data = '0'

        format_data = format(int(strip_data), ',d')
        if data.startswith('-'):
            format_data = '-' + format_data

        return format_data

    @staticmethod
    def change_format2(data):
        strip_data = data[:-2] + '.' + data[-2:]
        strip_data = strip_data.lstrip('-0')

        if strip_data == '':
            strip_data = '0'

        if strip_data[0] == '.':
            strip_data = '0' + strip_data

        if data.startswith('-'):
            strip_data = '-' + strip_data

        return strip_data


class ReturnCode(object):
    """ 키움 OpenApi+ 함수들이 반환하는 값 """

    OP_ERR_NONE = 0  # 정상처리
    OP_ERR_FAIL = -10  # 실패
    OP_ERR_LOGIN = -100  # 사용자정보교환실패
    OP_ERR_CONNECT = -101  # 서버접속실패
    OP_ERR_VERSION = -102  # 버전처리실패
    OP_ERR_FIREWALL = -103  # 개인방화벽실패
    OP_ERR_MEMORY = -104  # 메모리보호실패
    OP_ERR_INPUT = -105  # 함수입력값오류
    OP_ERR_SOCKET_CLOSED = -106  # 통신연결종료
    OP_ERR_SISE_OVERFLOW = -200  # 시세조회과부하
    OP_ERR_RQ_STRUCT_FAIL = -201  # 전문작성초기화실패
    OP_ERR_RQ_STRING_FAIL = -202  # 전문작성입력값오류
    OP_ERR_NO_DATA = -203  # 데이터없음
    OP_ERR_OVER_MAX_DATA = -204  # 조회가능한종목수초과
    OP_ERR_DATA_RCV_FAIL = -205  # 데이터수신실패
    OP_ERR_OVER_MAX_FID = -206  # 조회가능한FID수초과
    OP_ERR_REAL_CANCEL = -207  # 실시간해제오류
    OP_ERR_ORD_WRONG_INPUT = -300  # 입력값오류
    OP_ERR_ORD_WRONG_ACCTNO = -301  # 계좌비밀번호없음
    OP_ERR_OTHER_ACC_USE = -302  # 타인계좌사용오류
    OP_ERR_MIS_2BILL_EXC = -303  # 주문가격이20억원을초과
    OP_ERR_MIS_5BILL_EXC = -304  # 주문가격이50억원을초과
    OP_ERR_MIS_1PER_EXC = -305  # 주문수량이총발행주수의1%초과오류
    OP_ERR_MIS_3PER_EXC = -306  # 주문수량이총발행주수의3%초과오류
    OP_ERR_SEND_FAIL = -307  # 주문전송실패
    OP_ERR_ORD_OVERFLOW = -308  # 주문전송과부하
    OP_ERR_MIS_300CNT_EXC = -309  # 주문수량300계약초과
    OP_ERR_MIS_500CNT_EXC = -310  # 주문수량500계약초과
    OP_ERR_ORD_WRONG_ACCTINFO = -340  # 계좌정보없음
    OP_ERR_ORD_SYMCODE_EMPTY = -500  # 종목코드없음

    CAUSE = {
        0: '정상처리',
        - 10: '실패',
        - 100: '사용자정보교환실패',
        - 102: '버전처리실패',
        - 103: '개인방화벽실패',
        - 104: '메모리보호실패',
        - 105: '함수입력값오류',
        - 106: '통신연결종료',
        - 200: '시세조회과부하',
        - 201: '전문작성초기화실패',
        - 202: '전문작성입력값오류',
        - 203: '데이터없음',
        - 204: '조회가능한종목수초과',
        - 205: '데이터수신실패',
        - 206: '조회가능한FID수초과',
        - 207: '실시간해제오류',
        - 300: '입력값오류',
        - 301: '계좌비밀번호없음',
        - 302: '타인계좌사용오류',
        - 303: '주문가격이20억원을초과',
        - 304: '주문가격이50억원을초과',
        - 305: '주문수량이총발행주수의1%초과오류',
        - 306: '주문수량이총발행주수의3%초과오류',
        - 307: '주문전송실패',
        - 308: '주문전송과부하',
        - 309: '주문수량300계약초과',
        - 310: '주문수량500계약초과',
        - 340: '계좌정보없음',
        - 500: '종목코드없음'
    }

class FidList(object):
    """ receiveChejanData() 이벤트 메서드로 전달되는 FID 목록 """
    CHEJAN = {
        9201: '계좌번호',
        9203: '주문번호',
        9205: '관리자사번',
        9001: '종목코드',
        912: '주문업무분류',
        913: '주문상태',
        302: '종목명',
        900: '주문수량',
        901: '주문가격',
        902: '미체결수량',
        903: '체결누계금액',
        904: '원주문번호',
        905: '주문구분',
        906: '매매구분',
        907: '매도수구분',
        908: '주문/체결시간',
        909: '체결번호',
        910: '체결가',
        911: '체결량',
        10: '현재가',
        27: '(최우선)매도호가',
        28: '(최우선)매수호가',
        914: '단위체결가',
        915: '단위체결량',
        938: '당일매매수수료',
        939: '당일매매세금',
        919: '거부사유',
        920: '화면번호',
        921: '921',
        922: '922',
        923: '923',
        949: '949',
        10010: '10010',
        917: '신용구분',
        916: '대출일',
        930: '보유수량',
        931: '매입단가',
        932: '총매입가',
        933: '주문가능수량',
        945: '당일순매수수량',
        946: '매도/매수구분',
        950: '당일총매도손일',
        951: '예수금',
        307: '기준가',
        8019: '손익율',
        957: '신용금액',
        958: '신용이자',
        959: '담보대출수량',
        924: '924',
        918: '만기일',
        990: '당일실현손익(유가)',
        991: '당일신현손익률(유가)',
        992: '당일실현손익(신용)',
        993: '당일실현손익률(신용)',
        397: '파생상품거래단위',
        305: '상한가',
        306: '하한가'
    }



class RealType(object):
    REALTYPE = {
        '주식시세': {
            10: '현재가',
            11: '전일대비',
            12: '등락율',
            27: '최우선매도호가',
            28: '최우선매수호가',
            13: '누적거래량',
            14: '누적거래대금',
            16: '시가',
            17: '고가',
            18: '저가',
            25: '전일대비기호',
            26: '전일거래량대비',
            29: '거래대금증감',
            30: '거일거래량대비',
            31: '거래회전율',
            32: '거래비용',
            311: '시가총액(억)'
        },

        '주식체결': {
            20: '체결시간(HHMMSS)',
            10: '체결가',
            11: '전일대비',
            12: '등락율',
            27: '최우선매도호가',
            28: '최우선매수호가',
            15: '체결량',
            13: '누적체결량',
            14: '누적거래대금',
            16: '시가',
            17: '고가',
            18: '저가',
            25: '전일대비기호',
            26: '전일거래량대비',
            29: '거래대금증감',
            30: '전일거래량대비',
            31: '거래회전율',
            32: '거래비용',
            228: '체결강도',
            311: '시가총액(억)',
            290: '장구분',
            691: 'KO접근도'
        },

        '주식호가잔량': {
            21: '호가시간',
            41: '매도호가1',
            61: '매도호가수량1',
            81: '매도호가직전대비1',
            51: '매수호가1',
            71: '매수호가수량1',
            91: '매수호가직전대비1',
            42: '매도호가2',
            62: '매도호가수량2',
            82: '매도호가직전대비2',
            52: '매수호가2',
            72: '매수호가수량2',
            92: '매수호가직전대비2',
            43: '매도호가3',
            63: '매도호가수량3',
            83: '매도호가직전대비3',
            53: '매수호가3',
            73: '매수호가수량3',
            93: '매수호가직전대비3',
            44: '매도호가4',
            64: '매도호가수량4',
            84: '매도호가직전대비4',
            54: '매수호가4',
            74: '매수호가수량4',
            94: '매수호가직전대비4',
            45: '매도호가5',
            65: '매도호가수량5',
            85: '매도호가직전대비5',
            55: '매수호가5',
            75: '매수호가수량5',
            95: '매수호가직전대비5',
            46: '매도호가6',
            66: '매도호가수량6',
            86: '매도호가직전대비6',
            56: '매수호가6',
            76: '매수호가수량6',
            96: '매수호가직전대비6',
            47: '매도호가7',
            67: '매도호가수량7',
            87: '매도호가직전대비7',
            57: '매수호가7',
            77: '매수호가수량7',
            97: '매수호가직전대비7',
            48: '매도호가8',
            68: '매도호가수량8',
            88: '매도호가직전대비8',
            58: '매수호가8',
            78: '매수호가수량8',
            98: '매수호가직전대비8',
            49: '매도호가9',
            69: '매도호가수량9',
            89: '매도호가직전대비9',
            59: '매수호가9',
            79: '매수호가수량9',
            99: '매수호가직전대비9',
            50: '매도호가10',
            70: '매도호가수량10',
            90: '매도호가직전대비10',
            60: '매수호가10',
            80: '매수호가수량10',
            100: '매수호가직전대비10',
            121: '매도호가총잔량',
            122: '매도호가총잔량직전대비',
            125: '매수호가총잔량',
            126: '매수호가총잔량직전대비',
            23: '예상체결가',
            24: '예상체결수량',
            128: '순매수잔량(총매수잔량-총매도잔량)',
            129: '매수비율',
            138: '순매도잔량(총매도잔량-총매수잔량)',
            139: '매도비율',
            200: '예상체결가전일종가대비',
            201: '예상체결가전일종가대비등락율',
            238: '예상체결가전일종가대비기호',
            291: '예상체결가',
            292: '예상체결량',
            293: '예상체결가전일대비기호',
            294: '예상체결가전일대비',
            295: '예상체결가전일대비등락율',
            13: '누적거래량',
            299: '전일거래량대비예상체결률',
            215: '장운영구분'
        },

        '장시작시간': {
            215: '장운영구분(0:장시작전, 2:장종료전, 3:장시작, 4,8:장종료, 9:장마감)',
            20: '시간(HHMMSS)',
            214: '장시작예상잔여시간'
        },

        '업종지수': {
            20: '체결시간',
            10: '현재가',
            11: '전일대비',
            12: '등락율',
            15: '거래량',
            13: '누적거래량',
            14: '누적거래대금',
            16: '시가',
            17: '고가',
            18: '저가',
            25: '전일대비기호',
            26: '전일거래량대비(계약,주)'
        },

        '업종등락': {
            20: '체결시간',
            252: '상승종목수',
            251: '상한종목수',
            253: '보합종목수',
            255: '하락종목수',
            254: '하한종목수',
            13: '누적거래량',
            14: '누적거래대금',
            10: '현재가',
            11: '전일대비',
            12: '등락율',
            256: '거래형성종목수',
            257: '거래형성비율',
            25: '전일대비기호'
        },

        '주문체결': {
            9201: '계좌번호',
            9203: '주문번호',
            9205: '관리자사번',
            9001: '종목코드',
            912: '주문분류(jj:주식주문)',
            913: '주문상태(10:원주문, 11:정정주문, 12:취소주문, 20:주문확인, 21:정정확인, 22:취소확인, 90,92:주문거부)',
            302: '종목명',
            900: '주문수량',
            901: '주문가격',
            902: '미체결수량',
            903: '체결누계금액',
            904: '원주문번호',
            905: '주문구분(+:현금매수, -:현금매도)',
            906: '매매구분(보통, 시장가등)',
            907: '매도수구분(1:매도, 2:매수)',
            908: '체결시간(HHMMSS)',
            909: '체결번호',
            910: '체결가',
            911: '체결량',
            10: '체결가',
            27: '최우선매도호가',
            28: '최우선매수호가',
            914: '단위체결가',
            915: '단위체결량',
            938: '당일매매수수료',
            939: '당일매매세금'
        },

        '잔고': {
            9201: '계좌번호',
            9001: '종목코드',
            302: '종목명',
            10: '현재가',
            930: '보유수량',
            931: '매입단가',
            932: '총매입가',
            933: '주문가능수량',
            945: '당일순매수량',
            946: '매도매수구분',
            950: '당일총매도손익',
            951: '예수금',
            27: '최우선매도호가',
            28: '최우선매수호가',
            307: '기준가',
            8019: '손익율'
        },

        '주식시간외호가': {
            21: '호가시간(HHMMSS)',
            131: '시간외매도호가총잔량',
            132: '시간외매도호가총잔량직전대비',
            135: '시간외매수호가총잔량',
            136: '시간외매수호가총잔량직전대비'
        }
    }