# Wechatsync 本地 CLI 依赖缺失

## 复现步骤

在本地 Wechatsync clone 中直接运行已构建的 CLI：

```bash
node /Volumes/ExtSSD2601/AI_Assistant/tools/vendor/wechatsync/packages/cli/dist/index.js --help
```

## 期望行为

输出 `wechatsync` CLI 帮助信息，至少能列出 `sync`、`platforms`、`auth`、`extract` 等命令。

## 实际行为

命令启动失败，Node 无法解析 `ora` 依赖的 `cli-cursor` 包。

## 日志片段

```text
Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'cli-cursor' imported from /Volumes/ExtSSD2601/AI_Assistant/tools/vendor/wechatsync/packages/cli/node_modules/ora/index.js
    at Object.getPackageJSONURL (node:internal/modules/package_json_reader:255:9)
    at packageResolve (node:internal/modules/esm/resolve:767:81)
    at moduleResolve (node:internal/modules/esm/resolve:853:18)
```

## 备注

本次未修改 Wechatsync CLI/MCP/扩展源码。后续执行了：

```bash
pnpm install --frozen-lockfile
```

重新安装依赖后，`node packages/cli/dist/index.js --help` 已恢复正常。该问题更像是本地依赖安装不完整，而不是源码缺陷。
