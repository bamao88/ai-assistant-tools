#!/usr/bin/env python3
"""从 WeFlow 配置取微信图片解密 key（imgkey + xorkey）。

WeFlow 把 key 用 Electron safeStorage 加密存在 WeFlow-config.json 的 imageAesKey/imageXorKey
（值形如 `safe:djEw...`，base64 后是 `v10`+AES-128-CBC）。解密需 keychain 里的 safeStorage 密钥：
  security find-generic-password -s "weflow Safe Storage" -w   # 会弹一次钥匙串授权框,点"始终允许"
派生: key = PBKDF2-HMAC-SHA1(pw, b"saltysalt", 1003, 16)；IV=16×0x20；去 PKCS7。

输出: 写 imgkey.txt(16字节ASCII原样) 和 imgxor.txt；打印摘要(不打印明文 key)。
前置: WeFlow 装过并登录过(配置存在即可,WeFlow 不必在运行)。
"""
import subprocess, base64, json, os, sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from pathlib import Path

# engine 根（capabilities/acquire/ → up 2）入 sys.path，imgkey/imgxor 落点经 config 收口。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

CFG = os.path.expanduser("~/Library/Application Support/weflow/WeFlow-config.json")


def main():
    pw = subprocess.check_output(
        ["security", "find-generic-password", "-s", "weflow Safe Storage", "-w"]
    ).strip()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA1(), length=16, salt=b"saltysalt",
                     iterations=1003, backend=default_backend())
    aeskey = kdf.derive(pw)

    def dec(safeval):
        raw = base64.b64decode(safeval[len("safe:"):])
        assert raw[:3] == b"v10", raw[:3]
        d = Cipher(algorithms.AES(aeskey), modes.CBC(b" " * 16), backend=default_backend()).decryptor()
        pt = d.update(raw[3:]) + d.finalize()
        pad = pt[-1]
        return pt[:-pad] if 1 <= pad <= 16 else pt

    cfg = json.load(open(CFG))
    imgaes = dec(cfg["imageAesKey"])
    imgxor = dec(cfg["imageXorKey"])
    config.ensure_dir(config.PAYMENT_PROOF_DIR)
    config.PAYMENT_IMGKEY_FILE.write_text(
        imgaes.decode("latin-1") if all(c < 128 for c in imgaes) else imgaes.hex())
    config.PAYMENT_IMGXOR_FILE.write_text(imgxor.decode("latin-1", "replace"))
    print(f"imgkey 写入 imgkey.txt (len {len(imgaes)})；imgxor={imgxor!r} (本机通常=b'127' → XOR 0x7F)")
    print("DONE")


if __name__ == "__main__":
    main()
