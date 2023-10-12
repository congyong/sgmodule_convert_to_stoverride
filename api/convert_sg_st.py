import re
import sys
import codecs

def parse_sgmodule(content):
  # 解析sgmodule内容,返回元信息、规则、脚本、代理配置
  sg_info={}
  headers = {}
  rewrite_rules = []
  scripts = []
  mitm = []
  force_http= []
  proxy_rules=[]
  
  # 解析元信息
  for line in content.splitlines():
    if line.startswith('#!'):
      key, value = line[2:].split('=', 1)
      headers[key.strip()] = value.strip()
  #解析 rules
  common_pattern_tail= r'(.*?)(?=\n\s*\[\w[\w\s-]+\]\s*|$)'
  pattern = r'\[Rule\]'+common_pattern_tail
  matches = re.search(pattern, content, re.DOTALL)
  if matches:
    proxy_rules = matches.group(1).strip().splitlines()
  # 解析REWRITE规则
 # pattern = r'\[URL Rewrite\](.*)\[Script\]'
  pattern = r'\[URL Rewrite\]'+common_pattern_tail
  matches = re.search(pattern, content, re.DOTALL)
  if matches:
    rewrite_rules = matches.group(1).strip().splitlines()
  
  # 解析脚本
  pattern = r'\[Script\]'+common_pattern_tail
  matches = re.search(pattern, content, re.DOTALL)
  if matches:
    for line in matches.group(1).strip().splitlines():
        if not (re.match(r'\s*#', line) and line.strip()):     
         pattern = r'^([^=]+)=(.*)'
         m = re.search(pattern, line)
         name = m.group(1)
         remain = m.group(2)

         script = {'name': name}

         for item in remain.split(','):
            k, v = item.split('=', 1)
            script[k.strip()] = v.strip()

         scripts.append(script)
  # 解析代理
  pattern = r'\[MITM\]'+common_pattern_tail
  matches = re.search(pattern, content, re.DOTALL)
  if matches:
    for line in matches.group(1).strip().splitlines():
        if not (re.match(r'\s*#', line) and line.strip()):    
            mitm = line
            break # 看起来只有一行 有效 mitm
  #General字段处理 只支持 force-http-engine-hosts
  pattern = r'\[General\]'+common_pattern_tail
  matches = re.search(pattern, content, re.DOTALL)
  if matches:
    for line in matches.group(1).strip().splitlines():
        if  re.match(r'\s*force-http-engine-hosts', line) :    
            force_http = line
            break # 看起来只有一行 force http

  #merge infomation
  sg_info['headers'] = headers
  sg_info['proxy_rules'] = proxy_rules
  sg_info['rewrite_rules'] = rewrite_rules
  sg_info['scripts'] = scripts
  sg_info['mitm'] = mitm
  sg_info['force_http'] = force_http
#  return headers, proxy_rules,rewrite_rules, scripts, mitm
  return sg_info


def generate_stoverride(sg_info):

  stoverride = {
    'name': sg_info['headers']['name'],
    'desc': sg_info['headers']['desc'],
    'headers': sg_info['headers'],
    'rules'  : [],
    'mitm': [],
    'force_http':[],
    'rewrite': [],
    'script': [],
    'script-providers': {}
  }
  # 处理rules 
  for rule in sg_info['proxy_rules']:
    if re.match(r'\s*#', rule): 
        # 使用正则表达式匹配以空白符后跟#开头
        stoverride['rules'].append(rule)
    elif not rule.strip():
        # 空行
        stoverride['rules'].append(rule)
    else:
        stoverride['rules'].append('- ' + rule)

  # 处理mitm
  pattern = r'hostname\s*=\s*%APPEND%\s*'
  if sg_info['mitm']:
    mitm_hosts = re.sub(pattern, '', sg_info['mitm'])
    mitm_hosts = mitm_hosts.split(',')
  else:
    mitm_hosts = ''
  for host in mitm_hosts:
    stoverride['mitm'].append('- "' + host.strip() + '"')

  # 处理force-http-engine-hosts
  pattern = r'force-http-engine-hosts\s*=\s*%APPEND%\s*'
  if sg_info['force_http']:
    force_http_hosts = re.sub(pattern, '', sg_info['force_http'])
    force_http_hosts = force_http_hosts.split(',')
  else:
    force_http_hosts = ''
  


  for host in force_http_hosts:
    stoverride['force_http'].append('- "' + host.strip() + '"')

  # 处理规则
  for rule in sg_info['rewrite_rules']:
    if rule.strip():
        pattern = rule.replace('_ reject', '- reject')
        stoverride['rewrite'].append(pattern)

  # 处理脚本
  for script in sg_info['scripts']:
    item = {
      'match': script['pattern'],
      'name': script['name'],
      'type': script['type'].replace('http-', ''),
      'require-body': True if script.get('requires-body','0') == '1' else False,
      'max_size':  script.get('max_size', '0'),
      'timeout':  script.get('timeout', '5'),
      'binary-mode': True if script.get('binary-mode', '0') == '1' else False
    }
    stoverride['script'].append(item)

    stoverride['script-providers'][script['name']] = {
      'url': script['script-path'],
      'interval': 86400
    }

  return stoverride

def format_stoverride(stoverride):

  content = ''

  #输出 header
  if stoverride.get('headers'): 
    for header in stoverride['headers']:
        content += f'#!{header}={stoverride["headers"][header]}\n'

  # 格式化元信息
  content += f'name : {stoverride["name"]}\n'
  content += f'desc : {stoverride["desc"]}\n'

  #格式化 rules 
  if stoverride.get('rules'):
    content += '\n  rules:'
    for rule in stoverride['rules']:
     content += f'\n  {rule}'
  # 格式化mitm
  content += 'http:\n'
  if stoverride.get('mitm'):
    content += '  mitm:\n'
    for host in stoverride['mitm']:
        content += f'   {host}\n'

  # 格式化force-http-engine:
  if stoverride.get('force_http'):
    content += '\n  force-http-engine:\n'
    for host in stoverride['force_http']:
        content += f'   {host}\n'
  # 格式化script部分
  if stoverride.get('script'):
    content += '\n  script:'
    for script in stoverride['script']:
     content += '\n' 
     content += f'   - match: {script["match"]}\n'
     content += f'     name: {script["name"]}\n'
     content += f'     type: {script["type"]}\n'
     content += f'     require-body: {script["require-body"]}\n'
     content += f'     binary-mode: {script["binary-mode"]}\n'
     content += f'     max_size: {script["max_size"]}\n'
     content += f'     timeout: {script["timeout"]}\n'

  # 格式化rewrite规则
  if stoverride.get('rewrite'):
    content += '\n  url-rewrite:\n'
    for rule in stoverride['rewrite']:
        content += f'   - {rule}\n'

  # 格式化script-providers
  if stoverride.get('script-providers'):
     content += '\nscript-providers:\n'
     for name, script in stoverride['script-providers'].items():
   # content += '\n'
      content += f'  {name}:\n'
      content += f'    url: {script["url"]}\n'
      content += f'    interval: {script["interval"]}\n'

  return content

def sgmodule_to_stoverride(sgmodule_file, stoverride_file=None):
  
  # 读取sgmodule文件
  with codecs.open(sgmodule_file, 'r', encoding='utf-8') as f:
    sgmodule_content = f.read()

  # 解析内容
  sg_info = parse_sgmodule(sgmodule_content)

  # 生成stoverride
  stoverride = generate_stoverride(sg_info)

  # 输出stoverride文件
  if not stoverride_file:
    stoverride_file = sgmodule_file.replace('.sgmodule', '.stoverride')
  
  stoverride_content = format_stoverride(stoverride)
  with codecs.open(stoverride_file, 'w', encoding='utf-8') as f:
    f.write(stoverride_content)

  print(f'SGModule converted to STOverride: {stoverride_file}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python convert_sg_st.py input_file.sgmodule")
    else:
        input_file = sys.argv[1]
        sgmodule_to_stoverride(input_file)
