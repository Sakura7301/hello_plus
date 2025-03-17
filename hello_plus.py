# encoding:utf-8
import time
import requests
import json
from datetime import datetime
import threading
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
    def __init__(self):
        super().__init__()
        self.ql_list = {}
        self.group_members = {}
        self.memberList = []
        self.admin_user = []
        self.monitor_threads = {}  # 存储监控线程
        self.monitoring_groups = set()  # 存储正在监控的群组ID
        self.monitoring_groups_name = {}  # 存储正在监控的群组name
        # 线程名前缀
        self.thread_name_prefix = "HelloPlusThread"
        # 线程计数
        self.thread_num = 0

        try:
            self.config = super().load_config()
            if not self.config:
                self.config = self._load_config_template()

            # 配置参数
            self.group_welc_fixed_msg = self.config.get("group_welc_fixed_msg", {})
            self.group_welc_prompt = self.config.get("group_welc_prompt", "")
            self.group_exit_prompt = self.config.get("group_exit_prompt", "")
            self.patpat_prompt = self.config.get("patpat_prompt", "")
            self.redirect_link = self.config.get("redirect_link", "")
            self.exit_url = self.config.get("exit_url", "")
            self.say_exit = self.config.get("say_exit", "")
            self.sleep_time = self.config.get("sleep_time", 60)
            self.auth_token = self.config.get("auth_token", "admin")
            self.welc_text = self.config.get("welc_text", False)
            self.group_names = self.config.get("group_names", [])

            # 微信相关配置
            self.appid = conf().get("gewechat_app_id", "")
            self.gewetk = conf().get("gewechat_token", "")
            self.base_url = conf().get("gewechat_base_url")
            self.headers = {
                'X-GEWE-TOKEN': self.gewetk,
                'Content-Type': 'application/json'
            }

            # 检查线程是否关闭
            self.check_daemon()

            # 初始化群组列表
            self.check_thread = threading.Thread(target=self.get_group_list, name=self.get_thread_name())
            self.check_thread.daemon = True
            self.check_thread.start()

            logger.info("[HelloPlus] 初始化完成")
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        except Exception as e:
            logger.error(f"[HelloPlus] 初始化异常：{e}")
            raise "[HelloPlus] init failed, ignore "

    def get_thread_name(self):
        # 生成线程名并返回
        thread_name = f"{self.thread_name_prefix}_{self.thread_num}"
        self.thread_num += 1
        return thread_name

    def check_daemon(self):
        # 获取所有活动线程
        for thread in threading.enumerate():
            # 检查线程名
            if "HelloPlusThread_" in thread.name:
                # 回收线程
                logger.warning(f"[HelloPlus] 检测到线程 {thread.name} 未关闭，正在回收...")
                thread._stop()

    def on_handle_context(self, e_context: EventContext):
        """处理上下文事件"""
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
            self.handle_join_group(e_context, msg, group_name)
        elif e_context["context"].type == ContextType.EXIT_GROUP:
            self.handle_exit_group(e_context, msg)
        elif e_context["context"].type == ContextType.PATPAT:
            self.handle_patpat(e_context)
        else:
            self.handle_text_command(e_context, msg)

    def handle_join_group(self, e_context: EventContext, msg: ChatMessage, group_name: str):
        """处理加入群聊事件"""
        if "group_welcome_msg" in conf() or group_name in self.group_welc_fixed_msg:
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = self.group_welc_fixed_msg.get(group_name, conf().get("group_welcome_msg", ""))
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return

        try:
            time.sleep(2)
            qm, imgurl, nickName = self.get_info(msg.other_user_id, msg.actual_user_nickname)
            if qm is not None or imgurl is not None:
                ret = self.welcome(msg, qm, imgurl)
                if ret != 200:
                    self.send_default_welcome_message(e_context, msg)
            else:
                self.send_default_welcome_message(e_context, msg)
        except:
            self.send_default_welcome_message(e_context, msg)

    def handle_exit_group(self, e_context: EventContext, msg: ChatMessage):
        """处理退出群聊事件"""
        if "group_exit_msg" in conf():
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = conf().get("group_exit_msg", "")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return

        if conf().get("group_chat_exit_group"):
            e_context["context"].type = ContextType.TEXT
            e_context["context"].content = self.group_exit_prompt.format(nickname=msg.actual_user_nickname)
            e_context.action = EventAction.BREAK
            return

        e_context.action = EventAction.BREAK

    def handle_patpat(self, e_context: EventContext):
        """处理拍一拍事件"""
        e_context["context"].type = ContextType.TEXT
        e_context["context"].content = self.patpat_prompt
        e_context.action = EventAction.BREAK

    def handle_text_command(self, e_context: EventContext, msg: ChatMessage):
        """处理文本命令"""
        content = e_context["context"].content
        user_id = msg.actual_user_id

        if content.startswith('群监控管理认证'):
            self.handle_admin_verification(e_context, msg, content)
        elif content == '群监控列表':
            self.handle_view_monitoring_groups(e_context, user_id)
        elif content.startswith("开启监控"):
            self.handle_start_monitoring(e_context, user_id, content)
        elif content.startswith("关闭监控"):
            self.handle_stop_monitoring(e_context, user_id, content)

    def handle_admin_verification(self, e_context: EventContext, msg: ChatMessage, content: str):
        """处理管理员验证命令"""
        if e_context["context"]["isgroup"]:
            self.send_reply(e_context, "不支持群聊验证")
            return

        tk = content[7:].strip()
        reply_cont = "验证成功,已将您设为群监控管理员。" if self.add_admin_user(tk, msg.actual_user_id) else "验证失败"
        self.send_reply(e_context, reply_cont)

    def handle_view_monitoring_groups(self, e_context: EventContext, user_id: str):
        """处理群监控列表命令"""
        if not self.monitoring_groups:
            self.send_reply(e_context, "群监控列表为空")
            return

        group_member_count = {group_id: len(members) for group_id, members in self.group_members.items()}
        reply_content = "群监控列表：\n"
        for group_id in self.monitoring_groups:
            reply_content += f" 💬{self.monitoring_groups_name[group_id]} -🙎‍♂️当前成员： {group_member_count.get(group_id, 0)}人\n"
        self.send_reply(e_context, reply_content)

    def handle_start_monitoring(self, e_context: EventContext, user_id: str, content: str):
        """处理开启监控命令"""
        if e_context["context"]["isgroup"]:
            self.send_reply(e_context, "不支持群聊开启")
            return

        if not self.is_admin(user_id):
            self.send_reply(e_context, "没权限啊")
            return

        group_name = content[4:].strip()
        ret, msg = self.start_monitor(group_name)
        self.send_reply(e_context, msg)

    def handle_stop_monitoring(self, e_context: EventContext, user_id: str, content: str):
        """处理关闭监控命令"""
        if e_context["context"]["isgroup"]:
            self.send_reply(e_context, "不支持群聊关闭")
            return

        if not self.is_admin(user_id):
            self.send_reply(e_context, "没权限啊")
            return

        group_name = content[4:].strip()
        flag = True
        for group_id, name in list(self.monitoring_groups_name.items()):
            if name == group_name:
                flag = False
                if group_id in self.monitoring_groups:
                    self.monitoring_groups.remove(group_id)
                    del self.monitoring_groups_name[group_id]
                    self.send_reply(e_context, f"监控关闭成功: {group_name}")
                else:
                    self.send_reply(e_context, f"[{group_name}]未开启退群监控")
                break
        if flag:
            self.send_reply(e_context, f"未找到群组：{group_name}")

    def send_reply(self, e_context: EventContext, content: str):
        """发送回复"""
        reply = Reply()
        reply.type = ReplyType.TEXT
        reply.content = content
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS

    def send_default_welcome_message(self, e_context: EventContext, msg: ChatMessage):
        """发送默认欢迎消息"""
        e_context["context"].type = ContextType.TEXT
        e_context["context"].content = self.group_welc_prompt.format(nickname=msg.actual_user_nickname)
        e_context.action = EventAction.BREAK

    def welcome(self, msg, qm, imgurl):
        """发送欢迎消息"""
        post_url = f"{self.base_url}/message/postAppMsg"
        now = datetime.now().strftime("%Y年%m月%d日 %H时%M分%S秒")
        payload = json.dumps({
            "appId": self.appid,
            "toWxid": msg.other_user_id,
            "appmsg": (
                f'<appmsg appid="" sdkver="1">'
                f'<title>👏欢迎 {msg.actual_user_nickname} 加入群聊！🎉</title>'
                f'<des>⌚：{now}\n签名：{qm if qm else "这个人没有签名"}</des>'
                f'<action>view</action><type>5</type><showtype>0</showtype><content />'
                f'<url id="" type="url" status="failed" title="" wc="0">{self.redirect_link}</url>'
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
        return response.json().get('ret', 500)

    def exit(self, group_id, imgurl, nickName):
        """发送退出消息"""
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
                f'<url id="" type="url" status="parsing" title="" wc="0">{self.exit_url}</url>'
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
        return response.json().get('ret', 500)

    def get_info(self, group_id, nickname):
        """获取用户信息"""
        wxid = self.get_list(group_id, nickname)
        if wxid is None:
            return None, None, None

        payload = json.dumps({
            "appId": self.appid,
            "chatroomId": group_id,
            "memberWxids": [wxid]
        })
        response = requests.request("POST", f"{self.base_url}/group/getChatroomMemberDetail", data=payload, headers=self.headers)
        data = response.json()

        if data.get('ret') != 200 or not data.get('data'):
            return None, None, None

        member_data = data["data"][0]
        return member_data.get("signature"), member_data.get("smallHeadImgUrl"), member_data.get("nickName")

    def get_list(self, group_id, nickname):
        """获取群成员列表"""
        payload = json.dumps({
            "appId": self.appid,
            "chatroomId": group_id,
        })
        response = requests.request("POST", f"{self.base_url}/group/getChatroomMemberList", data=payload, headers=self.headers)
        data = response.json()

        if data.get('ret') != 200 or not data.get('data'):
            return None

        for member in data["data"]["memberList"]:
            if member["nickName"] == nickname:
                return member["wxid"]
        return None

    def get_member_list(self, other_user_id, other_user_nickname):
        """获取群成员列表并监控退群行为"""
        if other_user_id in self.monitor_threads:
            if other_user_id in self.monitoring_groups:
                self.monitoring_groups.remove(other_user_id)
            if other_user_id in self.monitoring_groups_name:
                del self.monitoring_groups_name[other_user_id]
            if self.monitor_threads[other_user_id].is_alive():
                self.monitor_threads[other_user_id].join(timeout=0)
            del self.monitor_threads[other_user_id]

        def monitor_group(group_id):
            while group_id in self.monitoring_groups:
                try:
                    payload = json.dumps({
                        "appId": self.appid,
                        "chatroomId": group_id,
                    })
                    response = requests.request("POST", f"{self.base_url}/group/getChatroomMemberList", data=payload, headers=self.headers)
                    data = response.json()

                    if data.get('ret') != 200:
                        logger.error(f"[HelloPlus] Failed to get member list for group {group_id}: {data}")
                        time.sleep(self.sleep_time)
                        continue

                    current_members = data["data"]["memberList"]
                    leave_members_name = []
                    old_wxids = set()
                    new_wxids = set()

                    if group_id not in self.group_members:
                        self.group_members[group_id] = current_members
                    else:
                        old_members = self.group_members[group_id]
                        old_wxids = {m["wxid"] for m in old_members}
                        new_wxids = {m["wxid"] for m in current_members}
                        leave_members = old_wxids - new_wxids
                        if leave_members:
                            for wxid in leave_members:
                                member = next(m for m in old_members if m["wxid"] == wxid)
                                logger.info(f"[HelloPlus] User {member['nickName']} left group {group_id}")
                                self.exit(group_id, member['smallHeadImgUrl'], member['nickName'])
                                leave_members_name += [member['nickName']]

                        self.group_members[group_id] = current_members
                    if leave_members_name:
                        leave_str = f"退群成员：{', '.join(leave_members_name)}"
                    else:
                        leave_str = ""
                    if leave_members_name:
                        logger.info(f"[HelloPlus] {other_user_nickname}: {len(old_wxids)}/{len(new_wxids)} {leave_str}")

                    self.memberList = current_members
                    time.sleep(self.sleep_time)

                except Exception as e:
                    logger.error(f"[HelloPlus] Error monitoring group {group_id}: {e}")
                    if group_id not in self.monitoring_groups:
                        break
                    time.sleep(self.sleep_time)
                    continue

            logger.info(f"[HelloPlus] Stopped monitoring group {group_id}")

        self.monitoring_groups.add(other_user_id)
        self.monitoring_groups_name[other_user_id] = other_user_nickname
        thread = threading.Thread(target=monitor_group, args=(other_user_id,), name=self.get_thread_name())
        thread.daemon = True
        thread.start()
        self.monitor_threads[other_user_id] = thread
        logger.debug(f"[HelloPlus] 监控启动成功: {other_user_nickname}")
        return self.memberList

    def is_admin(self, wxid):
        """检查是否为管理员"""
        return wxid in self.admin_user

    def add_admin_user(self, token, wxid):
        """添加管理员"""
        if token == self.auth_token:
            self.admin_user.append(wxid)
            return True
        return False

    def get_group_list(self):
        """获取群组列表"""
        time.sleep(3)
        url = f"{self.base_url}/contacts/fetchContactsList"
        payload = json.dumps({"appId": self.appid})
        response = requests.request("POST", url, data=payload, headers=self.headers)
        response_data = response.json()

        if response_data.get('ret') != 200:
            logger.error(f"[HelloPlus] Failed to get group list: {response_data}")
            return

        rooms = response_data['data']['chatrooms']
        self.get_group_info(rooms)
        return

    def get_group_info(self, rooms):
        """获取群组信息"""
        url = f"{self.base_url}/contacts/getDetailInfo"
        payload = json.dumps({"appId": self.appid, "wxids": rooms})
        response = requests.request("POST", url, data=payload, headers=self.headers)
        response_data = response.json()

        if response_data.get('ret') != 200:
            return None

        data_info = response_data['data']
        for group_name in self.group_names:
            found = False
            for data in data_info:
                self.ql_list[data['userName']] = data['nickName']
                if data['nickName'] == group_name:
                    # time.sleep(1)
                    self.get_member_list(data['userName'], data['nickName'])
                    found = True
                    break
            if not found:
                logger.error(f"[HelloPlus] 群组 {group_name} 未找到")
        return self.ql_list

    def start_monitor(self, group_name):
        """启动监控"""
        try:
            for group_id, name in self.ql_list.items():
                if name == group_name:
                    try:
                        self.get_member_list(group_id, group_name)
                        return True, f"监控启动成功: {group_name}"
                    except Exception as e:
                        error_msg = f"启动群监控失败: {group_name} "
                        logger.error(f"启动群监控失败 {str(e)}")
                        return False, error_msg
            return False, f"未找到群组: {group_name}"
        except Exception as e:
            error_msg = f"启动监控时发生错误: {group_name}"
            logger.error(f"[启动监控时发生错误] : {str(e)}")
            return False, error_msg

    def get_help_text(self, **kwargs):
        """获取帮助文本"""
        help_text = (
            "📜 功能说明：\n\n"
            "1️⃣ 群监控管理认证 [token] - 验证管理员权限，成功后可管理群监控。\n"
            "2️⃣ 群监控列表 - 查看当前正在监控的群组列表及成员数量。\n"
            "3️⃣ 开启监控 [群组名] - 开启指定群组的退群监控功能。\n"
            "4️⃣ 关闭监控 [群组名] - 关闭指定群组的退群监控功能。\n"
            "📌 注意：\n"
            "- 管理员验证需要正确的token。\n"
            "- 开启/关闭监控功能仅限管理员使用。\n"
            "🎉 祝你使用愉快！"
        )
        return help_text

    def _load_config_template(self):
        """加载配置模板"""
        logger.debug("No Hello plugin config.json, use plugins/hello/config.json.template")
        try:
            plugin_config_path = os.path.join(self.path, "config.json.template")
            if os.path.exists(plugin_config_path):
                with open(plugin_config_path, "r", encoding="utf-8") as f:
                    plugin_conf = json.load(f)
                    return plugin_conf
        except Exception as e:
            logger.exception(e)
