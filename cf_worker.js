// 在cf中创建worker部署该js，绑定py推送的目标kv


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

      // 检查是否是浏览器请求
      const acceptHeader = request.headers.get('accept') || '';
      const isWebRequest = acceptHeader.includes('text/html');

      // 如果是浏览器请求且没有指定配置文件
      if (isWebRequest && path.length === 0) {
        // 获取所有配置列表
        const keys = await env.subinfo.list();
        const configList = keys.keys.map(key => {
          try {
            // 对配置名称进行解码，以正确显示中文
            return decodeURIComponent(key.name);
          } catch {
            return key.name;
          }
        }).join(', ');
        
        return new Response(`
          <!DOCTYPE html>
          <html>
            <head>
              <title>subconverterONactions_pushTOkv</title>
              <meta charset="utf-8">
              <style>
                body {
                  font-family: Arial, sans-serif;
                  display: flex;
                  justify-content: center;
                  align-items: center;
                  height: 100vh;
                  margin: 0;
                  background-color: #f0f2f5;
                }
                .container {
                  text-align: center;
                  padding: 20px;
                  background-color: white;
                  border-radius: 8px;
                  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 {
                  color: #1a73e8;
                  margin-bottom: 10px;
                }
                p {
                  color: #5f6368;
                }
                .config-list {
                  margin-top: 20px;
                  padding: 10px;
                  background-color: #f8f9fa;
                  border-radius: 4px;
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
