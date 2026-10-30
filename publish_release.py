#!/usr/bin/env python3
"""publish_release.py — 用 Personal Access Token 创建 GitHub Release 并上传补丁

用法:
    GH_TOKEN=ghp_xxx python publish_release.py <补丁.7z路径>
    # 或
    python publish_release.py <补丁.7z路径> --token ghp_xxx

前置: 在 GitHub → Settings → Developer settings → Personal Access Tokens
      生成一个具有 repo（或 public_repo）权限的 token。
"""
import sys, os, json, urllib.request, urllib.error

REPO = "wknet1988/Tenshi-no-himegoto-CN-lang-pack"
API = "https://api.github.com"
TAG = "v1.0"
REL_NAME = "天使のひめごと 简体中文汉化补丁 v1.0"
HERE = os.path.dirname(os.path.abspath(__file__))


def get_token(argv):
    tok = os.environ.get("GH_TOKEN")
    if not tok:
        for i, a in enumerate(argv):
            if a in ("--token", "-t") and i + 1 < len(argv):
                return argv[i + 1]
    return tok


def api(method, url, token, data=None, binary=False, extra_headers=None):
    headers = {
        "Authorization": "Bearer %s" % token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if extra_headers:
        headers.update(extra_headers)
    body = None
    if data is not None:
        if binary:
            body = data
            headers["Content-Type"] = "application/octet-stream"
        else:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.getcode(), json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    argv = sys.argv[1:]
    token = get_token(argv)
    asset = next((a for a in argv if a.endswith(".7z") or a.endswith(".zip")), None)
    if not token:
        print("!! 缺少 token。用法: GH_TOKEN=xxx python publish_release.py <补丁.7z>")
        sys.exit(1)
    if not asset or not os.path.isfile(asset):
        print("!! 找不到补丁文件。请提供 .7z/.zip 路径作为第一个参数。")
        sys.exit(1)

    # 读取发布说明
    body_path = os.path.join(HERE, "RELEASE_BODY.md")
    body = open(body_path, "r", encoding="utf-8").read() if os.path.isfile(body_path) else "简体中文汉化补丁"

    print("== 创建 Release %s ==" % TAG)
    code, resp = api("POST", "%s/repos/%s/releases" % (API, REPO), token, {
        "tag_name": TAG,
        "name": REL_NAME,
        "body": body,
        "draft": False,
        "prerelease": False,
        "generate_release_notes": False,
    })
    if code not in (200, 201):
        print("!! 创建 Release 失败 (%d):" % code, resp)
        sys.exit(1)
    upload_url = resp.get("upload_url", "").split("{")[0]
    print("   创建成功, upload_url =", upload_url)

    print("== 上传资产 %s ==" % os.path.basename(asset))
    with open(asset, "rb") as f:
        code, resp = api(
            "POST",
            "%s?name=%s" % (upload_url, urllib.parse.quote(os.path.basename(asset))),
            token, data=f, binary=True,
        )
    if code not in (200, 201):
        print("!! 上传失败 (%d):" % code, resp)
        sys.exit(1)
    print("   上传成功 ->", resp.get("browser_download_url"))
    print("\n完成。Release 地址: https://github.com/%s/releases/tag/%s" % (REPO, TAG))


if __name__ == "__main__":
    import urllib.parse
    main()
