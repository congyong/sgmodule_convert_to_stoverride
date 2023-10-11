
# sgmodule_convert_to_stoverride

 脚本作用:将surge/shadowrocket 使用的 sgmodule "模块" 转换为 stash 使用的 "覆盖"   stoverride 文件

使用方法：python3 convert_sg_st.py file_name.sgmodule , 会在同目录下生成 file_name.stoverride 文件

**支持的sgmodule 里的标签有:**

-  [General] 中的 force-http-engine-hosts
-  MITM 
- URL Rewrite
- Rule
- Script

测试了 几个需要的脚本可以工作, 在此备份 
