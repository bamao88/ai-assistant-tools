# 公众号文章与原生贴图：现有Chrome网页流程

先按 [_local-chrome.md](_local-chrome.md)绑定本台电脑已有Chrome，通过会话hook。直接打开`https://mp.weixin.qq.com/`检查公众号主体；无登录时保留原页请用户扫码，不读取AppSecret、导Cookie、运行认证CLI或改用API直传。只有账号名/主体和任务目标匹配才继续。

## 内容包与样式

普通文章`news`使用已确认标题、作者、正文HTML和独立封面；原生贴图`newspic`使用有序图片与纯文本说明，首张即封面，不嵌进文章正文。素材数量、类型与限制按本次真实网页及本地发布包检查，不把旧API权限当成网页可用证明。

保留既有样式映射：AI PM小助理（AI PM超级小助理）使用coral，封面kit在`assets/gongzhonghao/ai-pm-assistant/`；直觉机器漫谈（MiaoDX）使用claude与本条封面，不套小助理模板。历史`wxp-ai/mdx/wxp-self`是API账号配置名，不是Chrome profile，不据此选择浏览器或调用发布API。

需要Markdown排版时可本地预览（不上传、不取令牌、不建草稿）：

```bash
npx tsx /Volumes/ExtSSD2601/AI_Assistant/tools/engines/gzh-publish/src/index.ts <publish_file.md> --theme <已确认主题> --dry-run
```

已有自定义样式时用已确认`--style-config <样式.json>`替代主题，保持账号专属。贴图发布包由`content-package-create`按`assets/templates/publish_gongzhonghao_newspic.md`准备；正文只放实际说明，图片顺序不能改变。

## 网页执行

1. 先查同一篇是否已有草稿或发表记录，结果不明接回原稿，不重复建稿。只读接管验证到身份/首页即停止。
2. `before_upload`通过后，在同一Chrome通过页面现有入口新建或编辑本次授权稿件；上传图片、封面，填标题、作者和正式正文，保留分段。
3. 普通文章检查实际排版、图片、摘要与封面各比例；贴图检查原生内容类型、顺序、首图裁切、说明和评论设置。找不到网页对应能力时保留页说明缺口，不自动改API或另一配置。
4. 保存草稿需本次授权；草稿回执与实际读回完成才报已保存。预览、发表、群发是不同动作，不把其中一项授权扩成另一项。
5. 最终发表/群发前读最新权限、核对真实目标与页面预览，运行`before_submit`。平台接受才记录提交；公开与手机呈现分别验收。

只关闭本条已成功任务页；等登录/审核/人工补位的页面按主Skill保留，不关闭共享Chrome。旧API能力及历史测试仅在history留作维护，当前流程不调用其上传、建草稿或发表命令。
