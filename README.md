# nova
自动化运维管理平台，基于Django1.10，python2.7版本.<br>
`项目来源于各种环境版本的自动化发布；后来逐渐添加了堡垒机的部分功能如webssh自动连接服务器；数据库脚本的提交、审核；web监控与自定义服务监控；nginx日志的查询统计；`<br>
 `django 1.10 + Mysql + Celery + Mongodb + GateOne.`<br>

    集成GateOne, 服务器ssh连接，服务自动化部署，版本发布，任务管理与日志，数据库脚本执行，web监控，自定义服务监控，
    nginx日志查询统计。

用户的管理使用了django的admin后台来创建与管理，用户权限通过用户组来分配权限。

# 部署
安装依赖模块<br>

    pip install -r requirements.txt

创建admin用户：<br>

    python manage.py createsuperuser

修改配置文件configmodule.py：<br>

    通过配置NOVA_ENV环境变量来判断读取哪个环境对应的配置；
    修改数据库连接DATABASES；
    修改CELERY连接的Redis；
    修改代码签出的svn用户名与密码；
    ssh_key_password为'private_key'表示RunCmd使用公钥连接服务器；
    修改GATEONE服务器地址, API_KEY, SECRET（生产环境API_KEY与SECRET尽可能配置复杂）；
    nodejs应用与tomcat应用暂时都统一安装到/u01目录下。

配置GateOne：<br>
修改20authentication.conf通过API接口调用GateOne:

    "auth": "api",

修改10server.conf：<br>

    "origins": ["localhost:443", "127.0.0.1:443", "应用IP地址:应用端口号"],

修改30api_keys.conf：<br>

    "gateone": {
                "api_keys": {
                    "配置文件configmodule.py中的GATEONE_API_KEY值": "配置文件configmodule.py中的GATEONE_SECRET值"
                }
            }

Django集成GateOne部分见views.py中host_connect与get_auth_obj<br>
运行app:<br>

    python manage.py runserver 0.0.0.0:端口号

运行celery worker：<br>

    celery -A nova worker --loglevel=info

运行celery beat：<br>

    celery -A nova beat

在admin后台创建普通用户，用户组，并赋予用户用户组的权限<br>

Celery定时任务在setting中的CELERYBEAT_SCHEDULE进行配置<br>

发送邮件的配置在表nova_mail中进行配置<br>

附件目录attachment下的文件如jdk，tomcat，nodejs，ant等因为太大没有上传到github<br>

# 效果图
部署的应用列表<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获.JPG)
服务器列表<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获2.JPG)
应用从svn初始化部署，目前是从svn直接部署<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获3.JPG)
应用每个环境不同应用的配置文件添加与查看
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获4.JPG)
SQL提交<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获5.JPG)
SQL审核<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获6.JPG)
WEB监控<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获7.JPG)
监控历史曲线图<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获8.JPG)
自定义服务监控
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获9.JPG)
操作任务列表<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获10.JPG)
操作任务日志<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获11.JPG)
附件上传至阿里云OSS存储<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获12.JPG)
nginx访问日志查询统计，支持单项条件与组合条件查询（使用多进程每天定时处理nginx日志并存储至Mongodb）<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获13.JPG)
nginx访问日志查询统计<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获14.JPG)
添加用户组<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获15.JPG)
给用户赋权限<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获16.JPG)
点击连接其他linux服务器<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获17.JPG)
跳转到该linux服务器的webssh界面（GateOne）<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获18.JPG)
自动登陆到该linux服务器<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获19.JPG)
地图数据实时展示<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获20.jpg)
