from HCNetSDK import *
from PlayCtrl import *
import time

nPort = C_LONG(-1)

class devClass:
    def __init__(self):
        self.hikSDK, self.playM4SDK = self.LoadSDK()  # 加载sdk库
        self.iUserID = -1  # 登录句柄
        self.lRealPlayHandle = -1  # 预览句柄
        self.wincv = None  # windows环境下的参数
        self.win = None  # 预览窗口
        self.FuncDecCB = None  # 解码回调
        self.PlayCtrlPort = C_LONG(-1)  # 播放通道号
        self.basePath = ''  # 基础路径
        self.preview_file = ''  # linux预览取流保存路径

    def LoadSDK(self):
        hikSDK = None
        playM4SDK = None
        try:
            print("netsdkdllpath: ", netsdkdllpath)
            hikSDK = load_library(netsdkdllpath)
            playM4SDK = load_library(playM4dllpath)
        except OSError as e:
            print('动态库加载失败', e)
        return hikSDK, playM4SDK

    # 设置SDK初始化依赖库路径
    def SetSDKInitCfg(self):
        # 设置HCNetSDKCom组件库和SSL库加载路径
        if sys_platform == 'windows':
            basePath = os.getcwd().encode('gbk')
            strPath = basePath + b'\lib'
            sdk_ComPath = NET_DVR_LOCAL_SDK_PATH()
            sdk_ComPath.sPath = strPath
            print('strPath: ', strPath)
            if self.hikSDK.NET_DVR_SetSDKInitCfg(NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_SDK_PATH.value,
                                                 byref(sdk_ComPath)):
                print('NET_DVR_SetSDKInitCfg: 2 Succ')
            if self.hikSDK.NET_DVR_SetSDKInitCfg(NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_LIBEAY_PATH.value,
                                                 create_string_buffer(strPath + b'\libcrypto-1_1-x64.dll')):
                print('NET_DVR_SetSDKInitCfg: 3 Succ')
            if self.hikSDK.NET_DVR_SetSDKInitCfg(NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_SSLEAY_PATH.value,
                                                 create_string_buffer(strPath + b'\libssl-1_1-x64.dll')):
                print('NET_DVR_SetSDKInitCfg: 4 Succ')
        else:
            basePath = os.getcwd().encode('utf-8')
            strPath = basePath + b'\lib'
            sdk_ComPath = NET_DVR_LOCAL_SDK_PATH()
            sdk_ComPath.sPath = strPath
            if self.hikSDK.NET_DVR_SetSDKInitCfg(NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_SDK_PATH.value,
                                                 byref(sdk_ComPath)):
                print('NET_DVR_SetSDKInitCfg: 2 Succ')
            if self.hikSDK.NET_DVR_SetSDKInitCfg(NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_LIBEAY_PATH.value,
                                                 create_string_buffer(strPath + b'/libcrypto.so.1.1')):
                print('NET_DVR_SetSDKInitCfg: 3 Succ')
            if self.hikSDK.NET_DVR_SetSDKInitCfg(NET_SDK_INIT_CFG_TYPE.NET_SDK_INIT_CFG_SSLEAY_PATH.value,
                                                 create_string_buffer(strPath + b'/libssl.so.1.1')):
                print('NET_DVR_SetSDKInitCfg: 4 Succ')
        self.basePath = basePath

    # 通用设置，日志/回调事件类型等
    def GeneralSetting(self):

        # 日志的等级（默认为0）：0-表示关闭日志，1-表示只输出ERROR错误日志，2-输出ERROR错误信息和DEBUG调试信息，3-输出ERROR错误信息、DEBUG调试信息和INFO普通信息等所有信息
        # self.hikSDK.NET_DVR_SetLogToFile(3, b'./SdkLog_Python/', False)
        self.hikSDK.NET_DVR_SetLogToFile(3, bytes('./SdkLog_Python/', encoding="utf-8"), False)

    def Init(self):
        self.SetSDKInitCfg()  # 设置SDK初始化依赖库路径
        self.hikSDK.NET_DVR_Init()  # 初始化sdk
        self.GeneralSetting()  # 通用设置，日志，回调函数等

    # 登录设备
    def LoginDev(self, ip, username, pwd):
        # 登录参数，包括设备地址、登录用户、密码等
        struLoginInfo = NET_DVR_USER_LOGIN_INFO()
        struLoginInfo.bUseAsynLogin = 0  # 同步登录方式y
        struLoginInfo.sDeviceAddress = ip  # 设备IP地址
        struLoginInfo.wPort = 8000  # 设备服务端口
        struLoginInfo.sUserName = username  # 设备登录用户名
        struLoginInfo.sPassword = pwd  # 设备登录密码
        struLoginInfo.byLoginMode = 0

        # 设备信息, 输出参数
        struDeviceInfoV40 = NET_DVR_DEVICEINFO_V40()
        # 登录设备，最多尝试登录10次
        cnt = 10
        while cnt:
            self.iUserID = self.hikSDK.NET_DVR_Login_V40(byref(struLoginInfo), byref(struDeviceInfoV40))
            if self.iUserID < 0:
                print("登录失败，错误码: %d" % self.hikSDK.NET_DVR_GetLastError())
                print('尝试再次登录...')
                time.sleep(1)
            else:
                print('登录成功，设备序列号：%s' % str(struDeviceInfoV40.struDeviceV30.sSerialNumber, encoding="utf8").rstrip('\x00'))
                return
            cnt -= 1
        self.hikSDK.NET_DVR_Cleanup()

    # 登出设备
    def LogoutDev(self):
        if self.iUserID > -1:
            # 撤销布防，退出程序时调用
            self.hikSDK.NET_DVR_Logout(self.iUserID)


    # 将视频流保存到本地
    def writeFile(self, filePath, pBuffer, dwBufSize):
        # 使用memmove函数将指针数据读到数组中
        data_array = (c_byte * dwBufSize)()
        memmove(data_array, pBuffer, dwBufSize)

        # 判断文件路径是否存在
        if not os.path.exists(filePath):
            # 如果不存在，使用 open() 函数创建一个空文件
            open(filePath, "w").close()

        preview_file_output = open(filePath, 'ab')
        preview_file_output.write(data_array)
        preview_file_output.close()


    def stopPlay(self):
        # 关闭预览
        self.hikSDK.NET_DVR_StopRealPlay(self.lRealPlayHandle)

        # 停止解码，释放播放库资源
        if self.PlayCtrlPort.value > -1:
            self.playM4SDK.PlayM4_Stop(self.PlayCtrlPort)
            self.playM4SDK.PlayM4_CloseStream(self.PlayCtrlPort)
            self.playM4SDK.PlayM4_FreePort(self.PlayCtrlPort)
            self.PlayCtrlPort = C_LONG(-1)
        # 登出设备
        self.hikSDK.NET_DVR_Logout(self.iUserID)
        # 释放资源
        self.hikSDK.NET_DVR_Cleanup()
