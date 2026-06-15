#!/usr/bin/env python3
"""WeChat v4 图片 .dat 解密（算法依据 chatlog/WeChatMsg）。

格式：头 07 08 56 32 = v4 "V2"。[6:10]LE=AES段长(恒1024)、[10:14]LE=XOR段长、[15:]=数据。
前 AES 段用 AES-128-ECB(无IV)解，其余单字节 XOR。解出 magic：
  FFD8FF=jpg / 89504E47=png / GIF8=gif / 'wxgf'=微信专有格式(本脚本不解码,需 Wxam2pic)。
两把 key 来自 WeFlow 配置（见 get_img_key.py）：imgkey=16字节、xorkey=单字节(本机=0x7F)。

CLI: decrypt_dat.py <imgkey_hex_or_ascii> <in.dat> <out_basepath_no_ext> [xor_hex]
库用: from decrypt_dat import dat2img; res,ext,info = dat2img(data, key_bytes, xor_byte)
"""
import sys, struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

V1_HDR = bytes([0x07, 0x08, 0x56, 0x31])
V2_HDR = bytes([0x07, 0x08, 0x56, 0x32])
V1_KEY = b"cfcd208495d565ef"  # v1 固定 key = md5("0")[:16]
SIGS = [(b"\xff\xd8\xff", "jpg"), (b"\x89PNG", "png"), (b"GIF8", "gif"),
        (b"\x49\x49\x2a\x00", "tiff"), (b"BM", "bmp"), (b"wxgf", "wxgf")]


def aes_ecb_dec(data, key):
    c = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return c.update(data) + c.finalize()


def detect(buf):
    for sig, ext in SIGS:
        if buf[: len(sig)] == sig:
            return ext
    return None


def dat2img(data, imgkey, xorkey=0x7F):
    """返回 (解出字节, 扩展名 or None, info)。ext=='wxgf' 表示是专有格式未转码。"""
    if data[:4] in (V2_HDR, V1_HDR):
        key = V1_KEY if data[:4] == V1_HDR else imgkey
        aes_len = struct.unpack("<I", data[6:10])[0]
        xor_len = struct.unpack("<I", data[10:14])[0]
        fd = data[15:]
        a0 = min((aes_len // 16) * 16 + 16, len(fd))
        dec = aes_ecb_dec(fd[:a0], key)
        res = dec[:aes_len] if len(dec) > aes_len else dec
        mid_e = len(fd) - xor_len
        if a0 < mid_e:
            res += fd[a0:mid_e]
        if xor_len > 0 and mid_e < len(fd):
            res += bytes(b ^ xorkey for b in fd[mid_e:])
        return res, detect(res), (aes_len, xor_len, xorkey)
    # 旧版单字节 XOR 整体
    for sig, ext in SIGS:
        if ext == "wxgf":
            continue
        xb = data[0] ^ sig[0]
        if all((data[i] ^ sig[i]) == xb for i in range(len(sig))):
            return bytes(b ^ xb for b in data), ext, ("xor", xb)
    return None, None, None


if __name__ == "__main__":
    raw = sys.argv[1]
    key = bytes.fromhex(raw) if len(raw) == 32 and all(c in "0123456789abcdefABCDEF" for c in raw) else raw.encode("latin-1")
    xk = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x7F
    data = open(sys.argv[2], "rb").read()
    res, ext, info = dat2img(data, key, xk)
    if not ext:
        print("FAIL", sys.argv[2], "first16", res[:16].hex() if res else None)
        sys.exit(2)
    out = sys.argv[3] + "." + ext
    open(out, "wb").write(res)
    print("OK", out, ext, len(res), info)
