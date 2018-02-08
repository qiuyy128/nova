#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 发票入库情况
sql_fprkqk1 = "SELECT count(1) FROM cy_cyrz"
sql_fprkqk2 = "SELECT count(1) FROM cy_cyrz WHERE qy like %s".encode('utf-8')
sql_fprkqk3 = "SELECT count(1) FROM cy_cyrz WHERE qy not like %s".encode('utf-8')
sql_fprkqk4 = "SELECT count(1) FROM cy_cyrz where cyrq BETWEEN %s and %s"
sql_fprkqk5 = "SELECT count(1) FROM cy_cyrz where cyrq BETWEEN %s and %s and qy like %s".encode('utf-8')
sql_fprkqk6 = "SELECT count(1) FROM cy_cyrz where cyrq BETWEEN %s and %s and qy not like %s".encode('utf-8')

# 营收情况
sql_ysqk_jfcs = """
select count(1) from fpcy_requeststatistics_log where requestStatus in('001','002','201','220') and
 inputTime BETWEEN %s AND %s"""
sql_ysqk_xfds_sk = """
SELECT ifnull(SUM(expense),0) expense FROM charging_record_charging WHERE chargingTime BETWEEN %s AND %s and productId = 'vat'
"""
sql_ysqk_czje = """
select IFNULL(SUM(totalAmount),0) from order_information a, order_goods b where a.orderId = b.orderId and b.goodsId in 
('sp1722874001', 'sp1722874002', 'sp1722874003', 'sp1722874004', 'sp1722874005', 'sp1722874006', 'sp1722874007', 'sp1722874008', 'sp1722874009', 'sp1722874010')
and a.orderState = '90' and a.inputTime BETWEEN %s AND %s
"""

##用户反馈情况表
sql_yhcyfkqkb = """
SELECT sum(a.cnt1) a1,sum(a.cnt2) a2,sum(a.cnt3) a3,CONCAT(ROUND(sum(a.cnt3)/sum(a.cnt2)*100,2),'%%') a4,sum(a.cnt4) a5,CONCAT(ROUND(sum(a.cnt4)/sum(a.cnt2)*100,2),'%%') a6,sum(a.cnt5) a7,
CONCAT(ROUND(sum(a.cnt5)/sum(a.cnt2)*100,2),'%%') a8,
sum(a.cnt6) a9,sum(a.cnt7) a10 from (
-- 用户查验请求次数
select count(1) cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7 from fpcy_requeststatistics_log where inputTime BETWEEN %s AND %s
-- GROUP BY comeFromCode
UNION
-- 有效请求次数
select 0 cnt1,count(1) cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7 from fpcy_requeststatistics_log where requestStatus not in('203','210','211','219','221') and
 inputTime BETWEEN %s AND %s
-- GROUP BY comeFromCode
UNION
-- 有效反馈次数
select 0 cnt1,0 cnt2,count(1) cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7 from fpcy_requeststatistics_log where requestStatus not in('203','210','211','219','221','212','213','231','232') and
 inputTime BETWEEN %s AND %s
UNION
-- 15秒内反馈成功次数（计费次数）
select 0 cnt1,0 cnt2,0 cnt3,count(1) cnt4,0 cnt5,0 cnt6,0 cnt7 from fpcy_requeststatistics_log where requestStatus in('001','002','201','220','204','206','215') and
 inputTime BETWEEN %s AND %s
UNION
-- 反馈发票明细次数（<=15秒）
select 0 cnt1,0 cnt2,0 cnt3,0 cnt4,count(1) cnt5,0 cnt6,0 cnt7 from fpcy_requeststatistics_log where requestStatus in('001','002') and
 inputTime BETWEEN %s AND %s
UNION
-- 反馈发票明细张数
select 0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,count(DISTINCT(CONCAT(fpdm,fphm))) cnt6,0 cnt7 from fpcy_requeststatistics_log where requestStatus in('001','002') and
 inputTime BETWEEN %s AND %s
UNION
-- 向核心请求次数
SELECT 0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,SUM(a) cnt7 FROM (
 SELECT count(1) as a from cy_cwrz WHERE cyrq BETWEEN %s AND %s UNION ALL
  SELECT count(1) as a from cy_cyrz WHERE cyrq BETWEEN %s AND %s) q
)
a
""".encode('utf-8')

##子产品情况表
sql_zcpcyqk = """
SELECT CASE a.comeFromCode
 WHEN '3' THEN '免费web'
 WHEN '1' THEN '收费web端'
 WHEN '2' THEN '收费微信端'
 WHEN '4' THEN '免费微信端'
 WHEN '5' THEN '风控系统'
 WHEN '6' THEN '企业接口'
 WHEN '7' THEN '代账平台'
 WHEN '8' THEN 'demo接口'
 WHEN '9' THEN '影像系统'
 END AS 请求端,sum(a.cnt1) a1,sum(a.cnt2) a2,sum(a.cnt3) a3,CONCAT(ROUND(sum(a.cnt3)/sum(a.cnt2)*100,2),'%%') a4,sum(a.cnt4) a5,CONCAT(ROUND(sum(a.cnt4)/sum(a.cnt2)*100,2),'%%') a6,sum(a.cnt5) a7,
CONCAT(ROUND(sum(a.cnt5)/sum(a.cnt2)*100,2),'%%') a8,sum(a.cnt6) a9 from (
-- 用户查验请求次数
select count(1) cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,comeFromCode from fpcy_requeststatistics_log where inputTime BETWEEN %s AND %s
 GROUP BY comeFromCode
UNION
-- 有效请求次数
select 0 cnt1,count(1) cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,comeFromCode from fpcy_requeststatistics_log where requestStatus not in('203','210','211','219','221') and
 inputTime BETWEEN %s AND %s
 GROUP BY comeFromCode
UNION
-- 有效反馈次数
select 0 cnt1,0 cnt2,count(1) cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,comeFromCode from fpcy_requeststatistics_log where requestStatus not in('203','210','211','219','221','212','213','231','232') and
 inputTime BETWEEN %s AND %s
 GROUP BY comeFromCode
UNION
-- 15秒内反馈成功次数（计费次数）
select 0 cnt1,0 cnt2,0 cnt3,count(1) cnt4,0 cnt5,0 cnt6,0 cnt7,comeFromCode from fpcy_requeststatistics_log where requestStatus in('001','002','201','220','204','206','215') and
 inputTime BETWEEN %s AND %s
 GROUP BY comeFromCode
UNION
-- 反馈发票明细次数（<=15秒）
select 0 cnt1,0 cnt2,0 cnt3,0 cnt4,count(1) cnt5,0 cnt6,0 cnt7,comeFromCode from fpcy_requeststatistics_log where requestStatus in('001','002') and
 inputTime BETWEEN %s AND %s
 GROUP BY comeFromCode
UNION
-- 反馈发票明细张数
select 0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,count(DISTINCT(CONCAT(fpdm,fphm))) cnt6,0 cnt7,comeFromCode from fpcy_requeststatistics_log where requestStatus in('001','002') and
 inputTime BETWEEN %s AND %s
  GROUP BY comeFromCode
)
a
 GROUP BY a.comeFromCode order by a1 DESC
""".encode('utf-8')

# 企业接口查验情况
sql_qyjkcyqk_qymc = """
select enterpriseName,telephone from open_app where userCode = %s
"""
sql_qyjkcyqk = """
SELECT customerId,sum(a.cnt1) a1,sum(a.cnt2) a2,sum(a.cnt3) a3,CONCAT(ROUND(sum(a.cnt3)/sum(a.cnt2)*100,2),'%%') a4,sum(a.cnt4) a5,CONCAT(ROUND(sum(a.cnt4)/sum(a.cnt2)*100,2),'%%') a6,sum(a.cnt5) a7,
CONCAT(ROUND(sum(a.cnt5)/sum(a.cnt2)*100,2),'%%') a8,
sum(a.cnt6) a9 from (
-- 用户查验请求次数
select count(1) cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,customerId from vat_requeststatistics_log where inputTime BETWEEN %s AND %s
and comeFromCode='6'
GROUP BY customerId
UNION
-- 有效请求次数
select 0 cnt1,count(1) cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,customerId from vat_requeststatistics_log where requestStatus not in('203','219','221','211','230','240') and
 inputTime BETWEEN %s AND %s
and comeFromCode='6'
GROUP BY customerId
UNION
-- 有效反馈次数
select 0 cnt1,0 cnt2,count(1) cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,customerId from vat_requeststatistics_log where requestStatus not in('203','219','221','213','211','230','240') and
 inputTime BETWEEN %s AND %s
and comeFromCode='6'
GROUP BY customerId
UNION
-- 15秒内反馈成功次数（计费次数）
select 0 cnt1,0 cnt2,0 cnt3,count(1) cnt4,0 cnt5,0 cnt6,0 cnt7,customerId from vat_requeststatistics_log where requestStatus in('1000','201','220') and
 inputTime BETWEEN %s AND %s
and comeFromCode='6'
GROUP BY customerId
UNION
-- 反馈发票明细次数（<=15秒）
select 0 cnt1,0 cnt2,0 cnt3,0 cnt4,count(1) cnt5,0 cnt6,0 cnt7,customerId from vat_requeststatistics_log where requestStatus in('1000') and
 inputTime BETWEEN %s AND %s
and comeFromCode='6'
GROUP BY customerId
UNION
-- 反馈发票明细张数
select 0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,count(DISTINCT(CONCAT(fpdm,fphm))) cnt6,0 cnt7,customerId from vat_requeststatistics_log where requestStatus in('1000') and
 inputTime BETWEEN %s AND %s
and comeFromCode='6'
GROUP BY customerId
)
a GROUP BY a.customerId order by a1 DESC
""".encode('utf-8')
# 企业接口查验情况 -> 来源计费系统（charging）
sql_qyjkcyqk_xfds_sk = """
SELECT a.userCode,IFNULL(sum(a.expense),0) cnt from charging_record_charging a
            where a.serviceCode='getInvoiceInfoForCom'
            and a.chargingTime between %s AND %s and a.userCode=%s
"""

# 核心服务状态表
sql_hxfwztb = """
SELECT a.invoiceName,sum(a.cnt1) a1,sum(a.cnt2) a2,CONCAT(ROUND(sum(a.cnt2)/sum(a.cnt1)*100,2),'%%') a3,sum(a.cnt3) a4,CONCAT(ROUND(sum(a.cnt3)/sum(a.cnt1)*100,2),'%%') a5,
sum(a.cnt4) a6,CONCAT(ROUND(sum(a.cnt4)/sum(a.cnt1)*100,2),'%%') a7,sum(a.cnt5) a8,CONCAT(ROUND(sum(a.cnt5)/sum(a.cnt1)*100,2),'%%') a9,
sum(a.cnt6) a10,sum(a.cnt7) a11 from (
-- 请求次数
SELECT q.invoiceName,SUM(q.a) cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7 FROM (
 SELECT count(1) as a,SUBSTR(qy,1,6) invoiceName from cy_cwrz WHERE cyrq BETWEEN %s AND %s
 GROUP BY invoiceName
UNION ALL
  SELECT count(1) as a,SUBSTR(qy,1,6) invoiceName from cy_cyrz WHERE cyrq BETWEEN %s AND %s
 GROUP BY invoiceName
) q
GROUP BY q.invoiceName
UNION
-- 有效反馈次数（<=60秒）
SELECT  q.invoiceName,0 cnt1,SUM(a) cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7 FROM (
 SELECT count(1) as a,SUBSTR(qy,1,6) invoiceName from cy_cwrz  WHERE cyrq BETWEEN %s AND %s
 and invoicefalseState not in('203','210','212','211','219','221','213','231','232') and CAST(useTime AS UNSIGNED)/1000<=60
 GROUP BY invoiceName
 UNION ALL
  SELECT count(1) as a,SUBSTR(qy,1,6) invoiceName from cy_cyrz WHERE cyrq BETWEEN %s AND %s
   and CAST(useTime AS UNSIGNED)/1000<=60
 GROUP BY invoiceName
) q
 GROUP BY q.invoiceName
UNION
-- 10秒内反馈次数
SELECT  q.invoiceName,0 cnt1,0 cnt2,SUM(a) cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7 FROM (
 SELECT count(1) as a,SUBSTR(qy,1,6) invoiceName from cy_cwrz  WHERE cyrq BETWEEN %s AND %s
 and invoicefalseState not in('203','210','212','211','219','221','213','231','232') and CAST(useTime AS UNSIGNED)/1000<=10
 GROUP BY invoiceName
 UNION ALL
  SELECT count(1) as a,SUBSTR(qy,1,6) invoiceName from cy_cyrz WHERE cyrq BETWEEN %s AND %s
   and CAST(useTime AS UNSIGNED)/1000<=10
 GROUP BY invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 反馈发票明细次数（<=60秒）
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,SUM(a) cnt4,0 cnt5,0 cnt6,0 cnt7 FROM (
  SELECT count(1) as a,SUBSTR(qy,1,6) invoiceName from cy_cyrz WHERE cyrq BETWEEN %s AND %s
   and CAST(useTime AS UNSIGNED)/1000<=60
 GROUP BY invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 反馈发票明细次数（<=10秒）
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,SUM(a) cnt5,0 cnt6,0 cnt7 FROM (
  SELECT count(1) as a,SUBSTR(qy,1,6) invoiceName from cy_cyrz WHERE cyrq BETWEEN %s AND %s
   and CAST(useTime AS UNSIGNED)/1000<=10
 GROUP BY invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 反馈发票明细张数
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,SUM(a) cnt6,0 cnt7 FROM (
  SELECT count(1) as a,SUBSTR(qy,1,6) invoiceName from cy_cyrz WHERE cyrq BETWEEN %s AND %s
 GROUP BY invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 查票请求次数
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,SUM(a) cnt7 FROM (
  SELECT count(1) as a,SUBSTR(invoiceName,1,6) invoiceName from fpcy_request_log WHERE inputTime BETWEEN %s AND %s
  and requestType='cy'
 GROUP BY invoiceName
) q
 GROUP BY  q.invoiceName
)a
GROUP BY  a.invoiceName order by a1 DESC
""".encode('utf-8')

##税局查验服务状态表
sql_sjcyfwztb = """
SELECT a.invoiceName,sum(a.cnt1) a1,sum(a.cnt2) a2,CONCAT(ROUND(sum(a.cnt2)/sum(a.cnt1)*100,2),'%%') a3,sum(a.cnt3) a4,CONCAT(ROUND(sum(a.cnt3)/sum(a.cnt1)*100,2),'%%') a5,sum(a.cnt4) a6,
sum(a.cnt5) a7,CONCAT(ROUND(sum(a.cnt5)/sum(a.cnt4)*100,2),'%%') a8,sum(a.cnt6) a9,CONCAT(ROUND(sum(a.cnt6)/sum(a.cnt4)*100,2),'%%') a10,
sum(a.cnt7) a11,sum(a.cnt8) a12,sum(a.cnt9) a13,sum(a.cnt10) a14,CONCAT(ROUND(1*100,2),'%%') a15,CONCAT(ROUND(sum(a.cnt9)/sum(a.cnt7)*100,2),'%%') a16,
sum(a.cnt11) a17,
-- sum(a.cnt11)/sum(a.cnt7) a17,sum(a.cnt11+a.cnt10)/sum(a.cnt7) a18,
CONCAT(ROUND(sum(a.cnt11)/sum(a.cnt9)*100,2),'%%') a18 from (
-- 1查票请求次数
SELECT q.invoiceName,SUM(q.a) cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,0 cnt8,0 cnt9,0 cnt10,0 cnt11 FROM (
  SELECT count(1) as a,SUBSTR(invoiceName,1,6) invoiceName from fpcy_request_log WHERE inputTime BETWEEN %s AND %s
  and requestType='cy'
  GROUP BY invoiceName
) q
GROUP BY q.invoiceName
UNION
-- 2有效反馈次数（<=10秒）
SELECT  q.invoiceName,0 cnt1,SUM(a) cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,0 cnt8,0 cnt9,0 cnt10,0 cnt11 FROM (
 SELECT count(1) as a,SUBSTR(invoiceName,1,6) invoiceName from fpcy_request_log WHERE inputTime BETWEEN %s AND %s
  and requestType='cy' and isSuccess='Y' and CAST(requestTime AS UNSIGNED)/1000<=10
  GROUP BY invoiceName
) q
 GROUP BY q.invoiceName
UNION
-- 3 1秒内反馈次数
SELECT  q.invoiceName,0 cnt1,0 cnt2,SUM(a) cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,0 cnt8,0 cnt9,0 cnt10,0 cnt11 FROM (
 SELECT count(1) as a,SUBSTR(invoiceName,1,6) invoiceName from fpcy_request_log WHERE inputTime BETWEEN %s AND %s
  and requestType='cy' and isSuccess='Y' and CAST(requestTime AS UNSIGNED)/1000<=1
 GROUP BY invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 4 请求验证码次数
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,SUM(a) cnt4,0 cnt5,0 cnt6,0 cnt7,0 cnt8,0 cnt9,0 cnt10,0 cnt11 FROM (
 SELECT count(1) as a,SUBSTR(invoiceName,1,6) invoiceName from fpcy_request_log WHERE inputTime BETWEEN %s AND %s
  and requestType='yzm'
  GROUP BY invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 5请求验证码成功次数（<=5秒）
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,SUM(a) cnt5,0 cnt6,0 cnt7,0 cnt8,0 cnt9,0 cnt10,0 cnt11 FROM (
  SELECT count(1) as a,SUBSTR(invoiceName,1,6) invoiceName from fpcy_request_log WHERE inputTime BETWEEN %s AND %s
  and requestType='yzm' and isSuccess='Y' and CAST(requestTime AS UNSIGNED)/1000<=5
  GROUP BY invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 6请求验证码成功次数（<=1秒）
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,SUM(a) cnt6,0 cnt7,0 cnt8,0 cnt9,0 cnt10,0 cnt11 FROM (
   SELECT count(1) as a,SUBSTR(invoiceName,1,6) invoiceName from fpcy_request_log WHERE inputTime BETWEEN %s AND %s
  and requestType='yzm' and isSuccess='Y' and CAST(requestTime AS UNSIGNED)/1000<=1
  GROUP BY invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 7打码次数
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,SUM(a) cnt7,0 cnt8,0 cnt9,0 cnt10,0 cnt11 FROM (
  SELECT count(1) as a,SUBSTR(b.invoiceName,1,6) invoiceName from ocr_request_log a
  LEFT JOIN fpcy_request_log b on b.requestId=a.requestId
 WHERE a.inputTime BETWEEN %s AND %s
 GROUP BY b.invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 8打码成功响应次数（<=6秒）
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,SUM(a) cnt8,0 cnt9,0 cnt10,0 cnt11 FROM (
  SELECT count(1) as a,SUBSTR(b.invoiceName,1,6) invoiceName from ocr_request_log a
  LEFT JOIN fpcy_request_log b on b.requestId=a.requestId
 WHERE a.inputTime BETWEEN %s AND %s
 and CAST(dateLength AS UNSIGNED)/1000<=6
 GROUP BY b.invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 9打码成功次数（已使用）
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,0 cnt8,SUM(a) cnt9,0 cnt10,0 cnt11 FROM (
  SELECT count(1) as a,SUBSTR(b.invoiceName,1,6) invoiceName from ocr_request_log a
  LEFT JOIN fpcy_request_log b on b.requestId=a.requestId
 WHERE a.inputTime BETWEEN %s AND %s
 AND isRight is not null
 GROUP BY b.invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 10 打码成功次数（未使用）
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,0 cnt8,0 cnt9,SUM(a) cnt10,0 cnt11 FROM (
  SELECT count(1) as a,SUBSTR(b.invoiceName,1,6) invoiceName from ocr_request_log a
  LEFT JOIN fpcy_request_log b on b.requestId=a.requestId
 WHERE a.inputTime BETWEEN %s AND %s
 AND isRight is null
 GROUP BY b.invoiceName
) q
 GROUP BY  q.invoiceName
UNION
-- 11 打码正确次数
SELECT  q.invoiceName,0 cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5,0 cnt6,0 cnt7,0 cnt8,0 cnt9,0 cnt10,SUM(a) cnt11 FROM (
  SELECT count(1) as a,SUBSTR(b.invoiceName,1,6) invoiceName from ocr_request_log a
  LEFT JOIN fpcy_request_log b on b.requestId=a.requestId
 WHERE a.inputTime BETWEEN %s AND %s
 AND isRight ='Y'
 GROUP BY b.invoiceName
) q
 GROUP BY  q.invoiceName
)a
GROUP BY  a.invoiceName
""".encode('utf-8')

###打码情况
sql_dmqk = """
SELECT a.company a1,sum(a.cnt1) a2,sum(a.cnt2) a3,sum(a.cnt3) a4,sum(a.cnt4) a5,CONCAT(ROUND(1*100,2),'%%') a6,CONCAT(ROUND(sum(a.cnt3)/sum(a.cnt1)*100,2),'%%') a7,
sum(a.cnt5) a8,CONCAT(ROUND(sum(a.cnt5)/sum(a.cnt3)*100,2),'%%') a9  from (
-- 1 打码次数
SELECT  q.company,SUM(q.a) cnt1,0 cnt2,0 cnt3,0 cnt4,0 cnt5 FROM (
 SELECT count(1) as a,a.company from ocr_request_log a
 WHERE a.inputTime BETWEEN %s AND %s
GROUP BY  a.company
) q
GROUP BY  q.company
UNION
-- 2打码成功响应次数（<=6秒）
SELECT   q.company,0 cnt1,SUM(a) cnt2,0 cnt3,0 cnt4,0 cnt5 FROM (
  SELECT count(1) as a,a.company from ocr_request_log a
 WHERE a.inputTime BETWEEN %s AND %s
 and CAST(dateLength AS UNSIGNED)/1000<=6
GROUP BY  a.company
) q
GROUP BY  q.company
UNION
-- 3打码成功次数（已使用）
SELECT  q.company,0 cnt1,0 cnt2,SUM(a) cnt3,0 cnt4,0 cnt5 FROM (
  SELECT count(1) as a,a.company from ocr_request_log a
 WHERE a.inputTime BETWEEN %s AND %s
 AND a.isRight is not null
GROUP BY  a.company
) q
GROUP BY  q.company
UNION
-- 4 打码成功次数（未使用）
SELECT   q.company,0 cnt1,0 cnt2,0 cnt3,SUM(a) cnt4,0 cnt5 FROM (
  SELECT count(1) as a,a.company from ocr_request_log a
 WHERE a.inputTime BETWEEN %s AND %s
AND a.isRight  is null
GROUP BY  a.company
) q
GROUP BY  q.company
UNION
-- 5 打码正确次数
SELECT  q.company,0 cnt1,0 cnt2,0 cnt3,0 cnt4,SUM(a) cnt5 FROM (
  SELECT count(1) as a,a.company from ocr_request_log a
 WHERE a.inputTime BETWEEN %s AND %s
 AND a.isRight ='Y'
GROUP BY  a.company
) q
GROUP BY  q.company
)a
GROUP BY  a.company
""".encode('utf-8')

### 税局响应情况（>60秒）
sql_sjxyqk = """
 select t1.invoiceName ,t1.a,t2.b from
(SELECT invoiceName,AVG(CAST(requestTime AS UNSIGNED))/1000 AS a FROM fpcy_request_log WHERE inputTime BETWEEN %s and %s
AND requestType='yzm'  GROUP BY invoiceName ) t1 ,
(SELECT invoiceName,AVG(CAST(requestTime AS UNSIGNED))/1000 AS b FROM fpcy_request_log WHERE inputTime BETWEEN %s and %s
AND requestType='cy'  GROUP BY invoiceName )t2
where t1.invoiceName=t2.invoiceName AND CAST(t1.a+t2.b AS UNSIGNED)>60 ORDER BY t1.a+t2.b desc limit 10
""".encode('utf-8')

# 用户查验请求详情
sql_yhcyqqxq = """
SELECT
 a.requestStatus a1,
 count(*) a2,
 b.returnMsg a3,
 b.ifValid a4,
 b.ifSucceed a5,
 b.ifCharging a6
FROM
 fpcy_requeststatistics_log a
LEFT JOIN fpcy_return_code b ON a.requestStatus = b.returnCode
WHERE
 a.inputTime BETWEEN %s AND %s
GROUP BY
 a.requestStatus
"""
# 税局查验请求详情
sql_sjcyqqxq = """
SELECT
 invoicefalseState a1,
 count(1) a2,
 b.returnMsg a3,
 b.ifValid a4,
 b.ifSucceed a5,
 b.ifCharging a6
FROM
 cy_cwrz a
LEFT JOIN fpcy_return_code b ON a.invoicefalseState = b.returnCode
WHERE
 cyrq BETWEEN %s AND %s
GROUP BY
 invoicefalseState
"""
