import os
import http.server
import socketserver
import json
import shutil
from urllib.parse import urlparse, parse_qs

class LocalProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        # 处理ping请求，用于测试连接
        if parsed_path.path == '/ping':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'status': 'success', 'message': 'Local proxy is running'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        # 处理文件传输请求
        elif parsed_path.path == '/transfer_ccx':
            try:
                # 获取参数
                source_path = query_params.get('source_path', [None])[0]
                target_path = query_params.get('target_path', [None])[0]

                if not source_path or not target_path:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {'status': 'error', 'message': 'Missing source_path or target_path'}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    return

                # 检查源文件是否存在
                if not os.path.exists(source_path):
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {'status': 'error', 'message': f'Source file not found: {source_path}'}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    return

                # 确保目标目录存在
                target_dir = os.path.dirname(target_path)
                os.makedirs(target_dir, exist_ok=True)

                # 复制文件
                shutil.copy2(source_path, target_path)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'success', 'message': f'File transferred to {target_path}'}
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'error', 'message': str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            return

        # 未知请求路径
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'status': 'error', 'message': 'Unknown endpoint'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return

def run_proxy_server(port=8000):
    """启动本地代理服务器"""
    server_address = ('', port)
    httpd = socketserver.TCPServer(server_address, LocalProxyHandler)
    print(f'[LocalProxy] 服务器启动在端口 {port}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('[LocalProxy] 服务器关闭')
        httpd.server_close()

if __name__ == '__main__':
    run_proxy_server()