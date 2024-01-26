const express = require('express');
const mysql = require('mysql2');
const cors = require('cors'); 
const bodyParser = require('body-parser');
const csvtojson = require('csvtojson');

const app = express();
const port = 3000;

app.use(cors());

app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*'); // 允许所有域访问
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, PATCH, DELETE');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  res.header('Content-Type', 'application/json; charset=utf-8');
  next();
});
app.use(bodyParser.json()); 

const connection = mysql.createConnection({
  host: 'localhost',
  user: 'root',
  password: 'caizhaoping525',
  database: 'python'
});

connection.connect();

app.get('/getDefaultValues', (req, res) => {
  connection.query('SELECT * FROM match_setting', (error, results, fields) => {
    if (error) {
      console.error(error);
      res.status(500).send('Internal Server Error');
      return;
    }
    res.json(results[0]); 
  });
});

app.post('/updateSettings', (req, res) => {
  const data = req.body;
  const sql = `
    UPDATE match_setting
    SET
      match_time_setting = ?,
      total_shooting_setting = ?,
      total_shootingOn_setting = ?,
      total_dangerous_attacks_setting = ?,
      differ_shooting_setting = ?,
      differ_dangerous_attacks_setting = ?;`;

  connection.query(sql, [
    data.match_time_setting,
    data.total_shooting_setting,
    data.total_shootingOn_setting,
    data.total_dangerous_attacks_setting,
    data.differ_shooting_setting,
    data.differ_dangerous_attacks_setting
  ], (error, results, fields) => {
    if (error) {
      console.error(error);
      res.status(500).json({ success: false, message: '更新比赛配置失败' });
    } else {
      res.json({ success: true, message: '更新比赛配置成功', data: data });
    }
  });
});

app.get('/exportData', async (req, res) => {
  const sqlQuery = 'SELECT match_name AS 比赛队伍, total_shooting AS 两队总射门, total_shootingOn AS 两队总射正, total_dangerous_attacks AS 两队危险进攻总数, match_link AS 比赛链接, match_id AS 比赛ID, match_league AS 比赛联赛, match_time AS 比赛时间 FROM `match`';
  connection.query(sqlQuery, (err, results) => {
    if (err) {
      console.error('Error fetching data: ' + err.stack);
      res.status(500).send('Internal Server Error');
      return;
    }
    const columns = Object.keys(results[0]);

    const headerRow = columns.join(',');
    console.log(headerRow);

    const csvData = [headerRow].concat(results.map(row => columns.map(column => row[column]).join(','))).join('\n');
    res.header('Content-Type', 'text/csv');
    res.header('Content-Disposition', 'attachment; filename=data.csv');
    res.send(csvData);
  });
});

app.get('/league', (req, res) => {
  connection.query('SELECT * FROM league', (error, results, fields) => {
    if (error) {
      console.error(error);
      res.status(500).send('Internal Server Error');
      return;
    }
    res.json(results); 
  });
});

app.post('/submit_filter', (req, res) => {
  const submittedOptions = req.body;
  const selectedOptions = submittedOptions;
  let asyncOperationsCount = selectedOptions.length;// 跟踪异步操作的数量
  const resultsArray = [];// 存储所有异步操作的结果
  const handleAsyncOperation = (error, results, fields) => {// 定义回调函数，用于处理每个异步操作完成后的逻辑
    if (error) {
      console.error(error);
      res.status(500).json({ success: false, message: '更新屏蔽联赛设定失败' });
    } else {
      resultsArray.push(results);
      asyncOperationsCount--;// 每次异步操作完成，减少计数
      if (asyncOperationsCount === 0) {// 当所有异步操作完成时，发送最终响应
        res.json({ success: true, message: '更新屏蔽联赛设定成功', data: resultsArray });
      }
    }
  };
  selectedOptions.forEach(element => {// 遍历 selectedOptions，为每个元素执行数据库更新操作
    const sql = `
      UPDATE league
      SET is_filter = 1
      WHERE league_name = '${element.name}';`;
    connection.query(sql, handleAsyncOperation);
  });
});

// 启动服务器
app.listen(port, () => {
  console.log(`Server is running on http://192.168.1.5:${port}`);
});
