import smtplib
from email.mime.text import MIMEText
from email.header import Header
import json
import re
import requests
from bs4 import BeautifulSoup
import schedule
import time
import datetime
import pymysql

#发送邮件
def send_email(current_time, smtp_host, smtp_port, username, password, sender, receivers, subject, body):
    message = MIMEText(body, 'plain', 'utf-8')
    message['From'] = Header(sender)
    message['To'] = Header(', '.join(receivers))
    message['Subject'] = Header(subject)

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(username, password)
            server.sendmail(sender, receivers, message.as_string())
            print(f"{current_time} 邮件发送成功")
    except Exception as e:
        print(f"{current_time} 邮件发送失败: {e}")
        
#邮件信息
def emailInfo(current_time, isSend_email, match_league, match_time, result, total_shooting, total_shootingOn, total_dangerous_attacks, total_shooting_set, total_shootingOn_set, total_dangerous_attacks_set, totalScore ,match_link):
    # 邮件信息
        smtp_host = 'smtp.qq.com'
        smtp_port = 465
        username = '1527474029@qq.com'
        password = 'qzuqttdgbtryihjc'
        sender = '1527474029@qq.com'
        receivers = ['1527474029@qq.com', 'yy119118@qq.com']
        subject = '测试邮件'
        html_link = f'<a href="{match_link}">{match_link}</a>'
        body = f'联赛：{match_league}\n\n比赛时间: {match_time}\n\n比赛场次:{result.strip()}\n\n比赛信息:\n射门次数总和:{total_shooting}\n射正次数总和:{total_shootingOn}\n危险进攻次数总和:{total_dangerous_attacks}\n比赛链接:{html_link}'
        if isSend_email == 1:
        # 发送邮件
          send_email(current_time, smtp_host, smtp_port, username, password, sender, receivers, subject, body)

#连接数据库
def connect_to_database():
    connection = pymysql.connect(
        host="localhost",
        user="root",
        password="caizhaoping525",
        database="python",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

#获取已经发送过邮件的比赛
def get_isSend_match():
  try:
    connection = connect_to_database()
    cursor = connection.cursor()
    table_name = "match"
    query = f"SELECT `match_id` FROM `{table_name}`"
    cursor.execute(query)
    result = [row['match_id'] for row in cursor.fetchall() or []]
    cursor.close()
    connection.close()
    return result
  except Exception as e:
        print(f"获取已经发送过邮件的比赛Error: {e}")
        return []

#插入数据库
def insert_data(current_time, web_url, match_league, match_time, result, total_shooting, total_shootingOn, total_dangerous_attacks, match_link):
    connection = connect_to_database()
    cursor = connection.cursor()
    table_name = "match"
    query = f"INSERT INTO `{table_name}` (`match_id`,`match_league`,`match_time`,`match_name`,`total_shooting`,`total_shootingOn`,`total_dangerous_attacks`,`match_link`) VALUES ('{web_url}','{match_league}','{match_time}','{result}','{total_shooting}','{total_shootingOn}','{total_dangerous_attacks}','{match_link}')"#插入数据
    cursor.execute(query)
    connection.commit()
    cursor.close()
    connection.close()
    print(f"{current_time} 插入成功")

#插入联赛
def insert_leagues(leagues):
    connection = connect_to_database()
    cursor = connection.cursor()
    table_name = "league"
    for league in leagues:
      cursor.execute(f"INSERT INTO `{table_name}` (`league_name`,`is_filter`) VALUES ('{league}',0)")
    connection.commit()
    connection.close()

#获取比赛场次    
def scrape_data(current_time):
    current_time = datetime.datetime.now()
    new_time = current_time - datetime.timedelta(hours=10)# 减去十个小时
    formatted_date = new_time.strftime("%Y-%m-%d")
    url = f"http://m.titan007.com/Schedule.htm?date={formatted_date}"
    headers = {
        'User-Agent': 'PostmanRuntime/7.35.0',
    }

    try:
        # Use headers in the initial request
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Check if there is an error in the response

        soup = BeautifulSoup(response.content, "html.parser")
        pattern = re.compile(r'var\s+scheduleDataStr\s*=\s*["\'](.*?)["\']')
        match = pattern.search(str(soup))

        if match:
            schedule_data_str = match.group(1)
            split_data = schedule_data_str.split('!')
            result = []

            for item in split_data:
                values = item.split('^')
                if len(values) >= 2:
                    result.append({values[0]: values[3]})

            # Convert result to JSON format
            json_result = json.dumps(result, ensure_ascii=False)
            data = json.loads(json_result)
            current_time = datetime.datetime.now()
            formatted_time = current_time.strftime("%Y%m%d%H%M")
            target_date = int(formatted_time)
            converted_data = [{key: value[:-2]} for item in data for key, value in item.items()]
            filtered_data = [item for item in converted_data if int(list(item.values())[0]) <= target_date]
            target_date = datetime.datetime.strptime(str(target_date), '%Y%m%d%H%M')
            
            filtered_data1 = [
                {key: value for key, value in item.items() 
                    if target_date > datetime.datetime.strptime(str(value), '%Y%m%d%H%M') > target_date - datetime.timedelta(minutes=75)}
                for item in filtered_data
                    if any(item.values())
            ]
            
            filtered_data2 = [item for item in filtered_data1 if any(item.values())]
            keys_list = [list(item.keys())[0] for item in filtered_data2]
            return keys_list

        else:
            print(f"{current_time} 获取比赛场次失败")
            return []  # Add a return statement here

    except requests.exceptions.RequestException as e:
        print(f"{current_time} 获取比赛场次 error : {e}")
        return []  # Add a return statement here
  
#处理数据    
def crawl_data(current_time, web_url, total_shooting_setting, total_shootingOn_setting, total_dangerous_attacks_setting, differ_shooting_setting, differ_dangerous_attacks_setting, filter_leagues):
    # print(f"开始爬取http://m.titan007.com/Analy/ShiJian/{web_url}.htm的数据")
    url = f'http://m.titan007.com/Analy/ShiJian/{web_url}.htm'
    # url = 'http://m.titan007.com/Analy/ShiJian/2437281.htm'
    
    headers = {
        'User-Agent': 'PostmanRuntime/7.35.0',
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        league_div = soup.find('div', class_='league')
        league_text = league_div.get_text().strip().replace('&nbsp', ' ')#获取比赛联赛和时间
        match_league = league_text.split()[0]#获取联赛名称
        match_time = f"{league_text.split()[1]} {league_text.split()[2]}"
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        keywords = keywords_tag.get('content')
        comma_index = keywords.find(",")
        football_index = keywords.find("足球")
        if comma_index != -1 and football_index != -1:
          result = keywords[comma_index + 1:football_index]
        else:
          print(f"{current_time} 获取不到比赛场次")
        
        if match_league in filter_leagues:
          print(f'{web_url}属于被忽略的联赛')
        else:
          def filter_techdata_scripts(tag):
              return tag.name == 'script' and 'techData' in tag.get_text()#只找上半场

          techdata_scripts = soup.find_all(filter_techdata_scripts)
          if not techdata_scripts:# 如果找不到techData代表上半场结束
            print(f'{web_url}没有上半场数据')
          else:
            for script in techdata_scripts:
              if 'techData' in script.text:# 检查每个脚本是否包含特定类型的脚本
                pattern = re.compile(r'var techData = ({.*?});', re.DOTALL)# 使用正则表达式提取 techData 的内容
                matches = pattern.search(script.text)
                if matches:
                  tech_data = matches.group(1)  # 匹配的 techData 内容
                  transformed_data = {}
                  if 'techStat' in tech_data:
                      data = json.loads(tech_data)
                      for item in data.get('techStat', {}).get('itemList', []):  # 遍历 techStat 中的 itemList
                          key = item['name']
                          if 'value' in item['home'] and 'value' in item['away']:
                              value_home = item['home']['value']
                              value_away = item['away']['value']
                              transformed_data[key] = [value_home, value_away]
                          else:
                              value_home = item['home']['value']
                              transformed_data[key] = value_home 
                  else:
                    print(f'{current_time} {web_url}上半场当前获取不到数据')
          # print(f"爬取http://m.titan007.com/Analy/ShiJian/{web_url}.htm的数据结束") 

          # 条件判断数据
          homeScore = soup.find('div', {'class': 'score', 'id': 'homeScore'})# 获取主队比分
          guestScore = soup.find('div', {'class': 'score', 'id': 'guestScore'})# 获取客队比分
          if homeScore is not None:
            home_score_text = homeScore.text
          else:
            home_score_text = 0
            print(f"{current_time} {web_url}比赛未开始")
          if guestScore is not None:
            guest_score_text = guestScore.text
          else:
            guest_score_text = 0
            print(f"{current_time} {web_url}比赛未开始")
          totalScore = home_score_text + guest_score_text# 获取总比分
          shooting_stats = transformed_data.get('射门', []) or transformed_data.get('射門', [])
          shootingOn_stats = transformed_data.get('射正', [])
          dangerous_attacks_stats = transformed_data.get('危险进攻', []) or transformed_data.get('危險進攻', [])
          total_shooting = sum(shooting_stats)# 射门总数
          differ_shooting = 0
          differ_dangerous_attacks = 0
          if shooting_stats:
            differ_shooting = abs(shooting_stats[0] - shooting_stats[1])# 射门差值
          else:
            print(f'{current_time} {web_url}没有射门数据')
          total_shootingOn = sum(shootingOn_stats)# 射正总数
          total_dangerous_attacks = sum(dangerous_attacks_stats)# 危险进攻总数
          if total_dangerous_attacks:
            differ_dangerous_attacks = abs(dangerous_attacks_stats[0] - dangerous_attacks_stats[1])# 危险进攻差值
          else:
            print(f'{current_time} {web_url}没有危险进攻数据')
          match_link = f'https://live.titan007.com/detail/{web_url}sb.htm' # 比赛链接
          print(f"{current_time} 获取http://m.titan007.com/Analy/ShiJian/{web_url}.htm的想要数据")     
          # 判断是否发送邮件
          if (int(total_shooting) >= int(total_shooting_setting) and int(total_shootingOn) >= int(total_shootingOn_setting) and int(total_dangerous_attacks) >= int(total_dangerous_attacks_setting) and totalScore == '00') or (int(differ_shooting) >= int(differ_shooting_setting) and int(differ_dangerous_attacks) >= int(differ_dangerous_attacks_setting) and totalScore == '00') :
             isSend_email = 1 
             print(f"{current_time}发送数据为{int(total_shooting)},{int(total_shooting_setting)},{int(total_shootingOn)},{int(total_shootingOn_setting)},{int(total_dangerous_attacks)},{int(total_dangerous_attacks_setting)},{totalScore} 或者{int(differ_shooting)},{int(differ_shooting_setting)},{int(differ_dangerous_attacks)},{int(differ_dangerous_attacks_setting)},{totalScore}")
             emailInfo(current_time, isSend_email, match_league, match_time, result, total_shooting, total_shootingOn, total_dangerous_attacks, total_shooting_setting, total_shootingOn_setting, total_dangerous_attacks_setting, totalScore ,match_link)
             emailInfo(current_time, isSend_email, match_league, match_time, result, total_shooting, total_shootingOn, total_dangerous_attacks, total_shooting_setting, total_shootingOn_setting, total_dangerous_attacks_setting, totalScore ,match_link)
             insert_data(current_time, web_url, match_league, match_time, result, total_shooting, total_shootingOn, total_dangerous_attacks, match_link)
            #  schedule.clear()
          else:
            print(f'{current_time} 本次爬取{web_url}比赛没有符合条件的数据')
    else:
        print('请求失败:', response.status_code)

#获取比赛设定
def getMatchSettings():
    try:
        connection = connect_to_database()
        cursor = connection.cursor()
        select_query = "SELECT * FROM match_setting"
        cursor.execute(select_query)
        result = cursor.fetchall()

        if len(result) > 0:
            return result[0]
        else:
            return []
    except Exception as e:
        print(f"获取比赛设定Error: {e}")
        return []

#获取所有联赛
def get_leagues():
  url = "http://m.titan007.com/Schedule.htm?date=2024-01-22"
  headers = {
        'User-Agent': 'PostmanRuntime/7.35.0',
    }
  response = requests.get(url, headers=headers)
  soup = BeautifulSoup(response.content, "html.parser")
  pattern = re.compile(r'var\s+scheduleDataStr\s*=\s*["\'](.*?)["\']')
  league_pattern = re.compile(r'var sclassDataStr = (.*?);', re.DOTALL)
  match = pattern.search(str(soup))# <re.Match object; span=(5305, 66524), match='var scheduleDataStr = "2512963^140^-1^20240120111>
  league_match = league_pattern.search(str(soup))
  league_split_data = []
  if league_match:
    league_data_str = league_match.group(1)
    league_split_data = [item.split('^')[0] for item in league_data_str.split('!')]
  return league_split_data

#获取被过滤的联赛
def get_filter_league():
    connection = connect_to_database()
    cursor = connection.cursor()
    select_query = "SELECT `league_name` FROM league WHERE is_filter = 1"
    cursor.execute(select_query)
    result = cursor.fetchall()
    result_as_list = [item[0] for item in result]
    if(len(result_as_list) != 0):
      return result_as_list
    else:
      return []
    
#过滤符合条件的url
def filter_url(matchUrl, match_time_setting):
    try:
      filtered_matches = []
      halfMatch = 0
      time_threshold = match_time_setting #比赛前20分钟
      for match in matchUrl:
        url = f'http://m.titan007.com/Analy/ShiJian/{match}.htm'
        headers = {
            'User-Agent': 'PostmanRuntime/7.35.0',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        span_element = soup.find('span', {'id': 'timeMini', 'class': 'time'})
        if span_element:
            script_content = span_element.script.string
            half_match = re.search(r'showMatchState\((\d+),', script_content)
            timestamp_match = re.search(r'new Date\("(.*?)"\)', script_content)
            #上半场还是下半场
            if half_match:
              halfMatch = half_match.group(1)
            #开场时间
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                timestamp = datetime.datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M:%S')
                current_time = datetime.datetime.now()
                time_difference = current_time - timestamp
                time_difference_minutes = time_difference.total_seconds() / 60
            if int(time_difference_minutes) <= int(time_threshold) and int(halfMatch) == 1:
                    filtered_matches.append(match)#筛选出前20分钟的上半场比赛
                    
            # else:
            #     print(f"{match}开场已经超过{match_time_setting}分钟")
        else:
            print(f"{current_time} 获取{matchUrl}比赛的当前时间失败")
      return filtered_matches
    except requests.exceptions.RequestException as req_err:
        print(f"Error making HTTP request: {req_err}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
      
def main():
    current_time = datetime.datetime.now()
    print("----------------------------")
    # data = get_leagues()#获取所有联赛
    # unique_list = list(set(data))#去除重复联赛
    # insert_leagues(unique_list)#插入数据库
    filter_leagues = get_filter_league()#屏蔽的联赛
    if len(filter_leagues) == 0:
      print("目前没有屏蔽的联赛")
      
    matchUrl = scrape_data(current_time) #当前正在进行的所有比赛[2389602]
    if len(matchUrl) == 0:
      print("当前没有正在进行的比赛")
    matchSetting = tuple(getMatchSettings().values()) #比赛配置
    if not matchSetting:
      print("获取比赛配置失败")
      matchSetting = (22, 4, 1, 33, 5, 15)
    match_time_setting, total_shooting_setting, total_shootingOn_setting, total_dangerous_attacks_setting, differ_shooting_setting, differ_dangerous_attacks_setting = matchSetting
    filterUrls = filter_url(matchUrl, match_time_setting)#默认前20分钟比赛[2389602,2507090,2507091]
    isSend_match = get_isSend_match() #获取符合条件并且已经发送过邮件的比赛web_url
    if filterUrls is not None and isSend_match is not None:
      new_sendMail_match = [element for element in map(int, filterUrls) if element not in map(int, isSend_match)]
    else:
      print(f"filterUrls 和/或 isSend_match 中有一个为 None。:{filterUrls},{isSend_match}")#过滤为符合条件但是没发过邮件的比赛
    if not new_sendMail_match:
      print("没有符合条件比赛")
    else:
      print(f"URL过滤成功")
    print(f"{current_time} 符合条件的比赛场次有:{new_sendMail_match}")
    if new_sendMail_match is not None:
      for web_url in new_sendMail_match:
        crawl_data(current_time, web_url, total_shooting_setting, total_shootingOn_setting, total_dangerous_attacks_setting, differ_shooting_setting, differ_dangerous_attacks_setting, filter_leagues)
    else:
      print("没有符合条件比赛url")
      
    print("----------------------------")
    
#定时发送（秒）
schedule.every(60).seconds.do(main)
while True:
    schedule.run_pending()
    schedule.run_all()#缩短定时
    time.sleep(1)