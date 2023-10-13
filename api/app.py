from flask import Flask, request, send_file, make_response
import subprocess
import tempfile
import shutil 
import os
import sys 
sys.path.append('../api/')
import convert_sg_st

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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as sgmodule_temp_file:
            sgmodule_temp_file.write(sgmodule_content)
            sgmodule_temp_file_path = sgmodule_temp_file.name

        # 调用 convert_sg_st.py 中的 sgmodule_to_stoverride 函数
        stoverride_content=convert_sg_st.sgmodule_to_stoverride(sgmodule_temp_file_path,output_file=False)


        # 删除临时文件
        os.remove(sgmodule_temp_file_path)
      

        # 创建响应并返回生成的 STOverride 文件
        response = make_response(stoverride_content)
        response.headers["Content-Disposition"] = "attachment; filename=xmly.stoverride"
        response.headers["Content-Type"] = "text/plain"

        return response

    return "Error converting SGModule to STOverride."

if __name__ == '__main__':
    app.run(debug=True)
