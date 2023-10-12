from flask import Flask, request, send_file, make_response
import subprocess
import tempfile
import shutil 
import os

app = Flask(__name__)

@app.route('/')
def index():
    return open('index.html', 'r').read()

@app.route('/convert', methods=['POST'])
def convert():
    sgmodule_content = None

    if 'file' in request.files and request.files['file'].filename:
        # 如果用户上传文件
        sgmodule_file = request.files['file']
        sgmodule_content = sgmodule_file.read().decode('utf-8')
    elif 'url' in request.form:
        # 如果用户提供文件的URL
        import urllib.request
        file_url = request.form['url']
        sgmodule_content = urllib.request.urlopen(file_url).read().decode('utf-8')

    if sgmodule_content:
        # 将 SGModule 内容写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False,encoding='utf-8') as f:
            f.write(sgmodule_content)
            f.close()
            shutil.copy(f.name,'input.sgmodule')
            

        # 调用 convert_sg_st.py 并传递文件路径
        result = subprocess.run(['python3', 'convert_sg_st.py', 'input.sgmodule'])
        print(result)
        if result.returncode == 0:
            # 读取生成的 STOverride 文件
            stoverride_content = None
            with open('input.stoverride', 'r', encoding='utf-8') as f:
                stoverride_content = f.read()

            # 将生成的 STOverride 返回给用户
            response = make_response(stoverride_content)
            response.headers["Content-Disposition"] = "attachment; filename=xmly.stoverride"
            response.headers["Content-Type"] = "text/plain"

            # 删除临时文件
            os.remove(f.name)
            os.remove('input.sgmodule')
           # os.remove('input.stoverride')

            return response

    return "Error converting SGModule to STOverride."

if __name__ == '__main__':
    app.run(debug=True)
