// 在cf中创建worker部署该js；绑定py推送的目标kv，我的变量名是subinfo；为worker设置一个“变量与机密”值就是token了，访问的时候在地址中加上后缀  ?token=123456789  （比如subconverterONactions_pushTOkv_token=123456789），我的变量名是subconverterONactions_pushTOkv_token
// 变量名自行查找替换


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
              <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
              <style>
                body {
                  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                  margin: 0;
                  padding: 10px;
                  background-color: #f0f2f5;
                  min-height: 100vh;
                  -webkit-text-size-adjust: 100%;
                }
                .container {
                  max-width: 800px;
                  width: 100%;
                  padding: 15px;
                  background-color: white;
                  border-radius: 8px;
                  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                  margin: 0 auto;
                  box-sizing: border-box;
                }
                .header {
                  text-align: center;
                  margin-bottom: 15px;
                }
                .header h1 {
                  color: #1a73e8;
                  margin-bottom: 8px;
                  font-size: 1.5rem;
                }
                .header p {
                  color: #5f6368;
                  margin: 4px 0;
                  font-size: 0.9rem;
                }
                .input-output-container {
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  gap: 15px;
                  margin: 15px 0;
                }
                .text-area-wrapper {
                  width: 100%;
                  text-align: center;
                }
                textarea {
                  width: 100%;
                  height: 120px;
                  padding: 12px;
                  border: 1px solid #ddd;
                  border-radius: 6px;
                  resize: vertical;
                  font-family: monospace;
                  margin-top: 5px;
                  font-size: 14px;
                  -webkit-appearance: none;
                  box-sizing: border-box;
                }
                #input, #output {
                  height: 50px;
                }
                #kv_convert_param {
                  height: 500px;
                }
                .buttons {
                  margin: 12px 0;
                  display: flex;
                  gap: 8px;
                  flex-wrap: wrap;
                  justify-content: center;
                  width: 100%;
                }
                button {
                  padding: 10px 16px;
                  background-color: #1a73e8;
                  color: white;
                  border: none;
                  border-radius: 6px;
                  cursor: pointer;
                  transition: background-color 0.2s;
                  font-size: 0.9rem;
                  min-width: 120px;
                  -webkit-tap-highlight-color: transparent;
                }
                button:hover, button:active {
                  background-color: #1557b0;
                }
                .clear {
                  background-color: #dc3545;
                }
                .clear:hover, .clear:active {
                  background-color: #bb2d3b;
                }
                .back-button {
                  background-color: #28a745;
                  margin-bottom: 12px;
                  width: 100%;
                }
                .back-button:hover, .back-button:active {
                  background-color: #218838;
                }
                /* 移动端优化 */
                @media (max-width: 480px) {
                  body {
                    padding: 5px;
                  }
                  .container {
                    padding: 10px;
                  }
                  textarea {
                    height: 100px;
                    padding: 10px;
                    font-size: 13px;
                  }
                  #input, #output {
                    height: 120px;
                  }
                  #kv_convert_param {
                    height: 1200px;
                  }
                  button {
                    padding: 12px 8px;
                    font-size: 0.85rem;
                    min-width: 0;
                    flex-grow: 1;
                  }
                  .buttons {
                    gap: 6px;
                  }
                }
                /* 防止移动设备上的缩放 */
                @media (pointer: coarse) {
                  textarea {
                    font-size: 16px !important;
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
                    <label for="kv_convert_param">KV CONVERT_PARAM:</label>
                    <textarea id="kv_convert_param">${kvParam}</textarea>
                  </div>
                  <div class="buttons">
                    <button onclick="base64Encode()">Base64 Encode</button>
                    <button onclick="base64Decode()">Base64 Decode</button>
                    <button onclick="refreshParam()">Refresh Param</button>
                  </div>
                </div>
              </div>

              <script>
                async function refreshParam() {
                  try {
                    const kvTextarea = document.getElementById('kv_convert_param');
                    const currentUrl = new URL(window.location.href);
                    
                    // 添加随机参数避免缓存
                    currentUrl.searchParams.set('_', Date.now());
                    
                    // 发起请求获取最新数据
                    const response = await fetch(currentUrl);
                    const html = await response.text();
                    
                    // 使用 DOMParser 解析 HTML，提取最新 KV 数据
                    const parser = new DOMParser();
                    const newDoc = parser.parseFromString(html, 'text/html');
                    const newValue = newDoc.getElementById('kv_convert_param').value;
                    
                    // 只更新文本框内容，不刷新整个页面
                    kvTextarea.value = newValue;
                  } catch (error) {
                    console.error('刷新失败:', error);
                    alert('刷新失败，请重试');
                  }
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

                function base64Encode() {
                  const kv_convert_param = document.getElementById('kv_convert_param').value;
                  try {
                    document.getElementById('kv_convert_param').value = btoa(unescape(encodeURIComponent(kv_convert_param)));
                  } catch(e) {
                    document.getElementById('kv_convert_param').value = 'Error: Invalid input for Base64 encoding';
                  }
                }
          
                function base64Decode() {
                  const kv_convert_param = document.getElementById('kv_convert_param').value;
                  try {
                    document.getElementById('kv_convert_param').value = decodeURIComponent(escape(atob(kv_convert_param)));
                  } catch(e) {
                    document.getElementById('kv_convert_param').value = 'Error: Invalid Base64 encoding';
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
        const configList = keys.keys
          .filter(key => key.name !== 'CONVERT_PARAM') // 排除CONVERT_PARAM键
          .map(key => {
          try {
            // 对配置名称进行解码，以正确显示中文
            return prefix + '/' + decodeURIComponent(key.name) + '?token=' + TOKEN;
          } catch {
            return prefix + '/' + key.name + '?token=' + TOKEN;
          }
        }).join('<br><br>');
        
        return new Response(`
          <!DOCTYPE html>
          <html>
            <head>
              <title>subconverterONactions_pushTOkv</title>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
              <style>
                body {
                  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                  display: flex;
                  justify-content: center;
                  align-items: center;
                  min-height: 100vh;
                  margin: 0;
                  background-color: #f0f2f5;
                  padding: 15px;
                  -webkit-text-size-adjust: 100%;
                }
                .container {
                  text-align: center;
                  padding: 20px;
                  background-color: white;
                  border-radius: 8px;
                  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                  width: 100%;
                  max-width: 1200px;
                  box-sizing: border-box;
                  margin: 15px;
                }
                h1 {
                  color: #1a73e8;
                  margin-bottom: 10px;
                  font-size: 1.8rem;
                  line-height: 1.3;
                }
                p {
                  color: #5f6368;
                  margin: 10px 0;
                  font-size: 1rem;
                  line-height: 1.5;
                }
                .config-list {
                  margin-top: 20px;
                  padding: 15px;
                  background-color: #f8f9fa;
                  border-radius: 6px;
                  word-wrap: break-word;
                  text-align: left;
                  overflow-wrap: break-word;
                }
                .config-list p {
                  margin: 0;
                  padding: 8px 0;
                  text-align: center;
                }
                .links {
                  margin-top: 20px;
                  display: flex;
                  flex-wrap: wrap;
                  justify-content: center;
                  gap: 12px;
                }
                .links a {
                  color: #1a73e8;
                  text-decoration: none;
                  padding: 8px 16px;
                  border-radius: 6px;
                  background-color: #f0f7ff;
                  transition: all 0.2s;
                  display: inline-block;
                  white-space: nowrap;
                }
                .links a:hover {
                  background-color: #e0efff;
                  text-decoration: none;
                }
                /* 移动端优化 */
                @media (max-width: 480px) {
                  body {
                    padding: 10px;
                    align-items: flex-start;
                    min-height: calc(100vh - 20px);
                  }
                  .container {
                    padding: 15px;
                    margin: 0;
                  }
                  h1 {
                    font-size: 1.5rem;
                    margin-bottom: 8px;
                  }
                  p {
                    font-size: 0.95rem;
                  }
                  .config-list {
                    padding: 12px;
                  }
                  .links {
                    gap: 8px;
                  }
                  .links a {
                    padding: 8px 12px;
                    font-size: 0.9rem;
                    white-space: normal;
                  }
                }
                /* 防止移动设备上的缩放问题 */
                @media (pointer: coarse) {
                  body {
                    font-size: 16px;
                  }
                  .links a {
                    padding: 10px 16px;
                  }
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
                  <p>Available Configurations URL:</p>
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
};
