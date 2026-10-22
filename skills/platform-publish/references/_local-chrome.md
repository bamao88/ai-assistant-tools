# 本机已有Chrome接管与会话hook

本文件是唯一活动浏览器连接流程。只复用本台电脑、负责人已运行的日常Chrome；不启动浏览器、不创建profile或上下文、不接远端、不导Cookie。可以在同一个已有profile内新开平台标签页。

## 发现和锁定

1. 先遵循当次浏览器工具的首次初始化协议。当前CUA首次需要库存时先单独调用`await cua.getState()`并读取返回文档；运行时已初始化后再按文档使用`cua.listBrowsers()`等入口枚举本机Chrome。选择`family=chrome,type=extension`的已运行实例。按项目已确认的Google/profile归属定位，不从脚本slot名或调试端口推断。
2. 用本机Chrome的`Local State`中profile目录、显示名/Google标签核对归属，只读取这些非凭据字段，不读网站Cookie。记录标准Chrome根目录与已存在的profile子目录。多个profile不能拿另一个业务账号补位。
3. 保存`binding.json`锁定本轮真实entry及profile。浏览器ID可能变化，不能把历史ID永久硬编码；同轮锁定后不因错误换成别的实例。
4. 保存`observed.json`，内容来自本轮真实inventory及即将使用/正在使用的连接。不得把CDP连接标成extension，不把新建上下文标成existing；缺信息即报错，不靠默认值补齐。

## 必经hook

```bash
python3 /Users/xpw/.agents/skills/Agent-Publish/scripts/guard_existing_chrome.py \
  --contract <本轮binding.json> \
  --observed <当前observed.json> \
  --phase before_connect
```

同一命令的阶段分别使用`before_connect`、`before_upload`、`before_submit`。上传阶段也覆盖填表、写草稿等写操作。成功退出0，错误退出2并返回`PUBLISH_SESSION_*`；错误必须向用户说明，不继续到平台写操作、不改绑定绕过。

`binding.json`格式（值必须来自实际环境）：

```json
{
  "schema_version": 1,
  "host": "local",
  "browser": {
    "family": "chrome",
    "id": "从当前inventory读取",
    "type": "extension",
    "profileName": "实际Chrome配置名",
    "metadata": {"extensionInstanceId": "实际扩展实例"}
  },
  "profile": {
    "user_data_dir": "本机标准Chrome数据目录",
    "profile_directory": "已核对的现有配置目录"
  }
}
```

`observed.json`格式：

```json
{
  "browser": {
    "family": "chrome",
    "id": "当前实际浏览器ID",
    "type": "extension",
    "profileName": "实际配置名",
    "metadata": {"extensionInstanceId": "实际扩展实例"}
  },
  "connection": {
    "host": "local",
    "transport": "extension",
    "provider": "cua",
    "browser_id": "当前连接的真实ID",
    "extension_instance_id": "当前连接的真实扩展实例",
    "existing_session": true,
    "headless": false,
    "launched_new_browser": false,
    "created_new_context": false,
    "restored_cookies": false
  }
}
```

可观测实际目录时同时填`connection.user_data_dir`、`profile_directory`，必须与绑定一致。CUA清单不暴露磁盘目录时不伪造该字段；hook按已核对的本机目录与精确扩展实例绑定检查。完整格式、错误码与测试见 [scripts说明](../scripts/README.md)。

hook检查本Skill入口提供的真实路由元数据与本机目录，不是宿主全局工具拦截器，也不独立获取浏览器数据或证明平台登录。所有活动发布入口都须调用它；绕过Skill任意运行旧CLI不受该脚本自动拦截，属于未遵循执行流程。

## 在同一连接执行

hook通过后使用已选Chrome句柄，在同一运行时复用连接与页面。接口缺项先查工具文档，不重启Chrome、换脚本profile或另连调试端口。连接失效与单步操作报错分开；重新连接时再检查hook及原tab/任务阶段。

登录直接读页面。创作后台未完成正常SSO时，可在同一profile从平台主站可见入口导航；主站和后台身份均须核对。若仍出现登录/本人认证页，保留它，请用户登录。不要运行检查器或恢复凭据。

只读接管验收只需打开平台、读取身份、可见管理页与截图；不选择文件、不填稿、不保存、不提交。已接受的稿件不得用来重放投稿。用户登录/未完成页使用`markHandoff()`逐轮保留，成功仅关闭对应任务页，始终不关闭共享Chrome。
