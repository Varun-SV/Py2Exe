import os
import subprocess
print("Checking Necessary Files...")
g = subprocess.getoutput("pip freeze")
temp = []
temp = g.split('\n')
t = []
for j in temp:
    t.append(j.split('==')[0])

if 'pyinstaller' not in t:
    print("Installing essentials...")
    _=subprocess.run("pip install pyinstaller")

file_name=str(input("Python script (with location): "))
fname=''
try:
    dir='\\'.join(file_name.split('\\')[:-1])
    dir+='\\'
    fname = str(file_name.split('\\')[-1])
    f=open(str(dir)+'hook-inputhook.py','w')
    st = '''from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('IPython.lib.inputhook')
'''
    f.writelines(st)
    f.close()
    cmd = 'cd '+dir+' && pyinstaller --onefile --additional-hooks-dir='+dir+' '+str(file_name)
    # print(cmd)
    os.system(cmd)
except:
    dir=os.getcwd()
    dir+='\\'
    f=open(str(dir)+'hook-inputhook.py','w')
    st = '''from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('IPython.lib.inputhook')
'''
    f.writelines(st)
    f.close()
    cmd = 'cd '+dir+' && pyinstaller --onefile --additional-hooks-dir='+dir+' '+str(file_name)
    # print(cmd)
    os.system(cmd)
finally:
    fn = "move /Y %sdist\\\%s.exe %s && rd /s/q %sbuild && rd /s/q %sdist && del /q %shook-inputhook.py && del /q %s.spec"%(str(dir),str(fname.split('.')[0]),str(dir),str(dir),str(dir),str(dir),str(dir+fname.split('.')[0]))
    # print(fn) 
    os.system(fn)