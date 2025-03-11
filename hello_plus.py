# encoding:utf-8

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
from common.log import logger
from plugins import *
from config import conf


@plugins.register(
    name="HelloPlus",
    desire_priority=1,
    hidden=True,
    desc="欢迎plus版",
    version="0.1",
    author="wangcl",
)


class HelloPlus(Plugin):

    group_welc_prompt = "请你随机使用一种风格说一句问候语来欢迎新用户\"{nickname}\"加入群聊。"
    group_exit_prompt = "请你随机使用一种风格介绍你自己，并告诉用户输入#help可以查看帮助信息。"
    patpat_prompt = "请你随机使用一种风格跟其他群用户说他违反规则\"{nickname}\"退出群聊。"
    exit_url="https://baike.baidu.com/item/%E9%80%80%E5%87%BA/28909"
    redirect_link = "https://baike.baidu.com/item/welcome/2135227"
    say_exit = "有缘再见"
    sleep_time = 60
    welc_text = False
    auth_token = "12345679"
    admin_user = set()
    def __init__(self):
        super().__init__()
        try:
            self.config = super().load_config()
            if not self.config:
                self.config = self._load_config_template()
            self.group_welc_fixed_msg = self.config.get("group_welc_fixed_msg", {})
            self.group_welc_prompt = self.config.get("group_welc_prompt", self.group_welc_prompt)
            self.group_exit_prompt = self.config.get("group_exit_prompt", self.group_exit_prompt)
            self.group_exit_prompt_str="\"{nickname}\"退出群聊。请你随机使用一种风格跟他说再见。"
            self.patpat_prompt = self.config.get("patpat_prompt", self.patpat_prompt)
            self.redirect_link = self.config.get("redirect_link", self.redirect_link)
            self.exit_url = self.config.get("exit_url", self.exit_url)
            self.say_exit = self.config.get("say_exit", self.say_exit)
            self.sleep_time=self.config.get("sleep_time", self.sleep_time)
            self.auth_token=self.config.get("auth_token", self.auth_token)
            self.welc_text=self.config.get("welc_text", self.welc_text)
            self.appid = conf().get("gewechat_app_id", "")
            self.gewetk = conf().get("gewechat_token", "")
            self.base_url = conf().get("gewechat_base_url")
            self.group_members={}
            self.memberList = []
            self.admin_user = []
            self.monitor_threads = {}  # 存储监控线程
            self.monitoring_groups = set()  # 存储正在监控的群组ID
            self.monitoring_groups_name = {}  # 存储正在监控的群组name
            self.headers = {
                'X-GEWE-TOKEN': self.gewetk,
                'Content-Type': 'application/json'
            }
            logger.info("[HelloPlus] inited")
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        except Exception as e:
            print(f"[HelloPlus]初始化异常-----：{e}")
            logger.error(f"[HelloPlus]初始化异常：{e}")
            raise "[HelloPlus] init failed, ignore "

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT,
            ContextType.JOIN_GROUP,
            ContextType.PATPAT,
            ContextType.EXIT_GROUP
        ]:
            return
        msg: ChatMessage = e_context["context"]["msg"]
        group_name = msg.from_user_nickname
        if e_context["context"].type == ContextType.JOIN_GROUP:
            if "group_welcome_msg" in conf() or group_name in self.group_welc_fixed_msg:
                
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    if group_name in self.group_welc_fixed_msg:
                        reply.content = self.group_welc_fixed_msg.get(group_name, "")
                    else:
                        reply.content = conf().get("group_welcome_msg", "")
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
                    return
            print('----welcome----')
            try:
                import time
                time.sleep(2)
                qm,imgurl,nickName=self.get_info(msg.other_user_id,msg.actual_user_nickname)
                if qm!=None or imgurl!=None:
                    ret=self.welcome(msg,qm,imgurl)
                    if ret!= 200:
                        e_context["context"].type = ContextType.TEXT
                        e_context["context"].content = self.group_welc_prompt.format(nickname=msg.actual_user_nickname)
                        e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
                    if self.welc_text:
                        time.sleep(2)
                        e_context["context"].type = ContextType.TEXT
                        e_context["context"].content = self.group_welc_prompt.format(nickname=msg.actual_user_nickname)
                        e_context.action = EventAction.BREAK
                else:
                    e_context["context"].type = ContextType.TEXT
                    e_context["context"].content = self.group_welc_prompt.format(nickname=msg.actual_user_nickname)
                    e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
            except:
                e_context["context"].type = ContextType.TEXT
                e_context["context"].content = self.group_welc_prompt.format(nickname=msg.actual_user_nickname)
                e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
            if not self.config or not self.config.get("use_character_desc"):
                e_context["context"]["generate_breaked_by"] = EventAction.BREAK
            return
        
        if e_context["context"].type == ContextType.EXIT_GROUP:
            
            if "group_exit_msg" in conf():
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = conf().get("group_exit_msg", "")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
                return
            if conf().get("group_chat_exit_group"):
                e_context["context"].type = ContextType.TEXT
                e_context["context"].content = self.group_exit_prompt.format(nickname=msg.actual_user_nickname)
                e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
                return
            e_context.action = EventAction.BREAK
            return
            
        if e_context["context"].type == ContextType.PATPAT:
            e_context["context"].type = ContextType.TEXT
            e_context["context"].content = self.patpat_prompt
            e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑
            if not self.config or not self.config.get("use_character_desc"):
                e_context["context"]["generate_breaked_by"] = EventAction.BREAK
            return

        content = e_context["context"].content
        logger.debug("[Hello] on_handle_context. content: %s" % content)
        if content == "Hello":
            reply = Reply()
            reply.type = ReplyType.TEXT
            if e_context["context"]["isgroup"]:
                reply.content = f"Hello, {msg.actual_user_nickname} from {msg.from_user_nickname}"
            else:
                reply.content = f"Hello, {msg.from_user_nickname}"
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
        user_id=msg.actual_user_id
        if content.startswith('群监控管理验证'):
            if e_context["context"]["isgroup"]:
                reply_cont="不支持群聊验证"
                reply = self.create_reply(ReplyType.TEXT, reply_cont)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS 
                return
            tk = content[7:].strip()
            reply_cont="验证成功,已将您设为群监控管理员。" if self.add_admin_user(tk,user_id) else "验证失败"
            reply = self.create_reply(ReplyType.TEXT, reply_cont)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS 
        if e_context["context"]["isgroup"]:
            if content =='查看监控群列表':
                if not self.is_admin(user_id):
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    reply.content = "没权限啊"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                # 获取监控群列表
                # 从self.group_members获取每个群的成员数量
                group_member_count = {}
                for group_id, members in self.group_members.items():
                    group_member_count[group_id] = len(members)
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = "监控群列表：\n"
                for group_id in self.monitoring_groups:
                    reply.content += f" 💬{self.monitoring_groups_name[group_id]} -🙎‍♂️当前成员： {group_member_count[group_id]}人\n"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            if content =='开启退群监控':
                if not self.is_admin(user_id):
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    reply.content = "没权限啊"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                self.get_member_list(msg)
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = f"当前群[{msg.other_user_nickname}]已开启退群监控"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            if content == "关闭退群监控":
                if not self.is_admin(user_id):
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    reply.content = "没权限啊"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                group_id = msg.other_user_id
                if group_id in self.monitoring_groups:
                    self.monitoring_groups.remove(group_id)
                    self.monitoring_groups_name.pop(group_id)
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    reply.content = f"当前群[{msg.other_user_nickname}]已关闭退群监控"
                    e_context["reply"] = reply
                else:
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    reply.content = "当前群未开启退群监控"
                    e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
        if content == "Hi":
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = "Hi"
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑，一般会覆写reply

        if content == "End":
            # 如果是文本消息"End"，将请求转换成"IMAGE_CREATE"，并将content设置为"The World"
            e_context["context"].type = ContextType.IMAGE_CREATE
            content = "The World"
            e_context.action = EventAction.CONTINUE  # 事件继续，交付给下个插件或默认逻辑

    def get_help_text(self, **kwargs):
        help_text = "输入Hello，我会回复你的名字\n输入End，我会回复你世界的图片\n"
        return help_text

    def _load_config_template(self):
        logger.debug("No Hello plugin config.json, use plugins/hello/config.json.template")
        try:
            plugin_config_path = os.path.join(self.path, "config.json.template")
            if os.path.exists(plugin_config_path):
                with open(plugin_config_path, "r", encoding="utf-8") as f:
                    plugin_conf = json.load(f)
                    return plugin_conf
        except Exception as e:
            logger.exception(e)
    def welcome(self,msg,qm,imgurl):
        import requests
        import json
        from datetime import datetime
        post_url = f"{self.base_url}/message/postAppMsg"
        now = datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒")
        url=self.redirect_link
        payload = json.dumps({
           "appId": self.appid,
           "toWxid": msg.other_user_id,
           "appmsg": (
               f'<appmsg appid="" sdkver="1">'
               f'<title>👏欢迎 {msg.actual_user_nickname} 加入群聊！🎉</title>'
               f'<des>⌚：{now}\n签名：{qm if qm else "这个人没有签名"}</des>'
               f'<action>view</action><type>5</type><showtype>0</showtype><content />'
               f'<url>{url}</url>'
               f'<dataurl /><lowurl /><lowdataurl /><recorditem />'
               f'<thumburl>{imgurl}</thumburl>'
               '<messageaction /><laninfo /><extinfo /><sourceusername /><sourcedisplayname />'
               '<commenturl /><appattach><totallen>0</totallen><attachid />'
               '<emoticonmd5></emoticonmd5><fileext /><aeskey></aeskey></appattach>'
               '<webviewshared><publisherId /><publisherReqId>0</publisherReqId></webviewshared>'
               '<weappinfo><pagepath /><username /><appid /><appservicetype>0</appservicetype>'
               '</weappinfo><websearch /></appmsg>'
           )
        })
        response = requests.request("POST", post_url, data=payload, headers=self.headers)

        return response.json()['ret']
    def exit(self,group_id,imgurl,nickName):
        import requests
        import json
        from datetime import datetime
        post_url = f"{self.base_url}/message/postAppMsg"
        now = datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒")
        payload = json.dumps({
           "appId": self.appid,
           "toWxid": group_id,
           "appmsg": (
               f'<appmsg appid="" sdkver="1">'
               f'<title> {nickName} 离开群聊！</title>'
               f'<des>⌚：{now}\n{self.say_exit}</des>'
               f'<action>view</action><type>5</type><showtype>0</showtype><content />'
               f'<url>{self.exit_url}</url>'
               f'<dataurl /><lowurl /><lowdataurl /><recorditem />'
               f'<thumburl>{imgurl}</thumburl>'
               '<messageaction /><laninfo /><extinfo /><sourceusername /><sourcedisplayname />'
               '<commenturl /><appattach><totallen>0</totallen><attachid />'
               '<emoticonmd5></emoticonmd5><fileext /><aeskey></aeskey></appattach>'
               '<webviewshared><publisherId /><publisherReqId>0</publisherReqId></webviewshared>'
               '<weappinfo><pagepath /><username /><appid /><appservicetype>0</appservicetype>'
               '</weappinfo><websearch /></appmsg>'
           )
        })
        response = requests.request("POST", post_url, data=payload, headers=self.headers)

        return response.json()['ret']
    def get_info(self,group_id,nickname):
        import requests
        import json
        print('----get_info----')
        wxid=self.get_list(group_id,nickname)
        if wxid==None:
            return None
        payload = json.dumps({
            "appId": self.appid,
            "chatroomId": group_id,
            "memberWxids": [
               wxid
            ]
        })
        data=requests.request("POST", f"{self.base_url}/group/getChatroomMemberDetail", data=payload, headers=self.headers).json()
        print('----get_info----',data["data"][0]["signature"],data["data"][0]["smallHeadImgUrl"],data["data"][0]["nickName"])
        return data["data"][0]["signature"],data["data"][0]["smallHeadImgUrl"],data["data"][0]["nickName"]
    def get_list(self,group_id,nickname):
        print('----get_list----')
        print('----group_id----',group_id,nickname)
        import requests
        import json
        payload = json.dumps({
           "appId": self.appid,
            "chatroomId": group_id,
        })
        
        data=requests.request("POST", f"{self.base_url}/group/getChatroomMemberList", data=payload, headers=self.headers).json()
        ret=data['ret']
        if ret!=200:
            return None
        wxid=None
       
        for member in data["data"]["memberList"]:
            if member["nickName"] == nickname:
                wxid=member["wxid"]
        print('----get_list----',wxid)
        return wxid  
    def get_member_list(self, msg):
        """
        获取群成员列表并监控退群行为
        Args:
            msg: 消息对象,包含群id等信息
        Returns:
            list: 群成员列表,None表示获取失败
        """
        print('----get_member_list----')
        import requests
        import json
        import time
        import threading
        
        def monitor_group(group_id):
            
            while group_id in self.monitoring_groups:  # 检查监控状态
                try:
                    # 构造请求参数
                    payload = json.dumps({
                        "appId": self.appid,
                        "chatroomId": group_id,
                    })
                    
                    # 请求群成员列表
                    data = requests.request("POST", f"{self.base_url}/group/getChatroomMemberList", 
                                         data=payload, headers=self.headers).json()
                    
                    # 检查请求是否成功
                    if data.get('ret') != 200:
                        continue
                        
                    current_members = data["data"]["memberList"]
                    
                    # 如果是第一次获取,直接保存
                    if group_id not in self.group_members:
                        self.group_members[group_id] = current_members
                    else:
                        # 对比新旧成员列表,找出退群成员
                        old_members = self.group_members[group_id]
                        old_wxids = {m["wxid"] for m in old_members}
                        new_wxids = {m["wxid"] for m in current_members}
                        
                        left_members = old_wxids - new_wxids
                        if left_members:
                            for wxid in left_members:
                                # 找到退群成员昵称
                                member = next(m for m in old_members if m["wxid"] == wxid)
                                print(f"用户 {member['nickName']} 退出了群聊")
                               
                                self.exit(group_id, member['smallHeadImgUrl'],member['nickName'])
                        
                        # 更新本地群成员数据        
                        self.group_members[group_id] = current_members
                    print(f"开始监控群 {group_id}")
                    self.memberList = current_members
                    time.sleep(self.sleep_time)  # 每self.sleep_time
                except Exception as e:
                    print(f"监控群 {group_id} 异常: {e}")
                    if group_id not in self.monitoring_groups:  # 如果已关闭监控则退出
                        break
                    time.sleep(self.sleep_time)
                    continue
            print(f"停止监控群 {group_id}")

        # 如果该群还没有监控线程,则创建新线程
        if msg.other_user_id not in self.monitor_threads:
            self.monitoring_groups.add(msg.other_user_id)  # 添加到监控集合
            self.monitoring_groups_name[msg.other_user_id]=msg.other_user_nickname  # 添加到监控集合
            t = threading.Thread(target=monitor_group, args=(msg.other_user_id,))
            t.daemon = True
            t.start()
            self.monitor_threads[msg.other_user_id] = t
            
        return self.memberList
    def is_admin(self,wxid):
        return wxid in self.admin_user
    def add_admin_user(self,token,wxid):
        if token==self.auth_token:
            print('--**验证成功')
            self.admin_user.append(wxid)
            print(self.admin_user)
            return True
        return False
    def create_reply(self, reply_type, content):
        reply = Reply()
        reply.type = reply_type
        reply.content = content
        return reply
