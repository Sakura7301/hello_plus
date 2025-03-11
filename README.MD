# HelloPlus Plugin

HelloPlus是一个增强版的微信群管理插件，主要提供群聊欢迎、退群提醒等功能（原hello插件增加卡片欢迎）。

## 功能特点

1. 群聊欢迎
   - 支持自定义欢迎消息
   - 显示新成员头像和个性签名
   - 支持自定义欢迎卡片跳转链接
   - 显示加入时间戳

2. 退群提醒
   - 可配置是否启用退群提醒
   - 支持自定义退群提示语

3. 基础对话
   - 响应"Hello"命令：回复用户昵称
   - 响应"Hi"命令：简单回复"Hi"
   - 响应"End"命令：生成"The World"的图片

## 配置参数说明

### 基础配置参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| group_welc_fixed_msg | object | {} | 群固定欢迎语配置，格式为 {"群名": "欢迎语"} |
| group_welc_prompt | string | "请你随机使用一种风格说一句问候语来欢迎新用户{nickname}加入群聊。" | AI欢迎语模板 |
| group_exit_prompt | string | "请你随机使用一种风格介绍你自己，并告诉用户输入#help可以查看帮助信息。" | 退群提示语模板 |
| patpat_prompt | string | "请你随机使用一种风格跟其他群用户说他违反规则{nickname}退出群聊。" | 拍一拍提示语模板 |
| welc_text | boolean | false | 是否在欢迎卡片后追加文字欢迎 |
| use_character_desc | boolean | true | 是否使用角色设定 |

### 链接配置参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| redirect_link | string | "https://baike.baidu.com/item/welcome/2135227" | 欢迎卡片跳转链接 |
| exit_url | string | "https://baike.baidu.com/item/%E9%80%80%E5%87%BA/28909" | 退群卡片跳转链接 |

### 监控配置参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| sleep_time | integer | 60 | 群监控检查间隔(秒) |
| auth_token | string | "12345679" | 管理员验证token |
| say_exit | string | "有缘再见" | 退群卡片提示语 |


### 示例配置

```json
{
    "group_welc_fixed_msg": {
        "测试群": "欢迎加入测试群！"
    },
    "group_welc_prompt": "热烈欢迎{nickname}加入我们的大家庭！",
    "redirect_link": "https://example.com/welcome",
    "exit_url": "https://example.com/goodbye",
    "sleep_time": 30,
    "auth_token": "your-secure-token",
    "welc_text": true,
    "use_character_desc": true
}
```

## 使用方法

1. 群成员加入时自动触发欢迎
   - 显示欢迎卡片，包含成员昵称、时间、签名等信息（失败使用普通欢迎）
   - 如果配置了固定欢迎语，优先使用固定欢迎语

2. 群成员退出时自动提醒
   - 如果启用了退群提醒，会发送相应消息
   - 可在配置中自定义退群提示语

3. 基础命令
   - 发送"Hello"：机器人回复问候语
   - 发送"Hi"：机器人简单回复
   - 发送"End"：机器人生成图片
   - 发送"#help"：查看帮助信息

4. 群监控操作
   - 发送"开启退群监控"：开启当前群的退群监控功能
   - 发送"关闭退群监控"：关闭当前群的退群监控功能
   - 发送"查看监控群列表"：查看当前所有开启监控的群及其成员数量
   - 发送"群监控管理验证 [token]"：验证成为群监控管理员(私聊)

注意:
- 只有管理员可以操作群监控功能
- 监控间隔可通过 sleep_time 参数配置
- 管理员验证token需要在配置文件中设置
- 建议在私聊环境下进行管理员验证

## 注意事项

1. 请确保已正确配置GE微信相关参数
2. 建议根据实际需求调整欢迎语和提示语模板
3. 如需禁用某些功能，可在配置文件中设置相应参数

## 作者

作者：wangcl
版本：0.1
