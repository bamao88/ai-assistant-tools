# 已有 Chrome 会话检查 hook

`guard_existing_chrome.py` 是 Agent-Publish 发布入口的前置检查。连接前、上传前、提交前分别运行：

```bash
python3 /Users/xpw/.agents/skills/Agent-Publish/scripts/guard_existing_chrome.py \
  --contract <本轮Chrome绑定.json> \
  --observed <当前实际选择与连接.json> \
  --phase before_connect
```

另两个阶段为 `before_upload`、`before_submit`。退出 `0` 才可继续；退出 `2` 时输出 `allowed:false` 和 `PUBLISH_SESSION_*` 错误码，立即保留原页并处理错误。不能用另一份 CLI、Cookie 恢复、CDP 或独立 profile 绕过失败。

## 输入

先从本轮 CUA inventory 选择负责人已打开的日常 Chrome，并核对本机 Chrome 的配置目录。原样保存该 inventory entry，形成本轮固定契约。浏览器 ID 与扩展实例 ID 是本轮绑定，不能永久硬编码；浏览器重启或实例改变后需要重新核对。

`contract.json`：

```json
{
  "schema_version": 1,
  "host": "local",
  "browser": {
    "family": "chrome",
    "id": "本轮inventory的id",
    "metadata": {"extensionInstanceId": "本轮inventory的实际扩展实例id"},
    "name": "Chrome",
    "profileName": "本轮已核对的日常配置名",
    "type": "extension"
  },
  "profile": {
    "user_data_dir": "/Users/xpw/Library/Application Support/Google/Chrome",
    "profile_directory": "Default"
  }
}
```

每个阶段读取当前实际选择的入口及连接方式，形成 `observed.json`，不能直接把旧契约复制成“当前观察”：

```json
{
  "browser": {
    "family": "chrome",
    "id": "当前实际浏览器ID",
    "metadata": {"extensionInstanceId": "当前实际扩展实例"},
    "profileName": "当前实际配置名",
    "type": "extension"
  },
  "connection": {
    "host": "local",
    "transport": "extension",
    "provider": "cua",
    "browser_id": "当前实际连接的inventory id",
    "extension_instance_id": "当前实际连接的扩展实例id",
    "existing_session": true,
    "headless": false,
    "launched_new_browser": false,
    "created_new_context": false,
    "restored_cookies": false
  }
}
```

连接元数据有 `user_data_dir`、`profile_directory` 时一并记录，必须和契约一致。CUA inventory 不提供磁盘目录时，不虚构“工具已读回目录”；目录来自本机核对，当前连接通过固定的 inventory/扩展实例匹配。`host` 固定为 `local`；Chrome 的标准数据目录按当前系统用户计算，契约不能授权脚本目录。Mac 的该目录为 `~/Library/Application Support/Google/Chrome`。

hook还只读本机`Local State → profile.info_cache`，确认配置目录名称与inventory.profileName唯一匹配；名称不同、未登记或重名无法绑定均报明确`PUBLISH_SESSION_PROFILE_*`错误。它不读取Cookie或回显其它Local State内容。

## 拦截与验收范围

- 拒绝 IAB、其它浏览器、CDP/脚本连接、其它电脑、另一个 Chrome 扩展实例/配置、脚本数据目录、新建浏览器/上下文、无头模式及 Cookie 恢复。
- 即使错误配置是可见浏览器，也拒绝；机器上另有脚本 Chrome 进程不会影响正确扩展入口通过。
- hook 不启动、重启、关闭或登录任何浏览器，不运行 `check-login`，不写 Cookie，不访问平台，不上传或发布。
- hook 检查调用方提供的实际 inventory 与连接元数据，不能阻止未经过它的任意 shell/浏览器调用，不能据此声称全局工具拦截已经启用。
- 平台登录状态、目标账号身份及内容质量由 Agent 在同一个 Chrome 页面核验。`before_connect` 不要求平台登录；上传/提交前须完成页面验收。未登录时保留该页，请用户在当前 Chrome 登录。

离线逻辑/契约验证：

```bash
python3 -m unittest discover \
  -s /Users/xpw/.agents/skills/Agent-Publish/scripts \
  -p 'test_guard_existing_chrome.py' -v
```

离线通过只证明路由规则有效。真实接管需用当前 Chrome 做只读页面验证；已经提交过的作品不重新上传或提交。
