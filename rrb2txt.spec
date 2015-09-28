# -*- mode: python -*-

block_cipher = None


a = Analysis(['rrb2txt.py'],
             pathex=['f:\\Brydz\\RRBridge'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)
pyz = PYZ(a.pure,
             cipher=block_cipher)
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
