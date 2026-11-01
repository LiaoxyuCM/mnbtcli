import os
import sys
import argparse
import time
import requests
from pprint import pp
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# 参数解析（保持不变）
# ---------------------------------------------------------------------------

def parse_flags(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    _, unknown = parser.parse_known_args(argv)
    data = {}
    i = 0
    while i < len(unknown):
        token = unknown[i]
        if token.startswith("--"):
            key = token[2:]
            if "=" in key:
                key, value = key.split("=", 1)
                data[key] = value
                i += 1
            else:
                if i + 1 < len(unknown) and not unknown[i + 1].startswith("--"):
                    data[key] = unknown[i + 1]
                    i += 2
                else:
                    data[key] = True
                    i += 1
        else:
            i += 1
    return data


def parse_positional(argv):
    if not argv:
        return None, {}
    cmd = argv[0]
    rest = argv[1:]

    if cmd == "changefilecontent":
        if len(rest) < 2:
            raise SystemExit("用法: changefilecontent <remote_path> <local_file>")
        return cmd, {"wj": rest[0], "local_file": rest[1]}
    if cmd == "listfile":
        return cmd, {"path": rest[0] if rest else "/"}
    if cmd == "setfilename":
        if len(rest) < 3:
            raise SystemExit("用法: setfilename <path> <origin_name> <changed_name>")
        return cmd, {"lj": rest[0], "wjjm": rest[1], "wjmc": rest[2]}
    if cmd == "deletefile":
        if len(rest) < 3:
            raise SystemExit("用法: deletefile <\"file\"/\"dir\"> <path> <name>")
        return cmd, {"lx": rest[0], "path": rest[1], "name": rest[2]}
    if cmd == "createfile":
        if len(rest) < 2:
            raise SystemExit("用法: createfile <path> <name>")
        return cmd, {"ml": rest[0], "wjname": rest[1]}
    raise SystemExit(f"未知命令: {cmd}")


def read_local_file(path):
    if not os.path.isfile(path):
        raise SystemExit(f"本地文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_request_data(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and not argv[0].startswith("--"):
        cmd, pos = parse_positional(argv)
        if cmd == "changefilecontent":
            return {"gn": "setwj", "wj": pos["wj"],
                    "nr": read_local_file(pos["local_file"])}
        if cmd == "listfile":
            return {"gn": "listfile", "path": pos["path"], "limit": "100",
                    "offset": "0", "page": "1", "sort": "name",
                    "sortOrder": "asc"}
        if cmd == "setfilename":
            return {"gn": "setname", "lj": pos["lj"],
                    "wjjm": pos["wjjm"], "wjmc": pos["wjmc"]}
        if cmd == "deletefile":
            return {"gn": "ftpsc", "lx": pos["lx"],
                    "path": pos["path"], "name": pos["name"]}
        if cmd == "createfile":
            return {"gn": "xjwj", "ml": pos["ml"],
                    "wjname": pos["wjname"]}
    return parse_flags(argv)


# ---------------------------------------------------------------------------
# 图表化展示工具
# ---------------------------------------------------------------------------

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


def print_status_banner(ok, code, msg, redirect=None):
    """状态横幅：成功/失败醒目展示。"""
    icon = "✔" if ok else "✘"
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


def print_file_tree(title, rows):
    """把 rows 按 dir/file 用树形结构展示。"""
    dirs = [r for r in rows if r.get("type") == "dir"]
    files = [r for r in rows if r.get("type") == "file"]
    others = [r for r in rows if r.get("type") not in ("dir", "file")]

    print()
    print(f"┌─ {title} (目录 {len(dirs)} / 文件 {len(files)})")
    print("│")
    for i, r in enumerate(dirs):
        last = (i == len(dirs) - 1) and not files and not others
        branch = "└──" if last else "├──"
        print(f"│  {branch} 📁 {r.get('name'):<40} {_human_size(r.get('size')):>10}  {_fmt_time(r.get('mtime'))}")
    for i, r in enumerate(files):
        last = (i == len(files) - 1) and not others
        branch = "└──" if last else "├──"
        print(f"│  {branch} 📄 {r.get('name'):<40} {_human_size(r.get('size')):>10}  {_fmt_time(r.get('mtime'))}")
    for i, r in enumerate(others):
        last = i == len(others) - 1
        branch = "└──" if last else "├──"
        print(f"│  {branch} ❓ {r.get('name'):<40} {_human_size(r.get('size')):>10}  {_fmt_time(r.get('mtime'))}")
    print("└")
    print()


def render_listfile(result):
    """渲染 listfile 的返回值。"""
    if not isinstance(result, dict):
        pp(result)
        return

    rows = result.get("rows") or []
    path = result.get("path", "/")
    total = result.get("total", len(rows))

    # 顶部摘要
    n_dir = sum(1 for r in rows if r.get("type") == "dir")
    n_file = sum(1 for r in rows if r.get("type") == "file")
    total_size = sum(int(r.get("size", 0) or 0) for r in rows)
    print()
    print("╔" + "═" * 60 + "╗")
    print(f"║ 📂 目录浏览  {path:<45} ║")
    print(f"║ 合计 {total} 项 · 目录 {n_dir} · 文件 {n_file} · 体积 {_human_size(total_size):<12} ║")
    print("╚" + "═" * 60 + "╝")

    if not rows:
        print("  (空目录)")
        return

    # 表格
    table_rows = []
    for r in rows:
        icon = {"dir": "📁", "file": "📄"}.get(r.get("type"), "❓")
        table_rows.append([
            f"{icon} {r.get('type', '?')}",
            r.get("name", ""),
            _human_size(r.get("size", 0)),
            _fmt_time(r.get("mtime", 0)),
            "⬇" if str(r.get("download", "0")) == "1" else "·",
        ])
    print_table(
        "明细",
        ["类型", "名称", "大小", "修改时间", "下载"],
        table_rows,
        aligns=["left", "left", "right", "left", "center"],
    )

    # 树形视图
    print_file_tree(f"树形 · {path}", rows)


def render_changefile(result, sent_data=None):
    """渲染 changefile（setwj）的返回值。"""
    if sent_data:
        print()
        print(f"📤 目标文件: {sent_data.get('wj')}")
        nr = sent_data.get("nr", "")
        print(f"📝 写入内容: {len(nr)} 字符 / {len(nr.encode('utf-8'))} 字节")
        # 内容预览（前 5 行）
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
        # 补充字段表
        print_table(
            "返回字段",
            ["字段", "值"],
            [[k, v] for k, v in result.items()],
            aligns=["left", "left"],
        )
    else:
        pp(result)


def render_generic(result):
    if isinstance(result, dict):
        ok = bool(result.get("success", True))
        print_status_banner(ok, result.get("code"), result.get("msg"),
                            result.get("redirect"))
        print_table(
            "返回字段",
            ["字段", "值"],
            [[k, v] for k, v in result.items()],
            aligns=["left", "left"],
        )
    else:
        pp(result)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    url = "https://m.luoli.love/user/ajax.php"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0",
    }
    cookies = {
        "user_token": os.getenv("AUTH_USER_TOKEN"),
        "PHPSESSID": os.getenv("AUTH_PHP_SESSION_TOKEN"),
    }

    data = build_request_data()
    if not data:
        raise SystemExit(
            "用法示例:\n"
            "  python xxx.py changefile /path/to/file.txt file.txt\n"
            "  python xxx.py listfile /\n"
            "  python xxx.py --gn setwj --wj /path/to/file.txt --nr \"Hello, world!\""
        )

    print(">>> 发送数据:")
    pp(data)

    try:
        resp = requests.post(url, headers=headers, cookies=cookies,
                             data=data, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print_status_banner(False, "网络错误", str(e))
        sys.exit(1)

    try:
        result = resp.json()
    except ValueError:
        print("响应不是合法 JSON:")
        print(resp.text)
        sys.exit(1)

    if not result:
        print_status_banner(False, "Request Failed", "服务端返回空响应")
        return

    # 按 gn 分派渲染器
    gn = data.get("gn")
    if gn == "listfile":
        render_listfile(result)
    elif gn == "setwj":
        render_changefile(result, data)
    else:
        render_generic(result)


if __name__ == "__main__":
    main()
