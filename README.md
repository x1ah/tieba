# tieba

 百度贴吧签到脚本

## 使用方法

1. 登录 [网页版贴吧](https://tieba.baidu.com/)
2. 找到名为 `BDUSS` 的 cookie，填入到脚本中
3. 安装依赖: `pip install -r requirements.txt`
4. 运行脚本: `python tieba.py`

## 示例配置

```python

if __name__ == "__main__":
    cli = Tieba("<BDUSS cookie 值>", [
        LarkChannel("<飞书 webhook>"),
        WorkWechatBotChannel("<企业微信机器人 key>"),
    ])
    for task in [
        LikeHotForums(cli=cli), # 每天关注新贴吧
        SignForums(cli=cli)     # 自动签到已经关注的贴吧
    ]:
        task.run()
```

## 支持的运行结果通知

- 飞书自定义机器人
- 企业微信机器人

