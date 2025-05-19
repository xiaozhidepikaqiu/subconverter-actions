# subconverterONactions_pushTOkv

利用GithubActions：构建环境，运行订阅转换工具[subconverter](https://github.com/tindy2013/subconverter)；执行Python进行订阅转换，同时推送到cf kv。

这里采用的是[asdlokj1qpi233/subconverter](https://github.com/asdlokj1qpi233/subconverter)的fork版本，其支持Hysteria2协议。

?target=clash&url=&insert=false&config=&tls13=true&emoji=true&list=false&xudp=true&udp=true&tfo=true&expand=true&scv=true&fdn=false&clash.doh=true&new_name=true

## 使用步骤

1.  Fork 本仓库

2.  在你自己 Fork 的仓库进行设置`Settings - Actions - General - Allow all actions and reusable workflows`，别忘了`save`

3.  在Cloudflare`计算(Workers) - Workers 和 Pages`中创建一个`从 Hello World! 开始`的worker。完成后进行`代码编辑`把原内容用cf_worker.js的文件内容替换掉

4.  为worker设置`变量和机密`作为访问token(注意设置的值名称要和cf_worker.js中的对应)

5.  然后`Settings - Secrets - Actions - New repository secret`，按下面例子新建几个`secrets`：

    | secrets Name               | Value                                                        |
    | ----------------           | ------------------------------------------------------------ |
    | `PERSONAL_TOKEN`           | Github Personal Access Token（[在此创建](https://github.com/settings/tokens/new?scopes=gist&description=subconverter-action)） |
    | `CF_ACCOUNT_ID`            | Cloudflare账户id                                             |
    | `CF_ACCOUNT_API_TOKEN`     | Cloudflare账户api令牌                                        |
    | `CF_KV_ID`                 | 与worker绑定的kv id                                           |
    | `CONVERT_PARAM`            | 配置参数                                                     |

    1.   `PERSONAL_TOKEN`：个人访问令牌，没啥好说的。
  
    2.   `CF_ACCOUNT_ID`：登陆Cloudflare在`账户主页`复制账户ID
      
    3.   `CF_ACCOUNT_API_TOKEN`：先在`管理账户 - 账户API令牌 - 创建令牌`创建一个有Workers KV存储权限的令牌，创建后复制token
  
    4.   `CF_KV_ID`：在`存储和数据库 - KV`中创建kv，后到`计算(Workers) - Workers 和 Pages`中为worker添加kv绑定(注意设置的值名称要和cf_worker.js中的对应)。复制kv id作为值

    5.   `CONVERT_PARAM`：这个比较复杂，是下述json格式的base64编码。`key`是推送至kv的键名，`value`值是通过在线订阅转换前端生成的后端参数。

        json
        {"sub1.yml": "?target=clash&insert=false&exclude=%E5%A5%97%E9%A4%90%E5%88%B0%E6%9C%9F%7C%E8%8A%82%E7%82%B9%E8%B6%85%E6%97%B6%7C%E6%9B%B4%E6%8D%A2%7C%E5%89%A9%E4%BD%99%E6%B5%81%E9%87%8F%7C%E5%88%B0%E6%9C%9F%E6%97%B6%E9%97%B4%7CTG%E7%BE%A4%7C%E5%AE%98%E7%BD%91&interval=259200&emoji=true&list=true&xudp=false&udp=true&tfo=false&expand=true&scv=true&fdn=false&new_name=true&url=SUBURL", "sub2.yml": "?target=clash&insert=false&exclude=%E5%A5%97%E9%A4%90%E5%88%B0%E6%9C%9F%7C%E8%8A%82%E7%82%B9%E8%B6%85%E6%97%B6%7C%E6%9B%B4%E6%8D%A2%7C%E5%89%A9%E4%BD%99%E6%B5%81%E9%87%8F%7C%E5%88%B0%E6%9C%9F%E6%97%B6%E9%97%B4%7CTG%E7%BE%A4%7C%E5%AE%98%E7%BD%91&interval=259200&emoji=true&list=true&xudp=false&udp=true&tfo=false&expand=true&scv=true&fdn=false&new_name=true&url=SUBURL"}
        

        在线转换生成的订阅链接，sub之后的参数即为value（**包含?号**）

   6.   访问cf给的地址加上后缀  ?token=123456789  （比如subconverterONactions_pushTOkv_token=123456789）(注意设置的值名称要和cf_worker.js中的对应)即可使用
