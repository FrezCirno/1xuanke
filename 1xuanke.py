#!/usr/bin/env python
# coding:utf-8
import os
import time
import json
import logging
import requests
from bs4 import BeautifulSoup
from base64 import b64encode
from fuzzywuzzy import fuzz
from urllib.parse import parse_qsl, urlsplit


def timestamp():  # 时间戳
    return str(int(time.time() * 1000))


class xuanke1(object):
    objSession = requests.Session()
    # objSession.proxies = {'http': '127.0.0.1:8888'}
    objSession.headers.update(
        {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0'})
    __baseUrl = 'http://1.tongji.edu.cn'

    def __init__(self):
        self.uid = ''
        self.password = ''
        self.token = ''
        self.type = ''
        self.hasLogin1 = False
        self.isLogin = False
        self.roundId = 0

    def __request(self, method, url, params=None, data=None):
        info = [method, url]
        if params:
            info.append('with params =')
            info.append(params)
        if data:
            info.append('with data =')
            info.append(data)
        logging.info(info)
        try:
            res = self.objSession.request(method, self.__baseUrl+url,
                                          params=params, data=data)
            resjson = res.json()
            logging.info(resjson)
            if res.status_code != 200:
                return res.status_code, resjson['message']
            return resjson['code'], resjson['data']
        except:
            logging.error(res.content)
            return res.status_code, res.content

    def post(self, url, params=None, data=None):
        return self.__request('post', url, params, data)

    def get(self, url, params=None):
        return self.__request('get', url, params)

    def login(self, uid=None, password=None):
        '''登录获取sessionId'''
        # relogin
        if uid is None:
            uid = self.uid
        if password is None:
            password = self.password
        if not self.hasLogin1:
            res = login1(uid, password, self.objSession)
            if not res:
                return 400, '统一认证失败'
            self.hasLogin1 = True
        self.uid = res['uid']
        self.password = password
        self.token = res['token']
        tryLoginTimes = 0
        while tryLoginTimes < 1:
            tryLoginTimes += 1
            code, loginInfo = self.post('/api/sessionservice/session/login',
                                        data={'token': self.token, 'uid': self.uid})
            if code == 200:
                loginUser = loginInfo['user']
                self.type = loginUser['type']
                self.isLogin = True
                return code, loginInfo
        return code, loginInfo

    def currentTermCalendar(self):
        '''获取当前学期信息'''
        return self.get('/api/baseresservice/schoolCalendar/currentTermCalendar',
                        {'_t': timestamp()})

    def schoolCalendar(self):
        return self.get('/api/baseresservice/schoolCalendar/list', params={'_t': timestamp()})

    def findUserInfoByIdType(self, uid=None, type=None):
        '''获取学生信息(详细版)'''
        if uid is None:
            uid = str(self.uid)
        if type is None:
            type = str(self.type)
        return self.get('/api/studentservice/studentInfo/findUserInfoByIdType',
                        params={
                            'userId': b64encode(uid.encode('utf-8')),
                            'type': b64encode(type.encode('utf-8')),
                            '_t': timestamp()
                        })

    def findUserInfoByType(self, uid=None, type=None):
        '''获取学生信息(简短版)'''
        if uid is None:
            uid = str(self.uid)
        if type is None:
            type = str(self.type)
        return self.get('/api/studentservice/studentInfo/findUserInfoByType',
                        params={
                            'userId': b64encode(uid.encode('utf-8')),
                            'type': b64encode(type.encode('utf-8')),
                            '_t': timestamp()
                        })

    def myTutor(self):
        return self.get('/api/welcomeservice/tutorStudent/myTutor', params={
            'type': 2,
            '_t': timestamp()
        })

    def getRounds(self, projectId=1):
        '''获取选课开放信息'''
        return self.post('/api/electionservice/student/getRounds',
                         params={'projectId': projectId})

    def loginCheck(self, uid=None):
        '''检查是否登录成功, 选课前可以调用, status=Init说明OK'''
        if uid is None:
            uid = self.uid
        return self.post('/api/electionservice/student/loginCheck', data={
            'roundId': self.roundId,
            'studentId': uid
        })

    def loading(self):
        '''loading的时候调用了这个方法, 响应的status=Ready的时候说明OK'''
        return self.post('/api/electionservice/student/' +
                         str(self.roundId) + '/loading')

    def electRes(self):
        '''轮询选课状态, 响应的status=Processing的时候等待, 为Ready的时候说明完毕, 返回结果'''
        return self.post('/api/electionservice/student/' +
                         str(self.roundId) + '/electRes')

    def getDataBk(self, useLocal=False):
        '''获取个人全部课表信息, 包括已修课程、计划课程、公共选修课、已选课程、正在学的课程等等'''
        if useLocal:
            try:
                with open('lastSucc.json', mode='r') as localDataFile:
                    localDataBk = json.load(localDataFile)
                return (200, localDataBk)
            except:
                print('本地数据源获取失败, 使用网络源')

        resPair = self.post(
            '/api/electionservice/student/' + str(self.roundId) + '/getDataBk')
        if resPair[0] == 200:
            with open('lastSucc.json', mode='w') as file:  # 本地保存一下
                json.dump(resPair[1], file)
        return resPair

    def getTeachClass4Limit(self, courseCode):
        '''获取课程开班情况(包括已选人数等), courseCode为6位课程代码'''
        return self.post('/api/electionservice/student/getTeachClass4Limit', params={
            'roundId': self.roundId,
            'courseCode': courseCode,
            'studentId': self.uid
        })

    def getStuInfoByParam(self, uid=None):
        '''获取学籍信息(专业等)'''
        if uid is None:
            uid = self.uid
        return self.get('/api/studentservice/studentDetailInfo/getStuInfoByParam', params={
            'studentId': uid,
            'stuInfoClass': '学籍信息',
            '_t': timestamp()
        })

    def findCampusProfessionList(self, grade, keyWord, pageSize=10, pageNum=1):
        '''获取学院设立专业的列表'''
        return self.post('/api/commonservice/campusProfession/findCampusProfessionList', data={
            'grade': grade,
            'keyWord': keyWord,
            'pageSize_': pageSize,
            'pageNum_': pageNum
        })

    def getMajorCourseList(self, majorCode, grade, calendarId):
        '''获取专业课表'''
        return self.get('/api/arrangementservice/timetable/major', params={
            'code': majorCode,  # 专业代码
            'grade': grade,  # 入学年份
            'calendarId': calendarId,  # 年份
            '_t': timestamp()
        })

    def findHomePageCommonMsgPublish(self, pageNum=1, pageSize=20):
        '''获取系统公告'''
        return self.post('/api/commonservice/commonMsgPublish/findHomePageCommonMsgPublish', data={
            'pageNum_': pageNum,
            'pageSize_': pageSize
        })

    def studentPlanCountByStuId(self, uid=None):
        '''获取个人培养计划(各部分学分数)'''
        if uid is None:
            uid = self.uid
        return self.get('/api/cultureservice/culturePlan/studentPlanCountByStuId', params={'studentId': uid})

    def elect(self, courseList, withdrawClassList=[]):
        '''选课, 参数格式如下
        {
            'courseCode': 123456,  # 课程编号
            'courseName': 'xxxxxxx',  # 课程名
            'teachClassCode': 12345601,  # 班级编号
            'teachClassId': 111111112483123,  # 班级ID
            'teacherName': 'xx'  # 教师名
        }'''
        return self.post('/api/electionservice/student/elect', data=json.dumps({
            'roundId': self.roundId,
            'elecClassList': courseList,
            'withdrawClassList': withdrawClassList
        }))

    def findStudentTimetab(self, calendarId, uid=None):
        '''个人课表'''
        if uid is None:
            uid = self.uid
        return self.get('/api/electionservice/reportManagement/findStudentTimetab', params={
            'calendarId': calendarId,
            'studentCode': uid,
            '_t': timestamp()
        })

    def findCourseInfoByCode(self, courseCode):
        '''查询某课程开班信息'''
        _, dataBk = self.getDataBk(useLocal=True)
        for plan in dataBk['planCourses']:
            if plan['courseCode'] == courseCode:
                return plan['course']
        for public in dataBk['publicCourses']:
            courseInfo = public['course']
            if courseInfo['courseCode'] == courseCode:
                return courseInfo
        return {}

    def findAllCourseInfoListByName(self, courseName: str):
        '''查询某课程开班信息'''
        res = []
        _, dataBk = self.getDataBk(useLocal=True)
        for plan in dataBk['planCourses']:
            courseInfo = plan['course']
            if courseInfo['courseName'].find(courseName) >= 0 or fuzz.ratio(courseInfo['courseName'], courseName) >= 30:
                res.append(courseInfo)
        for public in dataBk['publicCourses']:
            courseInfo = public['course']
            if courseInfo['courseName'].find(courseName) >= 0 or fuzz.ratio(courseInfo['courseName'], courseName) >= 30:
                res.append(courseInfo)
        return res


def login1(username, password, session):
    res = session.get('http://1.tongji.edu.cn:30100/oiosaml/saml/login')
    soup = BeautifulSoup(res.content, 'html.parser')
    res = session.get(soup.meta['content'][6:])
    if res.status_code != 200:
        return False

    res = session.post('https://ids.tongji.edu.cn:8443/nidp/saml2/sso?sid=0&sid=0', data={
        'option': 'credential',
        'Ecom_User_ID': username,
        'Ecom_Password': password
    })
    if res.status_code != 200:
        return False

    res = session.get('https://ids.tongji.edu.cn:8443/nidp/saml2/sso?sid=0')
    if res.status_code != 200:
        return False
    soup = BeautifulSoup(res.content, 'html.parser')
    try:
        res = session.post('http://1.tongji.edu.cn:30100/oiosaml/saml/SAMLAssertionConsumer',
                           data={'SAMLResponse': soup.input['value']})
    except TypeError:
        return False
    if res.status_code != 200:
        return False
    return dict(parse_qsl(urlsplit(res.url).query))  # 参数返回


def chooseCourseAndClass(xuankewang: xuanke1):
    inputline = input('请输入课程名/课程代码(6位)/班级代码(8位): ')
    if len(inputline) == 6 or len(inputline) == 8:
        try:
            int(inputline)
            isCode = True
        except ValueError:
            isCode = False
    else:
        isCode = False

    if isCode:
        courseInfo = xuankewang.findCourseInfoByCode(inputline[:6])
        if not courseInfo:
            print('找不到课号为', inputline, '的课程')
            return {}
    else:
        courseInfoList = xuankewang.findAllCourseInfoListByName(
            inputline)
        if not courseInfoList:
            print('找不到名字为', inputline, '的课程')
            return {}
        for index, courseInfo in enumerate(courseInfoList):
            print(index, '->',  courseInfo['courseName'],
                  courseInfo['campus'], courseInfo['remark'])
        index = int(input('选择课程序号(-1取消): '))
        if index == -1:
            return {}
        courseInfo = courseInfoList[index]

    courseCode = courseInfo['courseCode']
    _, classInfoList = xuankewang.getTeachClass4Limit(courseCode)

    if isCode and len(inputline) == 8:
        classInfo = [
            eachClass for eachClass in classInfoList if eachClass['teachClassCode'] == inputline][0]
    else:
        for classInfo in classInfoList:
            print(classInfo['teachClassCode'], '->',  classInfo['campusI18n'],
                  classInfo['teacherName'], classInfo['remark'],
                  [time['timeAndRoom'] for time in classInfo['timeTableList']])
        teachClassCode = input('请输入你想选的班级的序号: ')
        classInfo = [
            eachClass for eachClass in classInfoList if eachClass['teachClassCode'] == teachClassCode][0]

    print('您选择了<<%s>> <<%s>>老师的<<%s>>' % (classInfo['campusI18n'],
                                          classInfo['teacherName'], classInfo['courseName']))
    print('请仔细检查选课要求 ->', classInfo['remark'])
    print('和课程时间 ->', [time['timeAndRoom']
                       for time in classInfo['timeTableList']])
    print('**确保课程不会冲突**')
    return classInfo


def chooseCalandarId(xuankewang: xuanke1):
    code, schoolCalendar = xuankewang.schoolCalendar()
    if code != 200:
        print(code, schoolCalendar)
        return ''
    for term in schoolCalendar:
        print(term['id'], '->', term['fullName'])
    termId = input('输入学期编号: ')
    if not termId:
        print('使用当前学期')
        code, calendarInfo = xuankewang.currentTermCalendar()
        if code != 200:
            print(code, calendarInfo)
            return ''
        termId = calendarInfo['schoolCalendar']['id']
    return termId


def main():
    logging.basicConfig(filename='1xuanke.log', level=logging.INFO)
    logging.info(['Running at', timestamp()])

    xuankewang = xuanke1()

    wishList = []
    withdrawList = []
    electTimePeriod = 1
    checkTimePeriod = 0.5
    errorTimePeriod = 1

    print('**输入help查看提示信息')

    while True:
        if not xuankewang.isLogin:
            print('*当前处于未登录状态, 输入"l"或"login"登录')
        if not xuankewang.roundId:
            print('*未指定选课轮次, 输入"r"或"round"选择')
        if wishList:
            print('当前抢课列表: ')
            for index, courseReq in enumerate(wishList):
                print(index, '->', courseReq['teachClassCode'],
                      courseReq['courseName'], courseReq['teacherName'])
        if withdrawList:
            print('当前退课列表: ')
            for index, courseReq in enumerate(withdrawList):
                print(index, '->', courseReq['teachClassCode'],
                      courseReq['courseName'], courseReq['teacherName'])

        opList = input('>>> ').split()
        opCount = len(opList)
        op = opCount and opList[0]

        if op == 'table':
            termId = opCount > 1 and opList[1] or chooseCalandarId(xuankewang)
            uid = opCount > 2 and opList[2] or input(
                '输入学号: ') or xuankewang.uid
            code, myTimeTab = xuankewang.findStudentTimetab(termId, uid)
            if code != 200:
                print(code, myTimeTab)
                continue
            totalCourseCount = 0
            totalCredits = 0
            for course in myTimeTab:
                totalCourseCount += 1
                totalCredits += float(course['credits'])
                print(course['courseName'], course['teacherName'], course['credits'],
                      course['classRoomI18n'], course['classTime'], course['remark'])
            print('一共', totalCourseCount, '门课', totalCredits, '学分')
        elif op == 'info':
            uidList = opCount > 1 and opList[1:] or [input(
                '输入学号: ')]
            if not uidList[0]:
                uidList = [xuankewang.uid]
            for uid in uidList:
                if uid.find('-') != -1:
                    uidRange = uid.split('-')
                    for uidIt in range(int(uidRange[0]), int(uidRange[1])):
                        uidIt = str(uidIt)
                        _, info = xuankewang.findUserInfoByIdType(uidIt)
                        print(info['studentId'], info['name'], info['sexI18n'])
                        print(info['facultyI18n'], info['professionI18n'],
                              info['grade'],  info['trainingLevelI18n'])
                        print('导师: ', info['teacherName'])
                        time.sleep(0.05)
                else:
                    _, info = xuankewang.findUserInfoByIdType(uid)
                    print(info['studentId'], info['name'], info['sexI18n'])
                    print(info['facultyI18n'], info['professionI18n'],
                          info['grade'],  info['trainingLevelI18n'])
                    print('导师: ', info['teacherName'])

        elif op == 'msg':
            _, res = xuankewang.findHomePageCommonMsgPublish()
            for msg in res['list']:
                print('面向群体: ', msg['faceUserName'])
                print('标题: ', msg['title'])
                soup = BeautifulSoup(msg['content'], 'html.parser')
                print(soup.get_text(strip=True))
        elif op == 'course':
            majorCode = opCount > 1 and opList[1] or input('输入专业代码: ')
            grade = opCount > 2 and opList[2] or input('输入年级: ')
            calendarId = opCount > 3 and opList[3] or chooseCalandarId(
                xuankewang)
            _, courseList = xuankewang.getMajorCourseList(
                majorCode, grade, calendarId)
            for course in courseList:
                print(course['value'])
        elif op == 'major':
            grade = opCount > 1 and opList[1] or input('输入年级: ')
            keyWord = opCount > 2 and opList[2] or input('输入学院名称: ')
            _, data = xuankewang.findCampusProfessionList(
                grade, keyWord)
            for majorInfo in data['list']:
                print(majorInfo['professionCode'], majorInfo['professionName'],
                      majorInfo['professionNameEn'], majorInfo['facultyI18n'])
        elif op == 'tutor':
            _, data = xuankewang.myTutor()
            print(data['teacherName'], data['introduce'])

        elif op == 'a' or op == 'add':
            classInfo = chooseCourseAndClass(xuankewang)
            if classInfo:
                wishList.append({
                    'courseCode': classInfo['courseCode'],  # 课程编号
                    'courseName': classInfo['courseName'],  # 课程名
                    'teachClassCode': classInfo['teachClassCode'],  # 班级编号
                    'teachClassId': classInfo['teachClassId'],  # 班级ID
                    'teacherName': classInfo['teacherName']  # 教师名
                })
        elif op == 'wa' or op == 'wadd':
            classInfo = chooseCourseAndClass(xuankewang)
            if classInfo:
                withdrawList.append({
                    'courseCode': classInfo['courseCode'],  # 课程编号
                    'courseName': classInfo['courseName'],  # 课程名
                    'teachClassCode': classInfo['teachClassCode'],  # 班级编号
                    'teachClassId': classInfo['teachClassId'],  # 班级ID
                    'teacherName': classInfo['teacherName']  # 教师名
                })

        elif op == 'd' or op == 'delete':
            index = opCount > 1 and int(opList[1]) or int(
                input('选择要删除的课程序号(-1取消): '))
            if 0 <= index < len(wishList):
                wishList.pop(index)
        elif op == 'wd' or op == 'wdelete':
            index = opCount > 1 and int(opList[1]) or int(
                input('选择要删除的课程序号(-1取消): '))
            if 0 <= index < len(withdrawList):
                withdrawList.pop(index)

        elif op == 'e' or op == 'export':
            filename = opCount > 1 and opList[1] or input(
                '输入导出文件名: ') or 'wishList.json'
            with open(filename, mode='w') as f:
                json.dump(
                    {'wishList': wishList, 'withdrawList': withdrawList}, f)
            print('导出完毕')
        elif op == 'i' or op == 'import':
            filename = opCount > 1 and opList[1] or input(
                '输入导入文件名: ') or 'wishList.json'
            with open(filename, mode='r') as f:
                list = json.load(f)
                wishList = list['wishList']
                withdrawList = list['withdrawList']
            print('导入完毕')

        elif op == 's' or op == 'start':
            try:
                tryElectTimes = 0  # 选课请求次数
                while len(wishList):
                    successCoursesList = []
                    tryElectTimes += 1
                    print(tryElectTimes)
                    code, msg = xuankewang.elect(wishList, withdrawList)
                    if code != 200:
                        code, msg = xuankewang.loginCheck()
                        if code == 200 and type(msg) == dict and msg['status'] == 'Init':
                            pass
                        elif code == 502:
                            time.sleep(5)
                            continue
                        else:
                            logging.error('登录失效')
                            xuankewang.login()

                        tryLoadingTimes = 0
                        while tryLoadingTimes < 5:
                            tryLoadingTimes += 1
                            code, data = xuankewang.loading()
                            if code == 200:
                                if data['status'] == 'Ready':
                                    break
                                elif data['status'] == 'Init' or data['status'] == 'Loading':
                                    xuankewang.loading()
                            time.sleep(1)
                        time.sleep(errorTimePeriod)
                        continue
                    tryGetStatusTimes = 0
                    while tryGetStatusTimes < 5:  # 最多查询次数
                        tryGetStatusTimes += 1
                        code, electRes = xuankewang.electRes()
                        if code == 200:
                            print(tryGetStatusTimes, electRes['status'])
                            if electRes['status'] == 'Ready':
                                successCoursesList = electRes['successCourses']
                                if successCoursesList:
                                    newList = []
                                    for courseReq in wishList:
                                        if courseReq['teachClassId'] in successCoursesList:
                                            print(courseReq['teachClassCode'],
                                                  courseReq['courseName'], courseReq['teacherName'], '选课成功')
                                        else:
                                            newList.append(courseReq)
                                    wishList = newList[:]
                                    newList = []
                                    for courseReq in withdrawList:
                                        if courseReq['teachClassId'] in successCoursesList:
                                            print(courseReq['teachClassCode'],
                                                  courseReq['courseName'], courseReq['teacherName'], '退课成功')
                                        else:
                                            newList.append(courseReq)
                                    withdrawList = newList[:]
                                if electRes['failedReasons']:
                                    print(electRes['failedReasons'])
                                break
                        time.sleep(checkTimePeriod)
                    # while tryGetStatusTimes < 5
                    time.sleep(electTimePeriod)
                # while len(wishList)
            except KeyboardInterrupt:
                print('检测到键盘终止')
        elif op == 'q' or op == 'quit':
            print('GoodBye')
            break

        elif op == 'l' or op == 'login':
            uid = opCount > 1 and opList[1] or input('请输入学号: ')
            key = opCount > 2 and opList[2] or input('请输入密码: ')
            code, res = xuankewang.login(uid, key)
            if code == 200:
                print('登录成功')
            else:
                print(res)
        elif op == 'r' or op == 'round':
            xuankewang.roundId = opCount > 1 and opList[1]
            if not xuankewang.roundId:
                code, roundInfoList = xuankewang.getRounds()
                if code != 200 or len(roundInfoList) == 0:
                    inputId = input('获取选课轮次失败, 可以手动输入选课轮次ID: ')
                    if inputId:
                        xuankewang.roundId = int(inputId)  # 4973
                elif len(roundInfoList) == 1 and op == 'r':
                    roundInfo = roundInfoList[0]
                    xuankewang.roundId = roundInfo['id']
                else:
                    for roundInfo in roundInfoList:
                        print(roundInfo['id'], '->',
                              roundInfo['calendarName'], roundInfo['name'])
                        # print('remark =', roundInfo['remark'])
                    xuankewang.roundId = int(input('请选择选课轮次ID: '))
            print('RoundId ->', xuankewang.roundId)
            xuankewang.getDataBk()  # 刷新一次课程数据

        elif op == 't' or op == 'time':
            inputTime = opCount > 1 and opList[1] or input('输入选课请求间隔: ')
            if inputTime:
                electTimePeriod = float(inputTime)
                print('选课间隔设置为', electTimePeriod)
        elif op == 'tt' or op == 'ttime':
            inputTime = opCount > 1 and opList[1] or input('输入轮询请求间隔: ')
            if inputTime:
                checkTimePeriod = float(inputTime)
                print('轮询请求间隔设置为', checkTimePeriod)

        else:
            print('未知操作 ->', op)
            print('l|login  [uid] [password]    -> 登录')
            print('r|round  [roundId]           -> 选择选课轮次')
            print('msg                          -> 获取 1.tongji 上的通知')
            print('info     [uid|uid1-uid2]     -> 查询学生信息')
            print('tutor                        -> 查询我的导师')
            print('major    [grade] [keyWord]   -> 查询开设专业信息')
            print('course   [majorCode] [grade] [calandarId] -> 查询专业课表')
            print('table    [calandarId] [uid]  -> 查看课表')
            print('a|add                        -> 添加要抢的课')
            print('d|delete [index]             -> 删除要抢的课')
            print('wa|wadd                      -> 添加要退的课')
            print('wd|wdelete [index]           -> 删除要退的课')
            print('e|export [fileName]          -> 导出抢/退课列表')
            print('i|import [fileName]          -> 导入抢/退课列表')
            print('s|start                      -> 开始抢课')
            print('q|quit                       -> 退出')
            print('*                            -> 显示此提示信息')
            continue


if __name__ == '__main__':
    main()
