import os
import sys
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from config.errorCode import *
from PyQt5.QtTest import *
from config.kiwoomType import *
from config.log_class import *      # 로그 파일 임포트

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()
        print("===============  Kiwoom() class start.============== ")

        self.realType   = RealType()
        self.logging    = Logging()     # 로그 인스턴스

        self.logging.logger.debug("Kiwoom() class start.")

        ###### eventloop 모음
        self.login_event_loop               = QEventLoop()      # 로그인 요청용 이벤트 루프
        self.detail_account_info_event_loop = QEventLoop()      # 예수금 요청용 이벤트 루프
        self.calculator_event_loop          = QEventLoop()
        ###########################
        
        ###### 계좌 관련된 변수
        self.account_stock_dict = {}
        self.not_account_stock_dict = {}
        self.account_num = None                 # 계좌번호 담아줄 변수
        self.deposit = 0                        # 예수금
        self.use_money = 0                      # 실제 투자에 사용할 금액
        self.use_money_percent = 0.5            # 예수금에서 실제 사용할 비율
        self.output_deposit = 0                 # 출력가능 금액
        self.account_pwd = "0000"                #
        self.total_profit_loss_money = 0        # 총평가손익금액
        self.total_profit_loss_rate  = 0        # 총수익률(%)
        self.jango_dict = {}
        ###########################

        ###### 전체 종목 관리
        self.all_stock_dict = {}
        #########################

        ###### 종목 정보 가져오기
        self.portfolio_stock_dict = {}
        ###########################

        ###### 종목 분석 용
        self.calcul_data = []
        ##################

        ####### 스크린번호 모음
        self.screen_my_info             = "2000"    # 계좌 관련한 스크린 번호
        self.screen_calculation_stock   = "4000"    # 계산용 스크린 번호
        self.screen_real_stock          = "5000"    # 종목별로 할당할 스크린 번호
        self.screen_meme_stock          = "6000"    # 종목별 할당할 주문용 스크린 번호
        self.screen_start_stop_real     = "1000"    # 장 시작/종료 실시간 스크린 번호
        #########################

        ########### 초기 셋팅 함수들 바로 실행
        self.get_ocx_instance()                 # OCX 방식을 파이썬에 사용할 수 있게 반환해 주는 함수 실행
        self.event_slots()                      # 키움과 연결하기 위한 시그널 / 슬롯 모음
        self.real_event_slots()                 # 실시간 이벤트 시그널 / 슬롯 연결
        self.signal_login_commConnect()         # 로그인 요청 함수 포함
        self.get_account_info()                 # 계좌번호 가져오기
        self.detail_account_info()              # 예수금 요청 시그널 포함
        self.detail_account_mystock()           # 계좌평가잔고내역 가져오기
        QTimer.singleShot(5000, self.not_concluded_account)     #5초 뒤에 미체결 종목들 가져오기 실행
        ######################################################

        # 10초 뒤에 종목정를 담은 딕셔너리 담기 추가
        QTest.qWait(10000)
        self.read_code()
        self.screen_number_setting()

        QTest.qWait(5000)

        #실시간 수신 관련 함수
        self.dynamicCall("SetRealReg(QString, QString, QSting, QString)", self.screen_start_stop_real, '', self.realType.REALTYPE['장시작시간']['장운영구분'], "0")

        for code in self.portfolio_stock_dict.keys():
            screen_num = self.portfolio_stock_dict[code]['스크린번호']
            fids = self.realType.REALTYPE['주식체결']['체결시간']
            self.dynamicCall("SetRealReg(QString, QString, QSting, QString)", screen_num, code, fids, "1")
            self.logging.logger.debug("실시간 등록 : %s, 스크린번호 : %s  , 번호 : %s " %  (code, screen_num, fids))

       # self.not_concluded_account() # 미체결 요청하기

    def get_ocx_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")        # 레지스트리에 저장된 API 모듈 불러오기

    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)        # 로그인 관련 이벤트
        self.OnReceiveTrData.connect(self.trdata_slot)      # 트랜잭션 요청 관련 이벤트
        self.OnReceiveMsg.connect(self.msg_slot)            # 서버에서 메시지 받기

    def real_event_slots(self):
        self.OnReceiveRealData.connect(self.realdata_slot)  # 실시간 이벤트 연결
        self.OnReceiveChejanData.connect(self.chejan_slot)  # 종목 주문체결 관련한 이벤트

    def login_slot(self, errCode):
        self.logging.logger.debug("로그인 정보 코드 : %s " % errors(errCode)[1])
        self.login_event_loop.exit()                        # 로그인 처리가 완료됐으면 이벤트 루프를 종료한다.

    #계좌번호 가져오기
    def get_account_info(self):
        account_list = self.dynamicCall("GetLoginInfo(String)","ACCLIST")   # 계좌번호 반환
        self.account_num = account_list.split(';')[0]                       # a;b;c ->[a, b, c]
        self.logging.logger.debug("나의 보유 계좌번호 : %s" % self.account_num)

    # 수동 로그인설정인 경우 로그인창을 출력해서 로그인을 시도하거나 자동로그인 설정인 경우 로그인창 출력없이 로그인을 시도합니다.
    def signal_login_commConnect(self):
        self.dynamicCall("CommConnect()")                   # 로그인 요청 시그널
        self.login_event_loop.exec_()                       # 이벤트 루프 실행


    def detail_account_info(self, sPrevNext= "0"):

        self.logging.logger.debug("======예수금을 요청하는 부분=================== 시작")

        #Open API 조회 함수 입력값을 설정합니다.
        self.dynamicCall("SetInputValue(String, String)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(String, String)", "비밀번호", self.account_pwd)
        self.dynamicCall("SetInputValue(String, String)", "비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(String, String)", "조회구분", "1")      #추정
        # Open API 조회 함수를 호출해서 전문을 서버로 전송합니다.
        self.dynamicCall("CommRqData(String, String, int, String)", "예수금상세현황요청" ,  "opw00001"	,  sPrevNext,  self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def detail_account_mystock(self, sPrevNext="0"):
        print("======== 계좌평가잔고내역요청 연속조회  %s  ====  시작" % sPrevNext)
        self.dynamicCall("SetInputValue(String, String)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(String, String)", "비밀번호", self.account_pwd)
        self.dynamicCall("SetInputValue(String, String)", "비밀번호입력매체구분", "00")   # 비밀번호입력매체구분 = 00
        self.dynamicCall("SetInputValue(String, String)", "조회구분", "1")              # 1:합산, 2:개별

        self.dynamicCall("CommRqData(String, String, int, String)", "계좌평가잔고내역요청", "opw00018", sPrevNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def not_concluded_account(self, sPrevNext = "0"):

        print("======== 미체결 종목 요청 ========  시작")
        self.dynamicCall("SetInputValue(String, String)", "계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(String, String)", "체결구부", "1")
        self.dynamicCall("SetInputValue(String, String)", "매매구분", "0")
        self.dynamicCall("CommRqData(String, String, int, String)", "실시간미체결요청", "opt10075", sPrevNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):

        if sRQName == "예수금상세현황요청":
            deposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "예수금" )
            self.deposit = int(deposit)                                 # 예수금
            use_money = float(self.deposit) * self.use_money_percent    # 예수금에 50%만 사용
            self.use_money = int(use_money)
            self.use_money = self.use_money / 4                         # 사용금액 4종목으로 나눔
            output_deposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "출금가능금액" )
            self.output_deposit = int(output_deposit)
            self.logging.logger.debug("예수금 : %s   ====   출금가능금액 %s" % (self.deposit , self.use_money , self.output_deposit ))

            self.stop_screen_cancel(self.screen_my_info)
            self.detail_account_info_event_loop.exit()
            self.logging.logger.debug("======예수금을 요청하는 부분=================== 종료")

        elif sRQName == "계좌평가잔고내역요청":

            total_buy_money         = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "총매입금액" )
            total_profit_loss_money = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "총평가손익금액" )
            total_profit_loss_rate  = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "총수익률(%)" )
            self.total_buy_money            = int(total_buy_money)
            self.total_profit_loss_money    = int(total_profit_loss_money)
            self.total_profit_loss_rate     = float(total_profit_loss_rate)
            self.logging.logger.debug("계좌평가잔고내역요청 싱글데이터(총매입금액, 총평가손익금액, 총수익률(%)) : %s -  %s - %s " % (self.total_buy_money, self.total_profit_loss_money,  self.total_profit_loss_rate))

            # 20개까지 조회 가능
            rows = self.dynamicCall("GetRepeatCnt(QString, QString", sTrCode, sRQName)
            cnt = 0
            for i in range(rows):
                code                = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목번호")
                code_nm             = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목명")
                stock_quantity      = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "보유수량")
                buy_price           = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "매입가")
                learn_rate          = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "수익률(%)")
                current_price       = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "현재가")
                total_chegual_price = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "매입금액")
                possible_quantity   = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "매매가능수량")
                code = code.strip()[1:]

                self.logging.logger.debug("종목번호 : %s - 종목명 : %s - 보유수량 : %s - 매입가 : %s - 수익률 : %s - 현재가 : %s" % (code, code_nm, stock_quantity, buy_price, learn_rate, current_price))

                if code in self.account_stock_dict:
                    pass
                else:
                    self.account_stock_dict[code] = {}

                code_nm             = code_nm.strip()
                stock_quantity      = int(stock_quantity.strip())
                buy_price           = int(buy_price.strip())
                learn_rate          = float(learn_rate.strip())
                current_price       = int(current_price.strip())
                total_chegual_price = int(total_chegual_price.strip())
                possible_quantity   = int(possible_quantity.strip())

                self.account_stock_dict[code].update({"종목명 " : code_nm})
                self.account_stock_dict[code].update({"보유수량 ": stock_quantity})
                self.account_stock_dict[code].update({"매입가 ": buy_price})
                self.account_stock_dict[code].update({"수익률(%) " : learn_rate})
                self.account_stock_dict[code].update({"현재가 ": current_price})
                self.account_stock_dict[code].update({"매입금액 ": total_chegual_price})
                self.account_stock_dict[code].update({"매매가능수량 ": possible_quantity})

                cnt += 1

            self.logging.logger.debug("sPrevNext :  %s - row건수 : %s - 계좌 보유종목 건수 : %s" % (sPrevNext, rows , cnt))
            self.logging.logger.debug("계좌에 가지고 있는 종목 : %s" % rows)

            if sPrevNext == "2":
                self.detail_account_mystock(sPrevNext="2")
            else:
                #self.stop_screen_cancel(self.screen_my_info)
                self.detail_account_info_event_loop.exit()

        elif sRQName == "실시간미체결요청":
            rows = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)

            for i in range(rows):
                code            = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목코드")
                code_nm         = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "종목명")
                order_no        = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문번호")
                order_status    = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문상태")  #접수, 확인, 체결
                order_quantity  = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문수량")
                order_price     = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문가격")
                order_gubun     = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "주문구분")  # -매도, +매수, -매도정정, +매수정정
                not_quantity    = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "미체결수량")
                ok_quantity     = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "체결량")

                code            = code.strip()
                code_nm         = code_nm.strip()
                order_no        = int(order_no.strip())
                order_status    = order_status.strip()
                order_quantity  = int(order_quantity.strip())
                order_price     = int(order_price.strip())
                order_gubun     = order_gubun.strip().lstrip('+').lstrip('-')
                not_quantity    = int(not_quantity.strip())
                ok_quantity     = int(ok_quantity.strip())

                if order_no in self.not_account_stock_dict:
                       pass
                else:
                    self.not_account_stock_dict[order_no] = {}

                self.not_account_stock_dict[order_no].update({"종목코드": code})
                self.not_account_stock_dict[order_no].update({"종목명" :  code_nm})
                self.not_account_stock_dict[order_no].update({"주문번호": order_no})
                self.not_account_stock_dict[order_no].update({"주문상태": order_status})
                self.not_account_stock_dict[order_no].update({"주문수량": order_quantity})
                self.not_account_stock_dict[order_no].update({"주문가격": order_price})
                self.not_account_stock_dict[order_no].update({"주문구분": order_gubun})
                self.not_account_stock_dict[order_no].update({"미체결수량": not_quantity})
                self.not_account_stock_dict[order_no].update({"체결량"  :  ok_quantity})

                self.logging.logger.debug("미체결 종목 : %s" % self.not_account_stock_dict[order_no])

            self.detail_account_info_event_loop.exit()

        elif sRQName == "주식일봉차트조회":

            code    = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, 0, "종목코드")
            cnt     = self.dynamicCall("GetRepeatCnt(QString, QString)", sTrCode, sRQName)
            code    = code.strip()
            # data = self.dynamicCall("GetCommDataEx(QString, QString)", sTrCode, sRQName)

            for i in range(cnt): # 0...599
                data = []
                current_price   = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "현재가")
                value           = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "거래량")
                trading_value   = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "거래대금")
                date            = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "일자")
                start_price     = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "시가")
                high_price      = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "고가")
                low_price       = self.dynamicCall("GetCommData(QString, QString, int, QString)", sTrCode, sRQName, i, "저가")

                data.append("")
                data.append(current_price.strip())
                data.append(value.strip())
                data.append(trading_value.strip())
                data.append(date.strip())
                data.append(start_price.strip())
                data.append(high_price.strip())
                data.append(low_price.strip())
                data.append("")

                self.calcul_data.append(data.copy())

            if sPrevNext == "2":
                self.day_kiwoom_db(code=code, sPrevNext=sPrevNext)
            else:
                self.logging.logger.debug("총 일수 %s" % len(self.calcul_data))

                pass_success = False

                # 120일 이평선을 그릴만큼의 데이터가 있는지 체크
                if self.calcul_data == None or len(self.calcul_data) < 120:
                    pass_success = False
                else:
                    # 120일 이평선의 최근 가격 구함
                    total_price = 0
                    for value in self.calcul_data[:120]: #[오늘, 하루전, 하루하루전, 하루하루....]
                        total_price += int(value[1])
                    moving_average_price = total_price / 120

                    # 오늘자 주가가 120일 이평선에 걸쳐있는지 확인
                    bottom_stock_price = False
                    check_price = None
                    # self.calcul_data[0][7] 저가  self.calcul_data[0][6] 고가
                    if int(self.calcul_data[0][7]) <= moving_average_price and moving_average_price <= int(self.calcul_data[0][6]):
                        self.logging.logger.debug("오늘 주가 120이평선에 걸쳐 있는 것 확인")
                        bottom_stock_price = True
                        check_price = int(self.calcul_data[0][6])

                    # 과거 일봉 데이터를 조회하면서 120일 이동평균선보다 주가가 계속 밑에 존재하는지 확인
                    prev_price = None #과거의 일봉 저가
                    if bottom_stock_price == True:
                        moving_average_price_prev = 0
                        price_top_moving = False
                        idx = 1

                        while True:
                            if len(self.calcul_data[idx:]) < 120 : #120일치가 있는지 계속 확인
                                self.logging.logger.debug("120일치가 없음!")
                                break

                            total_price = 0
                            for value in self.calcul_data[idx:120+idx]:
                                total_price += int(value[1])
                            moving_average_price_prev = total_price / 120

                            if moving_average_price_prev <= int(self.calcul_data[idx][6]) and idx <= 20:
                                self.logging.logger.debug("20일 동안 주가가 120일 이평선과 같거나 위에 있으면 조건 통과 못함")
                                price_top_moving = False
                                break

                            elif int(self.calcul_data[idx][7]) > moving_average_price_prev and idx > 20:
                                self.logging.logger.debug("120일 이평선 위에 있는 있는 구간 확인됨")
                                price_top_moving = True
                                prev_price = int(self.calcul_data[idx][7])
                                break

                            idx += 1

                        # 해당부분 이평선이 가장 최근의 이평선 가격보다 낮은지 확인
                        if price_top_moving == True:
                            if moving_average_price > moving_average_price_prev and check_price > prev_price:
                                self.logging.logger.debug("포착된 이평선이 가격이 오늘자(최근일자) 이평선 가격보다 낮은 것 확인됨")
                                self.logging.logger.debug("포착된 부분의 일봉 저가가 오늘자 일봉의 고가보다 낮은지 확인됨 ")
                                pass_success = True

                if pass_success == True:
                    self.logging.logger.debug("조건부 통과됨")

                    code_nm = self.dynamicCall("GetMasterCodeName(QString)", code)

                    f = open("files/condition_stock.txt", "a", encoding="utf8")
                    f.write("%s\t%s\t%s\n" % (code, code_nm, str(self.calcul_data[0][1])))
                    f.close()

                elif pass_success == False:
                    self.logging.logger.debug("조건부 통과 못함")

                self.calcul_data.clear()
                self.calculator_event_loop.exit()

    def stop_screen_cancel(self, sScrNo=None):
        self.dynamicCall("DisconnectRealData(QString)", sScrNo)

    def get_code_list_by_market(self, market_code): # 코스닥 종목을 요청하는 함수 추가
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_code)
        code_list = code_list.split(";")[:-1]        # 마지막 빈자리 자르기 [:-1]
        return code_list

    def calculator_fnc(self):       # 종목 분석과 관련된 코드를 모아놓을 calculator 함수
        code_list = self.get_code_list_by_market("10") # 10 코스닥 갯수
        self.logging.logger.debug("====== 코스닥 갯수 %s " % len(code_list))

        for idx, code in enumerate(code_list):
            self.dynamicCall("DisconnectRealData(QString)", self.screen_calculation_stock)  # 스크린 연결 끊기

            self.logging.logger.debug("%s / %s : KOSDAQ Stock Code : %s is updating... " % (idx+1, len(code_list), code))
            self.day_kiwoom_db(code=code)

    def day_kiwoom_db(self, code=None, date=None, sPrevNext="0"):
        QTest.qWait(3600)   # 3.6초마다 딜레이를 준다.

        self.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")

        if date != None:
            self.dynamicCall("SetInputValue(QString, QString)", "기준일자", date)

        self.dynamicCall("CommRqData(String, String, int, String)", "주식일봉차트조회", "opt10081", sPrevNext, self.screen_calculation_stock)

        self.calculator_event_loop.exec_()

    # 매수법칙 계산 들어가면 됨
    def read_code(self):
        if os.path.exists("files/condition_stock.txt"): # 해당 경로에 파일이 있는지 체크한다.
            f = open("files/condition_stock.txt","r", encoding="utf8")

            lines = f.readlines()       # 파일에 있는 내용들이 모두 읽어와 진다.
            for line in lines:          # 줄바꿈된 내용릉이 한줄 씩 읽어와진다.
                if line != "":
                    ls = line.split("\t")   #["종목코드","종목명","현재가"]

                    stock_code = ls[0]
                    stock_name = ls[1]
                    stock_price = int(ls[2].split("\n")[0])
                    stock_price = abs(stock_price)      #절대값

                    self.portfolio_stock_dict.update({stock_code:{"종목명":stock_name, "현재가":stock_price}})

            f.close()

        self.logging.logger.debug("condition_stock 수집파일 %s " % self.portfolio_stock_dict)

    def merge_dict(self):
        self.all_stock_dict.update({"계좌평가잔고내역"  : self.account_stock_dict})
        self.all_stock_dict.update({"미체결종목"       : self.not_account_stock_dict})
        self.all_stock_dict.update({"포트폴리오종목"    : self.portfolio_stock_dict})

    def screen_number_setting(self):
        screen_overwrite = []

        # 계좌평가잔고내역에 있는 종목들
        for code in self.account_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 미체결에 있는 종목들
        for order_number in self.not_account_stock_dict.keys():
            code = self.not_account_stock_dict[order_number]['종목코드']

            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 포트폴리오에 담겨있는 종목들
        for code in self.portfolio_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        # 스크린 번호 할당
        cnt = 0
        for code in screen_overwrite:
            temp_screen = int(self.screen_real_stock)
            meme_screen = int(self.screen_meme_stock)

            if (cnt % 50) == 0:
                temp_screen += 1        #"5000" -> "5001"
                self.screen_real_stock = str(temp_screen)

            if (cnt % 50) == 0:
                meme_screen += 1
                self.screen_meme_stock = str(meme_screen)

            if code in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict[code].update({"스크린번호":str(self.screen_real_stock)})
                self.portfolio_stock_dict[code].update({"주문용스크린번호": str(self.screen_meme_stock)})

            elif code not in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict.update({code: {"스크린번호":str(self.screen_real_stock),"주문용스크린번호 ":str(self.screen_meme_stock)}})

            cnt += 1

        self.logging.logger.debug("screen_number_setting  %s " % self.portfolio_stock_dict)

    def realdata_slot(self, sCode, sRealType, sRealData):

        if sRealType == "장시작시간":
            fid     = self.realType.REALTYPE[sRealType]['장운영구분']    # (0:장시작전, 2:장종료전(20분), 3:장시작, 4,8:장종료(30분), 9:장마감)
            value   = self.dynamicCall("GetCommRealData(QString, int)", sCode, fid)

            if value == "0":
                self.logging.logger.debug("장 시작 전")

            elif value == "3":
                self.logging.logger.debug("장 시작")

            elif value == "2":
                self.logging.logger.debug("장 종료, 동시호가로 넘어감")

            elif value == "4":
                self.logging.logger.debug("3시30분 장 종료")

                for code in self.portfolio_stock_dict.keys():
                    self.dynamicCall("SetRealRemove(QString, QString)", self.portfolio_stock_dict[sCode]['스크린번호'], sCode)

                QTest.qWait(5000)

                self.file_delete()
                self.calculator_fnc()   # 종목 분석용, 임시용으로 실행

                sys.exit()

        elif sRealType == "주식체결":
            a = self.dynamicCall("GetCommRealData(QSting, int)", sCode, self.realType.REALTYPE[sRealType]['체결시간']) #HHMMSS
            b = self.dynamicCall("GetCommRealData(QSting, int)", sCode, self.realType.REALTYPE[sRealType]['현재가'])   # (+ -) 2500
            b = abs(int(b))
            c = self.dynamicCall("GetCommRealData(QSting, int)", sCode,self.realType.REALTYPE[sRealType]['전일대비'])  #
            c = abs(int(c))
            d = self.dynamicCall("GetCommRealData(QSting, int)", sCode,self.realType.REALTYPE[sRealType]['등락율'])
            d = float(d)
            e = self.dynamicCall("GetCommRealData(QSting, int)", sCode,self.realType.REALTYPE[sRealType]['(최우선)매도호가'])
            e = abs(int(e))
            f = self.dynamicCall("GetCommRealData(QSting, int)", sCode,self.realType.REALTYPE[sRealType]['(최우선)매수호가'])
            f = abs(int(f))
            g = self.dynamicCall("GetCommRealData(QSting, int)", sCode, self.realType.REALTYPE[sRealType]['거래량'])
            g = abs(int(g))
            h = self.dynamicCall("GetCommRealData(QSting, int)", sCode, self.realType.REALTYPE[sRealType]['누적거래량'])
            h = abs(int(h))
            i = self.dynamicCall("GetCommRealData(QSting, int)", sCode, self.realType.REALTYPE[sRealType]['고가'])
            i = abs(int(i))
            j = self.dynamicCall("GetCommRealData(QSting, int)", sCode, self.realType.REALTYPE[sRealType]['시가'])
            j = abs(int(j))
            k = self.dynamicCall("GetCommRealData(QSting, int)", sCode, self.realType.REALTYPE[sRealType]['저가'])
            k = abs(int(k))

            if sCode not in self.portfolio_stock_dict:
                self.portfolio_stock_dict.update({sCode:{}})

            self.portfolio_stock_dict[sCode].update({"체결시간", a})
            self.portfolio_stock_dict[sCode].update({"현재가", b})
            self.portfolio_stock_dict[sCode].update({"전일대비", c})
            self.portfolio_stock_dict[sCode].update({"등락율", d})
            self.portfolio_stock_dict[sCode].update({"(최우선)매도호가", e})
            self.portfolio_stock_dict[sCode].update({"(최우선)매수호가", f})
            self.portfolio_stock_dict[sCode].update({"거래량", g})
            self.portfolio_stock_dict[sCode].update({"누적거래량", h})
            self.portfolio_stock_dict[sCode].update({"고가", i})
            self.portfolio_stock_dict[sCode].update({"시가", j})
            self.portfolio_stock_dict[sCode].update({"저가", k})

            self.logging.logger.debug("실시간 주식체결 %s" % self.portfolio_stock_dict[sCode])

            # 계좌전고평가내역에 있고 오늘 산 잔고에는 없을 경우
            if sCode in self.account_stock_dict.key() and sCode not in self.jango_dict.keys():
                self.logging.logger.debug("%s %s" % ("계좌전고평가내역 매도를 한다", sCode))
                asd = self.account_stock_dict[sCode]
                meme_rate = (b - asd['매입가']) / asd['매입가'] * 100

                if asd['매매가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5):
                    order_success = self.doynamicCall(
                        "[SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)"
                        , ["신규매도", self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 2
                        ,sCode, asd['매매가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'], ""])

                    if order_success == 0:
                        self.logging.logger.debug("계좌전고 매도주문 전달 성공")
                        del self.account_stock_dict[sCode]
                    else:
                        self.logging.logger.debug("계좌전고 매도주문 전달 실패")

            # 오늘 산 잔고에 있을 경우
            elif sCode in self.jango_dict.keys():
                self.logging.logger.debug("%s %s " % ("잔고매도합니다. ", sCode))
                jd = self.jango_dict[sCode]
                meme_rate = (b - jd['매입단가']) / jd['매입단가'] * 100

                if jd['주문가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5):
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["신규매도", self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 2,
                         sCode, jd['주문가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'], ""]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매도주문 전달 성공")
                    else:
                        self.logging.logger.debug("매도주문 전달 실패")


            elif d > 2.0 and sCode not in self.jango_dict:
                print("매수조건 통과 %s" % sCode)

                result = (self.use_money * 0.1) / e
                quantity = int(result)

                order_success = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)"
                                                 , ["신규매수", self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 1
                                                     , sCode, quantity, e, self.realType.SENDTYPE['거래구분']['지정가'], ""]
                )

                if order_success == 0:
                    self.logging.logger.debug("매수주문 전달 성공")
                else:
                    self.logging.logger.debug("매수주문 전달 실패")

            not_meme_list = list(self.not_account_stock_dict)

            for order_num in not_meme_list:
                code        = self.not_account_stock_dict[order_num]["종목코드"]
                meme_price  = self.not_account_stock_dict[order_num]['주문가격']
                not_quantity= self.not_account_stock_dict[order_num]['미체결수량']
                order_gubun = self.not_account_stock_dict[order_num]['주문구분']

                if order_gubun == "매수" and not_quantity > 0 and e > meme_price:
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["매수취소", self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 3,
                         code, 0, 0, self.realType.SENDTYPE['거래구분']['지정가'], order_num]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매수취소 전달 성공")
                    else:
                        self.logging.logger.debug("매수취소 전달 실패")

                elif not_quantity == 0:
                    del self.not_account_stock_dict[order_num]

    def chejan_slot(self, sGubun, nItemCnt, sFIdList):

        if int(sGubun) == "0":       # 주문체결(주문 넣은게 체결 될때마다 불려와짐)
            self.logging.logger.debug("주문체결 등록한다.")
            account_num     = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['계좌번호'])
            sCode           = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목코드'])[1:]
            stock_name      = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목명'])
            origin_order_number = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['원주문번호'])
            order_number    = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문번호'])
            order_status    = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문상태'])
            order_quan      = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문수량'])
            order_price     = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문가격'])
            not_chegual_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['미체결수량'])
            order_gubun     = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문구분'])
            chegual_time_str = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문/체결시간'])
            chegual_price   = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['체결가'])

            stock_name  = stock_name.strip()
            order_quan  = int(order_quan)
            order_price = int(order_price)
            not_chegual_quan = int(not_chegual_quan)
            order_gubun = order_gubun.strip().lstrip('+').lstrip('-')

            if chegual_price == '':
                chegual_price = 0
            else:
                chegual_price = int(chegual_price)

            chegual_quantity = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['체결량'])

            if chegual_quantity == '':
                chegual_quantity = 0
            else:
                chegual_quantity = int(chegual_quantity)
                
            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['현재가'])
            current_price = abs(int(current_price))
            
            first_sell_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['(최우선)매도호가'])
            first_sell_price = abs(int(first_sell_price))
            
            first_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['(최우선)매수호가'])
            first_buy_price = abs(int(first_buy_price))

            ########  새로 들어온 주문이면 주문번호 할당
            if order_number not in self.account_stock_dict.keys():
                self.not_account_stock_dict.update({order_number :{}})

            self.not_account_stock_dict[order_number].update({"종목코드", sCode})
            self.not_account_stock_dict[order_number].update({"주문번호", order_number})
            self.not_account_stock_dict[order_number].update({"종목명", stock_name})
            self.not_account_stock_dict[order_number].update({"주문상태", order_status})
            self.not_account_stock_dict[order_number].update({"주문수량", order_quan})
            self.not_account_stock_dict[order_number].update({"주문가격", order_price})
            self.not_account_stock_dict[order_number].update({"미체결수량", not_chegual_quan})
            self.not_account_stock_dict[order_number].update({"원주문번호", origin_order_number})
            self.not_account_stock_dict[order_number].update({"주문구분", order_gubun})
            self.not_account_stock_dict[order_number].update({"주문/체결시간", chegual_time_str})
            self.not_account_stock_dict[order_number].update({"체결가", chegual_price})
            self.not_account_stock_dict[order_number].update({"체결량", chegual_quantity})
            self.not_account_stock_dict[order_number].update({"현재가", current_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매도호가", first_sell_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매수호가", first_buy_price})

            print(self.not_account_stock_dict)

        elif int(sGubun) == "1":      # 잔고(주문체결이 불려와지고 이어서 잔고가 불러와짐)
            self.logging.logger.debug("잔고 등록한다.")
            account_num     = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['계좌번호'])
            sCode           = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목코드'])[1:]
            stock_name      = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목명'])
            current_price   = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['현재가'])
            stock_quan      = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['보유수량'])
            like_quan       = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['주문가능수량'])
            buy_price       = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매입단가'])
            total_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['총매입가'])  #계좌에 있는 종목의 총매입가
            meme_gubun      = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매도매수구분'])
            first_sell_price = self.dynamicCall("GetChejanData(int)",self.realType.REALTYPE['잔고']['(최우선)매도호가'])
            first_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매수호가'])

            stock_name      = stock_name.strip()
            current_price   = abs(int(current_price))
            stock_quan      = int(stock_quan)
            like_quan       = int(like_quan)
            buy_price       = abs(int(buy_price))
            total_buy_price = int(total_buy_price)
            meme_gubun      = self.realType.REALTYPE['매도수구분'][meme_gubun]
            first_sell_price = abs(int(first_sell_price))
            first_buy_price = abs(int(first_buy_price))

            if sCode not in self.jango_dict.keys():
                self.jango_dict.update({sCode:{}})

            self.jango_dict[sCode].update({"현재가": current_price})
            self.jango_dict[sCode].update({"종목코드": sCode})
            self.jango_dict[sCode].update({"종목명": stock_name})
            self.jango_dict[sCode].update({"보유수량": stock_quan})
            self.jango_dict[sCode].update({"주문가능수량": like_quan})
            self.jango_dict[sCode].update({"매입단가": buy_price})
            self.jango_dict[sCode].update({"총매입가": total_buy_price})
            self.jango_dict[sCode].update({"매도매수구분": meme_gubun})
            self.jango_dict[sCode].update({"(최우선)매도호가": first_sell_price})
            self.jango_dict[sCode].update({"(최우선)매수호가" : first_buy_price})

            if stock_quan == 0:
                del self.jango_dict[sCode]
#                self.dynamicCall("SetRealRemove(QString, QString)", self.portfolio_stock_dict[sCode]['스크린번호'], sCode)

    # 송수신 메새지 get
    def msg_slot(self, sScrNo, sRQName, sTrCode, msg):
        self.logging.logger.debug("스크린: %s, 요청이름: %s, tr 코드 : %s ---- %s " % (sScrNo, sRQName, sTrCode, msg))

    #파일 삭제
    def file_delete(self):
        if os.path.isfile("files/condition_stock.txt"):
            os.remove("files/condition_stock.txt")