// 在cf中创建worker部署该js；绑定py推送的目标kv，我的变量名是subinfo；为worker设置一个“变量与机密”值就是token了，访问的时候在地址中加上后缀  ?token=123456789  （比如subconverterONactions_pushTOkv_token=123456789），我的变量名是subconverterONactions_pushTOkv_token


export default {
  async fetch(request, env, ctx) {
    try {
      // 处理 CORS
      if (request.method === 'OPTIONS') {
        return new Response(null, {
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Max-Age': '86400',
          }
        });
      }

      // 获取请求的 URL 和参数
      const url = new URL(request.url);
      const path = url.pathname.split('/').filter(Boolean);
      const prefix = url.origin;

      // 获取token
      const TOKEN = env.subconverterONactions_pushTOkv_token;

      // 在请求中获取 token 参数
      const token = url.searchParams.get('token');

      // 验证token
      if (!token) {
        return new Response('Missing token', { status: 401, headers: { 'Access-Control-Allow-Origin': '*' } });
      }
      if (token !== TOKEN) {
        return new Response('Invalid token', { status: 403, headers: { 'Access-Control-Allow-Origin': '*' } });
      }

      // 检查是否是浏览器请求
      const acceptHeader = request.headers.get('accept') || '';
      const isWebRequest = acceptHeader.includes('text/html');


      // 获取KV中CONVERT_PARAM内容
      const convertParamContent = await env.subinfo.get("CONVERT_PARAM");
      let kvParam = "Null"; // 默认值
      if (convertParamContent) {
        try {
          const parsed = JSON.parse(convertParamContent);  // 字符串 → 对象
          let decodedValue = parsed.CONVERT_PARAM || "";
          // Base64解码函数（支持中文）
          const base64Decode = (str) => {
            // 将Base64字符串转换为二进制字符串
            const binaryString = atob(str);
            // 将二进制字符串转换为字节数组
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            // 将字节数组解码为UTF-8字符串
            return new TextDecoder('utf-8').decode(bytes);
          };
          // 第一次Base64解码
          try {
            decodedValue = base64Decode(decodedValue);
            // 第二次Base64解码
            try {
              decodedValue = base64Decode(decodedValue);
              kvParam = decodedValue;
            } catch (innerError) {
              kvParam = "第二次Base64解码失败: " + innerError.message;
            }
          } catch (outerError) {
            kvParam = "第一次Base64解码失败: " + outerError.message;
          }
        } catch (e) {
          kvParam = "解析JSON出错: " + e.message;
        }
      }

      
      // 如果路径是 /encoder，返回编码器页面
      if (path[0] === 'encoder') {
        return new Response(`
          <!DOCTYPE html>
          <html>
            <head>
              <title>Online Encoder/Decoder - by xiaozhidepikaqiu</title>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <style>
                body {
                  font-family: Arial, sans-serif;
                  margin: 20px;
                  background-color: #f0f2f5;
                  display: flex;
                  justify-content: center;
                  min-height: 100vh;
                }
                .container {
                  max-width: 800px;
                  width: 100%;
                  padding: 20px;
                  background-color: white;
                  border-radius: 8px;
                  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .header {
                  text-align: center;
                  margin-bottom: 20px;
                }
                .header h1 {
                  color: #1a73e8;
                  margin-bottom: 10px;
                }
                .header p {
                  color: #5f6368;
                  margin: 5px 0;
                }
                .input-output-container {
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  gap: 20px;
                  margin: 20px 0;
                }
                .text-area-wrapper {
                  width: 90%;
                  text-align: center;
                }
                textarea {
                  width: 100%;
                  height: 150px;
                  padding: 10px;
                  border: 1px solid #ddd;
                  border-radius: 4px;
                  resize: vertical;
                  font-family: monospace;
                  margin-top: 5px;
                }
                #input {
                  height: 50px;
                }
              
                #output {
                  height: 50px;
                }
              
                #temp {
                  height: 400px;
                }
                .buttons {
                  margin: 15px 0;
                  display: flex;
                  gap: 10px;
                  flex-wrap: wrap;
                  justify-content: center;
                }
                button {
                  padding: 8px 16px;
                  background-color: #1a73e8;
                  color: white;
                  border: none;
                  border-radius: 4px;
                  cursor: pointer;
                  transition: background-color 0.2s;
                }
                button:hover {
                  background-color: #1557b0;
                }
                .clear {
                  background-color: #dc3545;
                }
                .clear:hover {
                  background-color: #bb2d3b;
                }
                .back-button {
                  background-color: #28a745;
                  margin-bottom: 15px;
                }
                .back-button:hover {
                  background-color: #218838;
                }
                @media (max-width: 600px) {
                  .container {
                    padding: 10px;
                  }
                  .buttons {
                    flex-direction: column;
                  }
                  button {
                    width: 100%;
                  }
                  .text-area-wrapper {
                    width: 100%;
                  }
                }
              </style>
            </head>
            <body>
              <div class="container">
                <div class="header">
                  <h1>Online URL/Base64 Coder</h1>
                  <p>Last Updated: ${new Date().toUTCString()}</p>
                  <p>By: xiaozhidepikaqiu</p>
                </div>
                <button onclick="goBack()" class="back-button">← Back to Home</button>
                <div class="input-output-container">
                  <div class="text-area-wrapper">
                    <label for="input">Input:</label>
                    <textarea id="input" placeholder="Enter text to encode/decode"></textarea>
                  </div>
                  <div class="buttons">
                    <button onclick="urlEncode()">URL Encode</button>
                    <button onclick="urlDecode()">URL Decode</button>
                    <button onclick="clearAll()" class="clear">Clear Input&Output</button>
                  </div>
                  <div class="text-area-wrapper">
                    <label for="output">Output:</label>
                    <textarea id="output" readonly></textarea>
                  </div>

                  <div class="buttons">
                    <button onclick="copyOutput()">Copy Output</button>
                  </div>
                  <div id="copy-tip" style="text-align:center; color:green; font-size:14px; visibility:hidden; opacity:0; transition: opacity 0.3s;">
                    Copied to clipboard!
                  </div>

                  <div class="text-area-wrapper">
                    <label for="temp">KV Storage Contents:</label>
                    <textarea id="temp">${kvParam}</textarea>
                  </div>
                  <div class="buttons">
                    <button onclick="base64EncodeTemp()">Base64 Encode Temp</button>
                    <button onclick="base64DecodeTemp()">Base64 Decode Temp</button>
                    <button onclick="refreshParam()">Refresh Param</button>
                  </div>
                </div>
              </div>

              <script>
                function refreshParam() {
                  window.location.reload();
                }
                
                function copyOutput() {
                  const output = document.getElementById('output');
                  const tip = document.getElementById('copy-tip');
                  const text = output.value;
                
                  // 显示提示函数（绿色或红色）
                  function showTip(message, color = 'green') {
                    tip.textContent = message;
                    tip.style.color = color;
                    tip.style.visibility = 'visible';
                    tip.style.opacity = '1';
                    setTimeout(() => {
                      tip.style.opacity = '0';
                      setTimeout(() => {
                        tip.style.visibility = 'hidden';
                        tip.textContent = 'Copied to clipboard!';
                        tip.style.color = 'green';
                      }, 300);
                    }, 1500);
                  }
                  // 现代浏览器使用 Clipboard API
                  if (navigator.clipboard && window.isSecureContext) {
                    navigator.clipboard.writeText(text).then(() => {
                      showTip('Copied to clipboard!', 'green');
                    }).catch(() => {
                      fallbackCopy();
                    });
                  } else {
                    fallbackCopy();
                  }               
                  // 兼容旧浏览器的复制方法
                  function fallbackCopy() {
                    output.select();
                    output.setSelectionRange(0, 99999); // 兼容移动端
                    const successful = document.execCommand('copy');
                    if (successful) {
                      showTip('Copied to clipboard!', 'green');
                    } else {
                      showTip('Copy failed', 'red');
                    }
                  }
                }              
                        
                function goBack() {
                  window.location.href = '/?token=${TOKEN}';
                }

                function urlEncode() {
                  const input = document.getElementById('input').value;
                  try {
                    document.getElementById('output').value = encodeURIComponent(input);
                  } catch(e) {
                    document.getElementById('output').value = 'Error: ' + e.message;
                  }
                }

                function urlDecode() {
                  const input = document.getElementById('input').value;
                  try {
                    document.getElementById('output').value = decodeURIComponent(input);
                  } catch(e) {
                    document.getElementById('output').value = 'Error: Invalid URL encoding';
                  }
                }

                function base64EncodeTemp() {
                  const temp = document.getElementById('temp').value;
                  try {
                    document.getElementById('temp').value = btoa(unescape(encodeURIComponent(temp)));
                  } catch(e) {
                    document.getElementById('temp').value = 'Error: Invalid input for Base64 encoding';
                  }
                }
          
                function base64DecodeTemp() {
                  const temp = document.getElementById('temp').value;
                  try {
                    document.getElementById('temp').value = decodeURIComponent(escape(atob(temp)));
                  } catch(e) {
                    document.getElementById('temp').value = 'Error: Invalid Base64 encoding';
                  }
                }

                function clearAll() {
                  document.getElementById('input').value = '';
                  document.getElementById('output').value = '';
                }
              </script>
            </body>
          </html>
        `, {
          headers: {
            'content-type': 'text/html;charset=utf-8',
            'Access-Control-Allow-Origin': '*'
          }
        });
      }

      // 如果是浏览器请求且没有指定配置文件
      if (isWebRequest && path.length === 0) {
        // 获取所有配置列表
        const keys = await env.subinfo.list();
        const configList = keys.keys.map(key => {
          try {
            // 对配置名称进行解码，以正确显示中文
            return prefix + '/' + decodeURIComponent(key.name) + '?token=' + TOKEN;
          } catch {
            return prefix + '/' + key.name + '?token=' + TOKEN;
          }
        }).join('<br>');
        
        return new Response(`
          <!DOCTYPE html>
          <html>
            <head>
              <title>subconverterONactions_pushTOkv</title>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <style>
                body {
                  font-family: Arial, sans-serif;
                  display: flex;
                  justify-content: center;
                  align-items: center;
                  min-height: 100vh;
                  margin: 0;
                  background-color: #f0f2f5;
                  padding: 20px;
                }
                .container {
                  text-align: center;
                  padding: 20px;
                  background-color: white;
                  border-radius: 8px;
                  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                  max-width: 1200px;
                  width: 100%;
                }
                h1 {
                  color: #1a73e8;
                  margin-bottom: 10px;
                }
                p {
                  color: #5f6368;
                  margin: 10px 0;
                }
                .config-list {
                  margin-top: 20px;
                  padding: 10px;
                  background-color: #f8f9fa;
                  border-radius: 4px;
                  word-wrap: break-word;
                }
                .links {
                  margin-top: 20px;
                }
                .links a {
                  color: #1a73e8;
                  text-decoration: none;
                  margin: 0 10px;
                }
                .links a:hover {
                  text-decoration: underline;
                }
              </style>
            </head>
            <body>
              <div class="container">
                <h1>subconverterONactions_pushTOkv</h1>
                <p>Configuration Service is Running</p>
                <p>Last Updated: ${new Date().toUTCString()}</p>
                <p>By: xiaozhidepikaqiu</p>
                <div class="config-list">
                  <p>Available Configurations:</p>
                  <p>${configList || 'No configurations available'}</p>
                </div>
                <div class="links">
                  <a href="/encoder?token=${TOKEN}">Go to Coder</a>
                </div>
              </div>
            </body>
          </html>
        `, {
          headers: {
            'content-type': 'text/html;charset=utf-8',
            'Access-Control-Allow-Origin': '*'
          }
        });
      }

      // 如果没有指定配置文件名，返回404
      if (path.length === 0) {
        return new Response('Please specify a configuration file', { 
          status: 404,
          headers: { 'Access-Control-Allow-Origin': '*' }
        });
      }

      // 获取配置文件名并进行URL解码
      const configName = decodeURIComponent(path[path.length - 1]);
      
      // 获取当前时间戳
      const now = new Date();
      const timestamp = Math.floor(now.getTime() / 1000);

      // 从 KV 中获取指定的配置
      let kvData;
      try {
        // 尝试直接获取
        kvData = await env.subinfo.get(configName);
        if (!kvData) {
          // 如果获取失败，尝试编码后再获取
          kvData = await env.subinfo.get(encodeURIComponent(configName));
        }
      } catch (error) {
        console.error('KV get error:', error);
      }

      if (!kvData) {
        return new Response('Configuration not found', { 
          status: 404,
          headers: { 'Access-Control-Allow-Origin': '*' }
        });
      }

      // 解析 KV 数据
      let kvParsedData;
      try {
        kvParsedData = JSON.parse(kvData);
      } catch (error) {
        console.error('Parse error:', error);
        return new Response('Invalid configuration data', { 
          status: 500,
          headers: { 'Access-Control-Allow-Origin': '*' }
        });
      }

      // 解码 base64 配置
      let configContent;
      try {
        // 获取配置内容（支持两种可能的键名格式）
        const base64Config = kvParsedData[configName] || kvParsedData[encodeURIComponent(configName)];
        if (!base64Config) {
          throw new Error('Configuration content not found');
        }
        
        const base64Decoded = atob(base64Config);
        const bytes = new Uint8Array(base64Decoded.length);
        for (let i = 0; i < base64Decoded.length; i++) {
          bytes[i] = base64Decoded.charCodeAt(i);
        }
        configContent = new TextDecoder('utf-8').decode(bytes);
      } catch (error) {
        console.error('Decode error:', error);
        return new Response('Failed to decode configuration', { 
          status: 500,
          headers: { 'Access-Control-Allow-Origin': '*' }
        });
      }

      // 构建响应头
      const headers = new Headers({
        'content-type': 'text/yaml;charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Expose-Headers': '*',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      });

      // 添加从原始订阅获取的头信息
      if (kvParsedData.headers) {
        for (const [key, value] of Object.entries(kvParsedData.headers)) {
          headers.set(key, value);
        }
      }

      // 如果没有获取到订阅信息，使用默认值
      if (!headers.has('subscription-userinfo')) {
        headers.set('subscription-userinfo', 'upload=0; download=0; total=0; expire=0');
      }
      if (!headers.has('profile-update-interval')) {
        headers.set('profile-update-interval', '24');
      }
      if (!headers.has('profile-update-timestamp')) {
        headers.set('profile-update-timestamp', timestamp.toString());
      }
      if (!headers.has('content-disposition')) {
        headers.set('content-disposition', `attachment; filename*=UTF-8''${encodeURIComponent(configName)}`);
      }

      // 返回配置
      return new Response(configContent, { headers });

    } catch (error) {
      console.error('Worker error:', error);
      return new Response(`Error: ${error.message}`, {
        status: 500,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Content-Type': 'text/plain;charset=utf-8'
        }
      });
    }
  }
};
