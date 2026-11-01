# MNBT CLI

由 DeepSeek 编写, 非官方项目, 主要用于不支持 FTP 的 MNBT 虚拟主机
若出事了, 使用者负全部责任

主要参数如下: `uv run mnbtcli `

- `changefilecontent`
- `listfile`
- `setfilename`
- `deletefile`
- `createfile`

## 登录

在使用之前, 请先登录.

在项目根目录上创建 `.env` 文件, 撰写如下内容:
```env
AUTH_PHP_SESSION_ID=你的SessionID
AUTH_USER_TOKEN=你的UserToken
```

两者的获取方式如下:
1. 在 `m.luoli.love` 登录账号
2. 打开 `F12`, 找到 `Applications` 或 `应用程序`
3. 找到 `Cookie`, 在下拉选项中找到 `https://m.luoli.love`
4. 其中 `PHPSESSID` 对应 `.env` 的 `AUTH_PHP_SESSION_ID`, `user_token` 对应 `AUTH_USER_TOKEN`
