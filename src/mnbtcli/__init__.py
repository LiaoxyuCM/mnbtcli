import os
import sys
import time
import requests
import subprocess
from dotenv import load_dotenv

load_dotenv()

REQUEST_URL: str = "https://m.luoli.love/user/ajax.php";
HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0",
}
COOKIES = {
    "user_token": os.getenv("AUTH_USER_TOKEN"),
    "PHPSESSID": os.getenv("AUTH_PHP_SESSION_TOKEN"),
}

def request_server(data):
    try:
        resp = requests.post(REQUEST_URL, headers=HEADERS, cookies=COOKIES,
                             data=data, timeout=15);
        resp.raise_for_status();
        return resp;
    except requests.RequestException as e:
        print_status_banner(False, "网络错误", str(e));
        sys.exit(1);


def print_status_banner(ok, code, msg, redirect=None):
    """状态横幅：成功/失败醒目展示。"""
    icon = "[OK]" if ok else "[ER]"
    color = "\033[92m" if ok else "\033[91m"  # green / red
    reset = "\033[0m"
    width = 60
    print()
    print(color + "═" * width + reset)
    print(color + f"  {icon}  {code or ('成功' if ok else '失败')}" + reset)
    if msg and msg != code:
        print(color + f"      {msg}" + reset)
    if redirect:
        print(color + f"      → {redirect}" + reset)
    print(color + "═" * width + reset)
    print()


def render_changefile(result, sent_data=None):
    """渲染 changefile（setwj）的返回值。"""
    if sent_data:
        print()
        print(f"目标文件: {sent_data.get('wj')}")
        nr = sent_data.get("nr", "")
        print(f"写入内容: {len(nr)} 字符 / {len(nr.encode('utf-8'))} 字节")
        preview = "\n".join(nr.splitlines()[:5])
        if preview:
            print("   预览:")
            for line in preview.splitlines():
                print(f"     │ {line}")
            if len(nr.splitlines()) > 5:
                print("     │ …")

    if isinstance(result, dict):
        ok = bool(result.get("success", False))
        print_status_banner(
            ok,
            result.get("code"),
            result.get("msg"),
            result.get("redirect"),
        )
        # # 补充字段表
        # print_table(
        #     "返回字段",
        #     ["字段", "值"],
        #     [[k, v] for k, v in result.items()],
        #     aligns=["left", "left"],
        # )
    else:
        pp(result)


def main():
    dtx = {}
    argv = list([] if sys.argv is None else sys.argv[1:])

    if not argv:
        print("""\
没有参数

欢迎使用 MNBTCLI ! 用法如下:
    已实现
        vim|vi|nano|notepad </path/to/file.txt>

    未实现
        ls <dir>
        mv_samedir <path/> <old_filename> <new_filename>
        mv_samefilename <old_path/> <new_path/> <filename>
        rm [-i] <path/> <filename>
        touch <path/> <filename>
        cp_samefilename <origin_path/> <origin_file_name> <new_path/>
""");
        return;
    cmd = argv[0]
    rest = argv[1:]

    if cmd in ["vim", "vi", "nano", "notepad"]:
        if not rest:
            print("缺少必要参数\nvim|vi|nano|notepad <path/to/file.txt>")
            return  # 或 sys.exit(1)

        import tempfile, subprocess, os
        fd, tmp = tempfile.mkstemp()
        os.close(fd)
        try:
            content = request_server({"gn": "hqwj", "wj": rest[0]}).text
            with open(tmp, "w") as f:
                f.write(content)

            if subprocess.run([cmd, tmp]).returncode != 0:
                print(f"调用 {cmd} 失败")
                return

            with open(tmp) as f:
                dtx = {"gn": "setwj", "wj": rest[0], "nr": f.read()}
            request_server(dtx)
        finally:
            os.remove(tmp)


    resp = request_server(dtx);

    try:
        result = resp.json()
    except ValueError:
        print("响应不是合法 JSON:")
        print(resp.text)
        sys.exit(1)

    if not result:
        print_status_banner(False, "Request Failed", "服务端返回空响应")
        return
    
    gn = dtx.get("gn")
    if gn == "setwj":
        render_changefile(result, dtx)

    # if gn == "listfile":
    #     render_listfile(result)
    # else:
    #     render_generic(result)


if __name__ == "__main__":
    main()
