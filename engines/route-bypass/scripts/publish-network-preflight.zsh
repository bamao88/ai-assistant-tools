#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
ROUTE_BYPASS="$SCRIPT_DIR/xhs-route-bypass.zsh"

usage() {
  cat <<USAGE
Usage:
  $0 <platform> [apply|status|resolve|remove]

Platforms:
  xiaohongshu|xhs          Xiaohongshu publish, including video/image upload CDN
  shipinhao|wechat-video  WeChat Channels publish
  bilibili|bilibili-video Bilibili video submission
  douyin                  Douyin creator publish
  gongzhonghao|gzh        WeChat Official Account draft/publish API
  article-drafts|wechatsync|draft-direct
                           Zhihu/Juejin/CSDN/Baijiahao/SegmentFault/Toutiao drafts
  transcribe|asr|video-transcribe
                           Cloud transcription (video-slicer): Volcengine/Aliyun ASR + OSS upload
  all|publishing          All configured publishing domains

Actions:
  apply    Refresh current platform IPs, apply local routes, and update managed hosts when needed
  status   Show route decisions for current platform domains
  resolve  Print current IPv4 answers for current platform domains
  remove   Remove routes managed by the underlying route-bypass helper
USAGE
}

die() {
  print -u2 "error: $*"
  exit 1
}

[[ -x "$ROUTE_BYPASS" ]] || die "route-bypass helper not executable: $ROUTE_BYPASS"

platform="${1:-}"
[[ -n "$platform" ]] || {
  usage
  exit 2
}
shift

action="${1:-apply}"
if [[ "$#" -gt 0 ]]; then
  shift
fi

case "$action" in
  apply|status|resolve|remove) ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    usage
    die "unknown action: $action"
    ;;
esac

is_truthy_env() {
  local value="${1:l}"
  [[ "$value" == "1" || "$value" == "true" || "$value" == "yes" || "$value" == "on" ]]
}

network_mode="${PLATFORM_PUBLISH_NETWORK_MODE:-${PUBLISH_NETWORK_MODE:-}}"
network_mode_lc="${network_mode:l}"
if [[ "$action" != "remove" && "$action" != "resolve" ]] && {
  [[ "$network_mode_lc" == "current-egress" ]] ||
  is_truthy_env "${PLATFORM_PUBLISH_SKIP_ROUTE_BYPASS:-}" ||
  is_truthy_env "${PUBLISH_SKIP_ROUTE_BYPASS:-}" ||
  is_truthy_env "${TVP_SKIP_ROUTE_BYPASS:-}"
}; then
  print "publish-network-preflight platform=$platform action=$action skipped mode=current-egress"
  exit 0
fi

typeset -a domains
manage_hosts=0
host_overrides=""
host_override_static=""
static_ips="__none__"
static_nets="__none__"

case "$platform" in
  xiaohongshu|xhs)
    domains=(
      xiaohongshu.com
      www.xiaohongshu.com
      creator.xiaohongshu.com
      edith.xiaohongshu.com
      ros-upload.xiaohongshu.com
      ros-upload.xhscdn.com
      ros-upload-d1.xhscdn.com
      ros-upload-d2.xhscdn.com
      ros-upload-d3.xhscdn.com
      ros-upload-d4.xhscdn.com
      ros-upload-d5.xhscdn.com
      ros-upload-d6.xhscdn.com
      ros-upload-d7.xhscdn.com
      ros-upload-d8.xhscdn.com
    )
    manage_hosts=1
    host_overrides="www.xiaohongshu.com edith.xiaohongshu.com ros-upload.xiaohongshu.com"
    static_ips="${XHS_ROUTE_STATIC_IPS:-23.59.252.178 23.59.252.200 23.59.252.201 23.59.252.202 23.59.252.203 96.7.244.134 96.7.244.142 96.7.244.153 96.7.244.158 184.27.185.201 184.27.185.213 212.129.158.241}"
    static_nets="${XHS_ROUTE_STATIC_NETS:-23.59.252.0/24 23.52.128.0/24 96.7.244.0/24 184.27.185.0/24 212.129.158.0/24}"
    ;;
  shipinhao|wechat-video|wechat-channels|channels)
    domains=(
      channels.weixin.qq.com
      open.weixin.qq.com
      res.wx.qq.com
      mp.weixin.qq.com
      store.mp.video.tencent-cloud.com
      finderpre.video.qq.com
      finder.video.qq.com
      finderassistancea.video.qq.com
      finderassistanceb.video.qq.com
      finderassistancec.video.qq.com
      finderassistanced.video.qq.com
      finderassistancee.video.qq.com
      wxapp.tc.qq.com
      aladin.wxqcloud.qq.com
      mmec.wxqcloud.qq.com.cn
      res.wxqcloud.qq.com.cn
    )
    manage_hosts=1
    # res.wx.qq.com DNS can return edge IPs that are routed locally but do not
    # accept 443 in the current network (2026-06-22 observed 43.x and
    # 183.204.106.138 timing out). Pin to a probed-good edge for login assets.
    host_override_static="res.wx.qq.com=39.156.8.194"
    # 视频号上传/CDN 边缘 IP 会在同一 /24 内轮换。2026-06-22 实测
    # 183.204.106.98 预检通过后，上传前解析到 183.204.106.138，
    # 如果只钉 host route 会重新走默认通道，导致上传被挡在流程前置检查。
    static_nets="${SHIPINHAO_ROUTE_STATIC_NETS:-183.204.90.0/24 183.204.96.0/24 183.204.106.0/24}"
    ;;
  bilibili|bilibili-video|bili)
    domains=(
      passport.bilibili.com
      api.bilibili.com
      member.bilibili.com
      app.bilibili.com
      www.bilibili.com
    )
    ;;
  douyin)
    domains=(
      creator.douyin.com
      www.douyin.com
      sso.douyin.com
      mcs.zijieapi.com
      security.zijieapi.com
      mon.zijieapi.com
      lf-fe-creator.douyinstatic.com
      lf-ucenter-web.yhgfb-cn-static.com
      lf3-static.bytednsdoc.com
      lf3-config.bytetcc.com
    )
    static_nets="${DOUYIN_ROUTE_STATIC_NETS:-101.47.85.0/24 101.126.58.0/24 103.216.136.0/24 111.13.104.0/24 111.13.110.0/24 111.31.37.0/24 111.32.168.0/24 111.132.33.0/24 111.132.35.0/24 111.132.43.0/24 111.132.45.0/24 111.47.233.0/24 111.47.235.0/24 111.62.47.0/24 111.62.113.0/24 111.62.187.0/24 117.161.15.0/24 117.161.26.0/24 117.161.66.0/24 117.161.134.0/24 117.161.138.0/24 117.169.5.0/24 120.226.6.0/24 120.233.80.0/24 120.255.47.0/24 139.177.246.0/24 155.102.209.0/24 163.181.39.0/24 183.201.204.0/24 183.201.235.0/24 183.201.251.0/24 221.194.131.0/24 27.222.17.0/24 36.143.194.0/24 36.143.201.0/24 39.136.88.0/24 39.137.66.0/24 59.80.57.0/24}"
    ;;
  gongzhonghao|gzh|wechat-official-account|weixin-mp)
    domains=(
      api.weixin.qq.com
      mp.weixin.qq.com
      res.wx.qq.com
      mmbiz.qpic.cn
      mmbiz.qlogo.cn
    )
    ;;
  article-drafts|wechatsync|draft-direct|article)
    domains=(
      www.zhihu.com
      zhuanlan.zhihu.com
      api.zhihu.com
      juejin.cn
      api.juejin.cn
      mp.csdn.net
      blog.csdn.net
      bizapi.csdn.net
      img-blog.csdnimg.cn
      baijiahao.baidu.com
      bjh.baidu.com
      mbd.baidu.com
      segmentfault.com
      api.segmentfault.com
      mp.toutiao.com
      www.toutiao.com
      pstatp.com
      byteimg.com
      zijieapi.com
    )
    ;;
  transcribe|asr|video-transcribe)
    # Cloud transcription (engines/video-slicer). 把整条转录链路都钉到本地出口，
    # 复刻"手动关代理"那条能跑通的路径（无需真关 VPN）：
    #  - 国内 ASR API：火山 openspeech / 阿里 dashscope（控制面调用走本地）。
    #  - public 上传站：uguu.se / 0x0.st（"上传公域音频"这一步也走本地，
    #    否则海外出口传大文件不稳——2026-06 实测 45MB/2.2h 走海外 8 次重试全空）。
    # OSS 两域名：⚠ 2026-06 OSS 凭证已过期，--uploader oss 暂不可用；
    #            域名留作续期后用，钉着无害。
    domains=(
      openspeech.bytedance.com
      dashscope.aliyuncs.com
      uguu.se
      h.uguu.se
      0x0.st
      oss-cn-beijing.aliyuncs.com
      zh-0121.oss-cn-beijing.aliyuncs.com
    )
    ;;
  all|publishing)
    domains=()
    manage_hosts=1
    host_overrides="www.xiaohongshu.com edith.xiaohongshu.com ros-upload.xiaohongshu.com"
    static_ips="${XHS_ROUTE_STATIC_IPS:-23.59.252.178 23.59.252.200 23.59.252.201 23.59.252.202 23.59.252.203 96.7.244.134 96.7.244.142 96.7.244.153 96.7.244.158 184.27.185.201 184.27.185.213 212.129.158.241}"
    static_nets="${XHS_ROUTE_STATIC_NETS:-23.59.252.0/24 23.52.128.0/24 96.7.244.0/24 184.27.185.0/24 212.129.158.0/24}"
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    usage
    die "unknown platform: $platform"
    ;;
esac

if [[ "$action" == "remove" ]]; then
  exec "$ROUTE_BYPASS" remove
fi

with_env=(
  XHS_ROUTE_MANAGE_HOSTS="$manage_hosts"
  XHS_ROUTE_HOST_OVERRIDE_DOMAINS="$host_overrides"
  XHS_ROUTE_HOST_OVERRIDE_STATIC="$host_override_static"
  XHS_ROUTE_STATIC_IPS="$static_ips"
  XHS_ROUTE_STATIC_NETS="$static_nets"
)

if [[ "$action" == "apply" ]]; then
  tailscale set --exit-node-allow-lan-access=true >/dev/null 2>&1 || true
fi

if [[ "$action" != "resolve" ]]; then
  print "publish-network-preflight platform=$platform action=$action"
fi
if [[ "${#domains[@]}" -gt 0 ]]; then
  env "${with_env[@]}" "$ROUTE_BYPASS" "$action" "${domains[@]}"
else
  env "${with_env[@]}" "$ROUTE_BYPASS" "$action"
fi
