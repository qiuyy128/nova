# nova
自动化运维管理平台，基于Django<br>
`项目来源于各种环境版本的自动化发布；后来逐渐添加了堡垒机的部分功能如webssh自动连接服务器；数据库脚本的提交、审核；web监控与自定义服务监控；nginx日志的查询统计；`<br>
 `django 1.10 + Mysql + Celery + Mongodb + GateOne.`<br>
集成GateOne, 服务器ssh连接，服务自动化部署，版本发布，任务管理与日志，数据库脚本执行，web监控，自定义服务监控，nginx日志查询统计。<br>
用户的管理与权限分配使用了django的admin后台来创建与管理。<br>
# 部署
安装依赖模块<br>
`pip install -r requirements.txt`<br>
创建admin用户：<br>
`python manage.py createsuperuser`<br>
运行app:<br>
`python manage.py runserver 0.0.0.0:端口号`<br>
运行celery worker：<br>
`celery -A nova worker --loglevel=info`<br>
运行celery beat：<br>
`celery -A nova beat`<br>
在admin后台创建普通用户，用户组，并赋予用户用户组的权限<br>
# 效果图
部署的应用列表<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获.JPG)
服务器列表<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获2.JPG)
应用从svn初始化部署<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获3.JPG)
应用每个环境不同的配置文件添加与查看
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
附件上传<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获12.JPG)
nginx访问日志查询统计，支持单项条件与组合条件查询（使用多进程每天定时处理nginx日志并存储至Mongodb）<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获13.JPG)
nginx访问日志查询统计<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获14.JPG)
添加用户组<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获15.JPG)
给用户赋权限<br>
![image](https://raw.githubusercontent.com/qiuyy128/nova/master/screenshoot/捕获16.JPG)
