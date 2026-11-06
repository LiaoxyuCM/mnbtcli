import os
import sys
import time
import requests
import subprocess
import tempfile
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


def _human_size(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0


def _fmt_time(ts):
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(int(ts)))
    except (TypeError, ValueError, OSError):
        return str(ts)


# 显示宽度：中文算 2 列
def _width(s):
    w = 0
    for ch in str(s):
        w += 2 if ord(ch) > 0x2E80 else 1
    return w


def _pad(s, w, align="left"):
    s = str(s)
    gap = w - _width(s)
    if gap <= 0:
        return s
    return s + " " * gap if align == "left" else " " * gap + s


def _truncate(s, w):
    s = str(s)
    if _width(s) <= w:
        return s
    out, cur = "", 0
    for ch in s:
        cw = 2 if ord(ch) > 0x2E80 else 1
        if cur + cw > w - 1:
            break
        out += ch
        cur += cw
    return out + "…"


def print_table(title, headers, rows, aligns=None):
    """打印一个自适应列宽的表格。"""
    if aligns is None:
        aligns = ["left"] * len(headers)

    # 计算每列宽度（表头 vs 数据）
    widths = [_width(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], _width(cell))

    # 上限截断（避免超宽）
    MAX = 60
    widths = [min(w, MAX) for w in widths]

    total = sum(widths) + 3 * (len(headers) - 1)
    bar = "─" * total

    print()
    print(f"┌─ {title} " + "─" * max(0, total - _width(title) - 3) + "┐")
    # 表头
    head_line = "  ".join(_pad(h, widths[i], aligns[i])
                          for i, h in enumerate(headers))
    print("│ " + head_line + " │")
    print("├" + bar + "┤")
    # 数据
    for r in rows:
        cells = [_truncate(c, widths[i]) for i, c in enumerate(r)]
        line = "  ".join(_pad(c, widths[i], aligns[i])
                         for i, c in enumerate(cells))
        print("│ " + line + " │")
    print("└" + bar + "┘")
    print()

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

def render_listfile(result):
    """渲染 listfile 的返回值。"""
    if not isinstance(result, dict):
        return

    rows = result.get("rows") or []
    path = result.get("path", "/")
    total = result.get("total", len(rows))

    # 顶部摘要
    n_dir = sum(1 for r in rows if r.get("type") == "dir")
    n_file = sum(1 for r in rows if r.get("type") == "file")
    total_size = sum(int(r.get("size", 0) or 0) for r in rows)
    print()
    print(f"目录浏览  {path:<45}")
    print(f"合计 {total} 项 · 目录 {n_dir} · 文件 {n_file} · 体积 {_human_size(total_size):<12}")

    if not rows:
        print("  (空目录)")
        return

    # 表格
    table_rows = []
    for r in rows:
        table_rows.append([
            r.get("name", "") + ("/" if r.get("type") == "dir" else ""),
            _human_size(r.get("size", 0)),
            _fmt_time(r.get("mtime", 0)),
            "⬇" + str(r.get("download", "0"))
        ])
    print_table(
        "明细",
        ["名称", "大小", "修改时间", "下载"],
        table_rows,
    )



def main():
    dtx = {}
    argv = list([] if sys.argv is None else sys.argv[1:])

    if not argv:
        print("""\
没有参数

欢迎使用 MNBTCLI ! 用法如下:
    已实现
        vim|vi|nano|notepad </path/to/file.txt>
        ls <dir/>

    未实现
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
            # request_server(dtx)
        finally:
            os.remove(tmp)
    elif cmd == "ls":
        if not rest:
            print("缺少必要参数\nls <path/>")
            return  # 或 sys.exit(1)
        dtx = {"gn": "listfile", "path": rest[0], "limit": "100",
                    "offset": "0", "page": "1", "sort": "name",
                    "sortOrder": "asc"}



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
    elif gn == "listfile":
         render_listfile(result)
    # else:
    #     render_generic(result)


if __name__ == "__main__":
    main()
