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
    redirect_link = "https://mp.weixin.qq.com/s/k03Gw_7aKoAKrJZlz7fXzg"
    def __init__(self):
        super().__init__()
        try:
            self.config = super().load_config()
            if not self.config:
                self.config = self._load_config_template()
            self.group_welc_fixed_msg = self.config.get("group_welc_fixed_msg", {})
            self.group_welc_prompt = self.config.get("group_welc_prompt", self.group_welc_prompt)
            self.group_exit_prompt = self.config.get("group_exit_prompt", self.group_exit_prompt)
            self.patpat_prompt = self.config.get("patpat_prompt", self.patpat_prompt)
            self.redirect_link = self.config.get("redirect_link", self.redirect_link)
            self.appid = conf().get("gewechat_app_id", "")
            self.gewetk = conf().get("gewechat_token", "")
            self.base_url = conf().get("gewechat_base_url")
            self.headers = {
                'X-GEWE-TOKEN': self.gewetk,
                'Content-Type': 'application/json'
            }
            logger.info("[HelloPlus] inited")
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        except Exception as e:
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
                qm,imgurl=self.get_info(msg)
                if qm!=None or imgurl!=None:
                    self.welcome(msg,qm,imgurl)
                    e_context.action = EventAction.BREAK  # 事件结束，并跳过处理context的默认逻辑
                    return
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
        url = f"{self.base_url}/message/postAppMsg"
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
        response = requests.request("POST", url, data=payload, headers=self.headers)
    
    def get_info(self,msg):
        import requests
        import json
        wxid=self.get_list(msg)
        if wxid==None:
            return None
        payload = json.dumps({
            "appId": self.appid,
            "chatroomId": msg.other_user_id,
            "memberWxids": [
               wxid
            ]
        })
        data=requests.request("POST", f"{self.base_url}/group/getChatroomMemberDetail", data=payload, headers=self.headers).json()
        return data["data"][0]["signature"],data["data"][0]["smallHeadImgUrl"]
    def get_list(self,msg):
        import requests
        import json
        payload = json.dumps({
           "appId": self.appid,
            "chatroomId": msg.other_user_id,
        })
        
        data=requests.request("POST", f"{self.base_url}/group/getChatroomMemberList", data=payload, headers=self.headers).json()
        wxid=None
        for member in data["data"]["memberList"]:
            if member["nickName"] == msg.actual_user_nickname:
                wxid=member["wxid"]

        return wxid  