# -*- coding: utf8 -*-
import json
import requests
import leancloud
import logging

# leancloud的应用Keys
LEANCLOUD_APPID = 'YOURS APPID'
LEANCLOUD_APPKEY = 'YOURS APPKEY'
LEANCLOUD_CLASS = 'YOURS CLASS'
PP_TOKEN='YOURS PUSHPLUS TOKEN'

#设置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Leancloud_DB:
    # 初始化leancloud
    def __init__(self,leancloud_AppID,leancloud_AppKey):
        leancloud.init(leancloud_AppID,leancloud_AppKey)
    
        self.live = leancloud.Object.extend(LEANCLOUD_CLASS)
        self.query = self.live.query

    # 得到数据
    def GetDB(self,leancloud_objectId):
        
        db_list = []
        item = self.query.get(leancloud_objectId)
        #状态
        status = item.get('status')
        #直播间ID
        liveID = item.get('liveID')
        # 获取内置属性
        object_id  = item.id
        update_at  = item.updated_at
        created_at = item.created_at

        db_list.append(object_id)
        db_list.append(liveID)
        db_list.append(status)
        db_list.append(created_at)
        db_list.append(update_at)

        return db_list

    # 设置数据
    def SetDB(self,leancloud_objectId,status):
        item = self.query.get(leancloud_objectId)
        
        item.set('status',status)
        item.save()

def GetLiveStatus(live_id:str):
    '''
    :通过url获取json字典信息判断是否直播
    :param: live_id: 直播间ID str类型
    :return: 返回是否直播
    '''
    headers = {
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
    }

    url = 'https://apiv2.douyucdn.cn/japi/search/api/getSearchRec?kw=%s&tagTest=a&client_sys=android'%(live_id)
    
    response = requests.get(url=url,headers=headers)
    response.raise_for_status()
    result_dic = response.json()
    data_list = result_dic['data']['recList']

    for data in data_list:
        id = data['roomInfo']['rid']
        if data['roomInfo']['rid'] == int(live_id):
            is_live = data['roomInfo']['isLive']
            if is_live == 1:
                return True
            else:
                return False
        else:
            return None

def PushPlus(data:str):
    '''
    :通过PushPlus发送消息
    :param:data
    '''
    token = PP_TOKEN  #在pushplus网站中可以找到
    title= '直播消息'  #改成你要的标题内容
    content = data   #改成你要的正文内容
    url = 'http://pushplus.hxtrip.com/send?token='+token+'&title='+title+'&content='+content
    requests.get(url)

def MonitorStatus(live_id:str,leancloud_objectId):
    '''
    :监测直播状态
    :param:live_id 房间号
    :param:leancloud_objectId
    '''
    db = Leancloud_DB(LEANCLOUD_APPID,LEANCLOUD_APPKEY)
    db_status_list = db.GetDB(leancloud_objectId)
    old_status = db_status_list[2]
    logger.info('** 原先 %s 的直播状态为 %s **'%(live_id,old_status))

    if old_status == False:
        try:
            res = GetLiveStatus(live_id)
            if res == True:
                logger.info('上班 %s 直播开始'%live_id)
                # 数据库操作
                db.SetDB(leancloud_objectId,res)
                # 发送消息
                data = live_id + ':正在直播'
                PushPlus(data)
                return True,res

            elif res == False:
                logger.info('直播 %s 没有开始'%live_id)
                return False,res
            else:
                logger.warning('数据 %s 爬取失败'%live_id)
                return False,res
        
        except Exception as e:
            logger.warning(e)
            return False,res

    else:
        try:
            res = GetLiveStatus(live_id)
            if res == False:
                logger.info('下班 %s 直播结束'%live_id)
                #数据库操作
                db.SetDB(leancloud_objectId,res)
                return True,res

            elif res == True:
                logger.info('直播 %s 进行ing'%live_id)
                return False,res
                
            else:
                logger.warning('数据 %s 爬取失败'%live_id)
                return False,res
        
        except Exception as e:
            logger.warning(e)
            return False,res
            
# ('live_id', {'oid': 'YOURS_OID'})

def main_handler(event, context):

    """
    云函数处理
    :param event: 定时触发器 -> Message
    :return:
    """
    if event and 'Message' in event:
        try:
            data = json.loads(event['Message'].strip())
        except Exception as e:
            raise Exception('触发器格式不正确', e)
        else:
            for item in data.items():
                live_id = str(item[0])
                oid = str(item[1]['oid'])
                res = MonitorStatus(live_id,oid)
                print('*******')
                print("current status: ", res[1])

    else:
        raise Exception('请配置触发器参数')