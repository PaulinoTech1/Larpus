import ctypes,os,subprocess,tempfile,time,unittest
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from runtime import dlp
from runtime.mcp_client import child_parameters

SE_DACL_PROTECTED=0x1000
ACCESS_ALLOWED_ACE_TYPE=0
FILE_ALL_ACCESS=0x1F01FF
OBJECT_INHERIT_ACE,CONTAINER_INHERIT_ACE,INHERITED_ACE=0x1,0x2,0x10

def read_dacl(path):
    """Return (dacl_protected, [(ace_type, flags, mask, sid_string)]) via advapi32, no PowerShell."""
    advapi=ctypes.WinDLL('advapi32',use_last_error=True)
    dacl,descriptor=ctypes.c_void_p(),ctypes.c_void_p()
    status=advapi.GetNamedSecurityInfoW(ctypes.c_wchar_p(str(path)),1,4,None,None,ctypes.byref(dacl),None,ctypes.byref(descriptor))
    if status:raise OSError(status,'GetNamedSecurityInfoW failed')
    try:
        control,revision=wintypes.WORD(),wintypes.DWORD()
        if not advapi.GetSecurityDescriptorControl(descriptor,ctypes.byref(control),ctypes.byref(revision)):raise ctypes.WinError(ctypes.get_last_error())
        class ACL(ctypes.Structure):_fields_=[('rev',ctypes.c_ubyte),('sbz1',ctypes.c_ubyte),('size',wintypes.WORD),('count',wintypes.WORD),('sbz2',wintypes.WORD)]
        class ACE(ctypes.Structure):_fields_=[('type',ctypes.c_ubyte),('flags',ctypes.c_ubyte),('size',wintypes.WORD),('mask',wintypes.DWORD),('sid',wintypes.DWORD)]
        aces=[]
        for index in range(ACL.from_address(dacl.value).count):
            ace=ctypes.c_void_p()
            if not advapi.GetAce(dacl,index,ctypes.byref(ace)):raise ctypes.WinError(ctypes.get_last_error())
            entry=ACE.from_address(ace.value);text=ctypes.c_wchar_p()
            if not advapi.ConvertSidToStringSidW(ctypes.c_void_p(ace.value+ACE.sid.offset),ctypes.byref(text)):raise ctypes.WinError(ctypes.get_last_error())
            aces.append((entry.type,entry.flags,entry.mask,text.value));ctypes.windll.kernel32.LocalFree(text)
        return bool(control.value&SE_DACL_PROTECTED),aces
    finally:ctypes.windll.kernel32.LocalFree(descriptor)

def current_sid():
    return subprocess.run(['whoami','/user','/fo','csv','/nh'],capture_output=True,text=True,check=True,stdin=subprocess.DEVNULL).stdout.strip().split(',')[-1].strip('"')

class HelperInvocationTests(unittest.TestCase):
    def test_command_is_fixed_and_noninteractive(self):
        command=dlp.protect_command('powershell.exe',Path('C:/q'))
        self.assertEqual(command[:4],['powershell.exe','-NoProfile','-NonInteractive','-File'])
        self.assertEqual(command[4:],[str(dlp.ROOT/'scripts/protect-quarantine.ps1'),'-Target',str(Path('C:/q'))])

    def test_helper_never_inherits_mcp_stdin(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(dlp,'QUARANTINE',Path(temp)/'data'/'quarantine'),\
             patch.object(dlp,'os',SimpleNamespace(**{**vars(os),'name':'nt','environ':{**os.environ,'SYSTEMROOT':'C:\\Windows'}})),\
             patch('runtime.dlp.subprocess.run',return_value=subprocess.CompletedProcess([],0)) as run:
            dlp.secure_directory()
        kwargs=run.call_args.kwargs
        self.assertIs(kwargs['stdin'],subprocess.DEVNULL)
        self.assertEqual((kwargs['shell'],kwargs['check'],kwargs['capture_output'],kwargs['timeout']),(False,True,True,10))
        self.assertNotIn('env',kwargs);self.assertNotIn('creationflags',kwargs)

    def test_helper_script_uses_no_cmdlets(self):
        # Cmdlet resolution triggers module discovery, which is what made launches slow.
        source=(dlp.ROOT/'scripts/protect-quarantine.ps1').read_text(encoding='utf-8')
        script='\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('#'))
        for cmdlet in ('Get-Item','Get-Acl','Set-Acl','Test-Path','Get-ChildItem','Import-Module'):
            self.assertNotIn(cmdlet,script)

@unittest.skipUnless(os.name=='nt','Windows ACL readback')
class WindowsAclTests(unittest.TestCase):
    def protect(self,target):
        executable=Path(os.environ['SYSTEMROOT'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        # Same allowlisted environment as the MCP child (no PSModulePath), same production timeout.
        env=child_parameters().env
        started=time.monotonic()
        result=subprocess.run(dlp.protect_command(executable,target),shell=False,capture_output=True,stdin=subprocess.DEVNULL,timeout=dlp.PROTECT_TIMEOUT_DEFAULT,env=env)
        return result,time.monotonic()-started

    def test_acl_is_owner_and_system_only_without_inheritance(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'quarantine';target.mkdir()
            self.assertFalse(read_dacl(target)[0])
            result,seconds=self.protect(target)
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            self.assertLess(seconds,dlp.PROTECT_TIMEOUT_DEFAULT)
            protected,aces=read_dacl(target)
            self.assertTrue(protected)
            self.assertEqual(sorted(sid for *_,sid in aces),sorted({current_sid(),'S-1-5-18'}))
            for ace_type,flags,mask,sid in aces:
                self.assertEqual((ace_type,mask),(ACCESS_ALLOWED_ACE_TYPE,FILE_ALL_ACCESS),sid)
                self.assertEqual(flags&(OBJECT_INHERIT_ACE|CONTAINER_INHERIT_ACE|INHERITED_ACE),OBJECT_INHERIT_ACE|CONTAINER_INHERIT_ACE,sid)
            again,_=self.protect(target)
            self.assertEqual(again.returncode,0);self.assertEqual(read_dacl(target),(protected,aces))

    def test_missing_target_and_junction_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertNotEqual(self.protect(Path(temp)/'missing')[0].returncode,0)
            real=Path(temp)/'real';real.mkdir();link=Path(temp)/'link'
            subprocess.run(['cmd','/c','mklink','/J',str(link),str(real)],capture_output=True,check=True,stdin=subprocess.DEVNULL)
            self.assertNotEqual(self.protect(link)[0].returncode,0)

if __name__=='__main__':unittest.main()
