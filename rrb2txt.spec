import os
a = Analysis(['rrb2txt.py'],
             pathex=[os.path.abspath('.')],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='rrb2txt.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
