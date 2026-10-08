"""OWASP-recommended scanner in static mode, with Python network calls denied.

This is a cooperative wrapper, not an OS sandbox for hostile Python/native code.
"""
import os
import sys
from importlib.metadata import version

def deny_network(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr','socket.sendto','subprocess.Popen','os.system','os.exec','os.posix_spawn'):
        raise PermissionError('Larpus scanner policy denies network and child execution')

def main():
    for key in list(os.environ):
        if any(word in key.upper() for word in ('API_KEY','TOKEN','PROXY','SECRET','OTEL_EXPORTER','LANGSMITH','LANGCHAIN_TRACING')):
            os.environ.pop(key,None)
    os.environ.update({'LANGSMITH_TRACING':'false','LANGCHAIN_TRACING_V2':'false','OTEL_SDK_DISABLED':'true','AWS_EC2_METADATA_DISABLED':'true','PYTHONUTF8':'1'})
    sys.addaudithook(deny_network)
    if version('skillspector')!='2.12.0':
        raise SystemExit('Expected pinned SkillSpector 2.12.0')
    if '--no-llm' not in sys.argv or len(sys.argv)<3 or sys.argv[1]!='scan':
        raise SystemExit('Only static scan commands are supported')
    from skillspector.cli import app
    app()

if __name__=='__main__':
    main()
